"""Private Instagram reader; publish only its JSON and downloaded photographs.

Uses Instagram API with Instagram Login (instagram_business_basic). No scraping,
browser token or access to messages/comments. Can run in CI or behind the CMS.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024
PUBLIC_FEED_MAX_BYTES = 160000
MAX_PAGES = 8
MEDIA_FIELDS = 'id,caption,media_type,media_url,permalink,timestamp,children.limit(50){media_type,media_url}'


class InstagramError(ValueError):
    """Safe operational message: never include upstream bodies, URLs or tokens."""


def _url_allowed(url: str, kind: str) -> bool:
    try:
        value = urlsplit(url)
        host = (value.hostname or '').lower()
        if value.scheme != 'https' or value.username or value.password or value.port not in (None, 443):
            return False
        if value.fragment or '\\' in url or any(ord(c) < 32 for c in url):
            return False
        if kind == 'graph':
            return host == 'graph.instagram.com'
        return any(host.endswith('.' + domain) for domain in ('cdninstagram.com', 'fbcdn.net'))
    except (ValueError, TypeError):
        return False


def _resolve_public(url: str) -> None:
    try:
        addresses = socket.getaddrinfo(urlsplit(url).hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise InstagramError('El servicio ha devuelto un destino de red no permitido.')
    except (OSError, ValueError):
        raise InstagramError('No se ha podido resolver el servicio de Instagram.') from None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request(url: str, *, kind: str, token: str = '', maximum: int) -> tuple[bytes, str]:
    """Validate every redirect before issuing it, including its DNS addresses."""
    from urllib.parse import urljoin
    opener = build_opener(_NoRedirect())
    for attempt in range(4):
        if not _url_allowed(url, kind):
            raise InstagramError('Instagram ha devuelto un enlace no permitido.')
        _resolve_public(url)
        headers = {'User-Agent': 'FormulaUEM-InstagramReader/1', 'Accept': 'application/json' if kind == 'graph' else 'image/jpeg,image/png,image/webp'}
        if token and kind == 'graph':
            headers['Authorization'] = 'Bearer ' + token
        try:
            with opener.open(Request(url, headers=headers), timeout=20) as response:
                length = response.headers.get('Content-Length')
                if length and (not length.isdigit() or int(length) > maximum):
                    raise InstagramError('La respuesta de Instagram supera el límite permitido.')
                body = response.read(maximum + 1)
                if len(body) > maximum:
                    raise InstagramError('La respuesta de Instagram supera el límite permitido.')
                return body, response.headers.get_content_type().lower()
        except HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and exc.headers.get('Location'):
                url = urljoin(url, exc.headers['Location'])
                exc.close()
                continue
            status = exc.code
            exc.close()
            if status in (400, 401, 403):
                raise InstagramError('Instagram ha rechazado la autorización. Revisa la conexión y la vigencia del token.') from None
            if status == 429:
                raise InstagramError('Instagram ha limitado temporalmente las consultas. Se conserva la versión anterior.') from None
            raise InstagramError('Instagram no está disponible. Se conserva la versión anterior.') from None
        except (OSError, URLError, ValueError):
            raise InstagramError('No se ha podido consultar Instagram. Se conserva la versión anterior.') from None
    raise InstagramError('Demasiadas redirecciones del servicio de Instagram.')


def _graph(path: str, params: dict, token: str) -> dict:
    body, mime = _request('https://graph.instagram.com/' + path + '?' + urlencode(params), kind='graph', token=token, maximum=MAX_JSON_BYTES)
    try:
        data = json.loads(body)
        if mime != 'application/json' or not isinstance(data, dict) or 'error' in data:
            raise ValueError
        return data
    except (ValueError, UnicodeError):
        raise InstagramError('Instagram ha devuelto una respuesta no válida.') from None


def post_shortcode(value: str) -> str:
    try:
        url = urlsplit(value)
        if url.scheme != 'https' or url.hostname not in ('www.instagram.com', 'instagram.com') or url.username or url.password or url.port not in (None, 443):
            return ''
        match = re.fullmatch(r'/(?:[A-Za-z0-9_.]+/)?(?:p|reel)/([A-Za-z0-9_-]{1,100})/?', url.path)
        return match[1] if match else ''
    except (TypeError, ValueError):
        return ''


def _candidate(row: dict, hashtag: str) -> dict | None:
    if not isinstance(row, dict):
        return None
    identifier = str(row.get('id', ''))
    if not re.fullmatch(r'[0-9]{1,40}', identifier):
        return None
    caption = row.get('caption', '')
    if not isinstance(caption, str):
        return None
    if hashtag and not re.search(r'(?<!\w)#' + re.escape(hashtag) + r'(?!\w)', caption, re.I):
        return None
    shortcode = post_shortcode(row.get('permalink', ''))
    if not shortcode:
        return None
    try:
        timestamp = datetime.fromisoformat(str(row['timestamp']).replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    media_type = row.get('media_type')
    media_url = row.get('media_url')
    if media_type == 'CAROUSEL_ALBUM':
        children = row.get('children', {})
        children = children.get('data', []) if isinstance(children, dict) else []
        if not isinstance(children, list):
            return None
        media_url = next((child.get('media_url') for child in children[:50] if isinstance(child, dict) and child.get('media_type') == 'IMAGE'), None)
    elif media_type != 'IMAGE':
        return None
    if not isinstance(media_url, str) or not _url_allowed(media_url, 'media'):
        return None
    return {'id': identifier, 'caption': caption[:2200], 'timestamp': timestamp.astimezone(timezone.utc).isoformat(),
            'url': 'https://www.instagram.com/p/' + shortcode + '/', 'mediaType': media_type, '_download': media_url}


def _image_extension(body: bytes, mime: str) -> str:
    if mime == 'image/jpeg' and body.startswith(b'\xff\xd8\xff') and body.endswith(b'\xff\xd9'):
        return '.jpg'
    if mime == 'image/png' and body.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in body[-12:]:
        return '.png'
    if mime == 'image/webp' and len(body) >= 16 and body[:4] == b'RIFF' and body[8:12] == b'WEBP':
        return '.webp'
    raise InstagramError('La fotografía de Instagram no tiene un formato permitido.')


def _unsafe_link(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, 'is_junction', lambda: False)())


def sync_feed(output_dir: Path, token: str, user_id: str, username: str = 'fuem83', version: str = 'v26.0', hashtag: str = '', limit: int = 24) -> dict:
    """Fetch first, commit last. A failed request leaves the previous feed intact.

    The output directory is private until the caller publishes the two public
    resources. Retained old image files support visitors with cached old JSON.
    """
    if not token or any(ord(c) < 33 or ord(c) > 126 for c in token) or len(token) > 8192:
        raise InstagramError('Falta una autorización válida de Instagram.')
    if not re.fullmatch(r'[0-9]{1,40}', str(user_id)) or not re.fullmatch(r'[A-Za-z0-9_.]{1,30}', username) or not re.fullmatch(r'v[0-9]{1,3}\.0', version):
        raise InstagramError('La configuración de Instagram no es válida.')
    if not isinstance(limit, int) or not 1 <= limit <= 50 or not re.fullmatch(r'\w{0,80}', hashtag):
        raise InstagramError('El filtro o el límite de Instagram no son válidos.')
    account = _graph(version + '/' + user_id, {'fields': 'id,username'}, token)
    if str(account.get('id')) != user_id or str(account.get('username', '')).lower() != username.lower():
        raise InstagramError('La autorización no corresponde a la cuenta de Instagram del club configurada.')
    found, after = {}, ''
    for _ in range(MAX_PAGES):
        params = {'fields': MEDIA_FIELDS, 'limit': '50'}
        if after:
            params['after'] = after
        data = _graph(version + '/' + user_id + '/media', params, token)
        if not isinstance(data.get('data'), list) or len(data['data']) > 50:
            raise InstagramError('La lista de publicaciones de Instagram no es válida.')
        for row in data['data']:
            candidate = _candidate(row, hashtag)
            if candidate:
                found[candidate['id']] = candidate
        paging = data.get('paging') or {}
        if not isinstance(paging, dict):
            raise InstagramError('La paginación de Instagram no es válida.')
        cursors = paging.get('cursors')
        cursor = cursors.get('after') if isinstance(cursors, dict) else None
        # Never follow paging.next: it can carry a token or point to another host.
        if not paging.get('next') or cursor == after:
            break
        if not isinstance(cursor, str) or not cursor or len(cursor) > 4096:
            raise InstagramError('La paginación de Instagram no es válida.')
        after = cursor
    posts = sorted(found.values(), key=lambda row: row['timestamp'], reverse=True)[:limit]
    output_dir = Path(output_dir)
    if _unsafe_link(output_dir):
        raise InstagramError('El destino de Instagram no puede ser un enlace simbólico.')
    output_dir = output_dir.resolve()
    if _unsafe_link(output_dir / 'instagram-media') or _unsafe_link(output_dir / 'instagram-feed.json'):
        raise InstagramError('El destino de Instagram no puede contener enlaces simbólicos.')
    output_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.instagram-stage-', dir=output_dir))
    try:
        media_dir = staging / 'instagram-media'
        media_dir.mkdir()
        for post in posts:
            body, mime = _request(post.pop('_download'), kind='media', maximum=MAX_IMAGE_BYTES)
            extension = _image_extension(body, mime)
            filename = post['id'] + '-' + hashlib.sha256(body).hexdigest()[:12] + extension
            (media_dir / filename).write_bytes(body)
            post['image'] = './instagram-media/' + filename
        result = {'schema': 1, 'updatedAt': datetime.now(timezone.utc).isoformat(), 'username': username, 'posts': posts}
        # Caption length is in characters, while the public budget is in bytes.
        # Emoji-heavy captions can otherwise exceed the browser's byte budget.
        while len((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')) > PUBLIC_FEED_MAX_BYTES:
            for post in posts:
                post['caption'] = post['caption'][:len(post['caption']) // 2]
        old_file = output_dir / 'instagram-feed.json'
        if old_file.is_file():
            try:
                old = json.loads(old_file.read_text(encoding='utf-8'))
                if old.get('schema') == 1 and old.get('username') == username and old.get('posts') == posts:
                    result['updatedAt'] = old['updatedAt']
            except (OSError, ValueError, KeyError, AttributeError):
                pass
        public_media = output_dir / 'instagram-media'
        public_media.mkdir(exist_ok=True)
        for source in media_dir.iterdir():
            target = public_media / source.name
            if _unsafe_link(target):
                raise InstagramError('El destino de una fotografía no es seguro.')
            source.replace(target)
        staged_feed = staging / 'instagram-feed.json'
        staged_feed.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        staged_feed.replace(old_file)
        return result
    finally:
        shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description='Actualizar fotografías públicas del Instagram autorizado del club.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--hashtag', default='')
    parser.add_argument('--limit', type=int, default=24)
    args = parser.parse_args()
    try:
        result = sync_feed(args.output, os.environ.get('FUEM_INSTAGRAM_ACCESS_TOKEN', ''), os.environ.get('FUEM_INSTAGRAM_USER_ID', ''),
                           os.environ.get('FUEM_INSTAGRAM_USERNAME', 'fuem83'), os.environ.get('FUEM_INSTAGRAM_API_VERSION', 'v26.0'), args.hashtag.lstrip('#'), args.limit)
        print(json.dumps({'status': 'updated', 'posts': len(result['posts']), 'updatedAt': result['updatedAt']}))
    except InstagramError as exc:
        parser.exit(2, str(exc) + '\n')
    except OSError:
        parser.exit(2, 'No se ha podido guardar la actualización. Se conserva la versión anterior.\n')


if __name__ == '__main__':
    main()
