(() => {
  const stage = document.querySelector('#component-stage');
  const toggle = document.querySelector('#explode-toggle');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const parts = {
    body: ["ESTRUCTURA VISUAL","CARROCER\u00cdA","Da forma al monoplaza e integra visualmente sus sistemas. Su dise\u00f1o y fabricaci\u00f3n conectan el trabajo de distintas \u00e1reas del equipo."],
    'front-wheel': ["CONTACTO CON EL ASFALTO","RUEDA DELANTERA","Transmite la direcci\u00f3n, el apoyo y la frenada al asfalto. Neum\u00e1tico, llanta y suspensi\u00f3n trabajan como un conjunto para dar precisi\u00f3n al piloto."],
    'rear-wheel': ["TRACCI\u00d3N Y APOYO","RUEDA TRASERA","Lleva la entrega de potencia al suelo. La adherencia y la puesta a punto influyen en la aceleraci\u00f3n y en el comportamiento del coche a la salida de curva."],
    'front-wing': ["AERODIN\u00c1MICA","ALER\u00d3N DELANTERO","Es uno de los primeros elementos que encuentra el aire. Su geometr\u00eda forma parte del estudio aerodin\u00e1mico del monoplaza y de su equilibrio."],
    'rear-wing': ["AERODIN\u00c1MICA","ALER\u00d3N TRASERO","El conjunto trasero participa en el comportamiento aerodin\u00e1mico del coche. Su desarrollo conecta dise\u00f1o, simulaci\u00f3n, fabricaci\u00f3n y validaci\u00f3n."]
  };
  if (stage && toggle) {
    toggle.addEventListener('click', () => {
      const expanded = !stage.classList.contains('exploded');
      stage.classList.toggle('exploded', expanded);
      toggle.setAttribute('aria-pressed', String(expanded));
      toggle.firstChild.textContent = expanded ? "Ensamblar componentes " : 'Separar componentes ';
      document.querySelector('#stage-mode').textContent = expanded ? 'VISTA SEPARADA' : 'ENSAMBLADO';
      stage.setAttribute('aria-label', expanded ? "Componentes exteriores del monoplaza separados: carrocer\u00eda, ruedas y alerones" : "Vista fotogr\u00e1fica del monoplaza con sus componentes ensamblados");
      const bounds=stage.getBoundingClientRect();
      if(bounds.bottom>innerHeight-25 || bounds.top<10)stage.scrollIntoView({behavior:reduce.matches?'instant':'smooth',block:'center'});
    });
    document.querySelectorAll('[data-part]').forEach(button => button.addEventListener('click', () => {
      const key = button.dataset.part;
      stage.dataset.selected = key;
      stage.classList.add('has-selection');
      document.querySelectorAll('[data-part]').forEach(other => other.setAttribute('aria-pressed', String(other === button)));
      const [category,title,copy] = parts[key];
      document.querySelector('#part-category').textContent = category;
      document.querySelector('#part-title').textContent = title;
      document.querySelector('#part-copy').textContent = copy;
    }));
  }

  const video = document.querySelector('#hero-video');
  const hero = document.querySelector('.home-hero');
  const credit = document.querySelector('#hero-media-credit');
  const scenes = {
    night: {src:video?.dataset.nightSrc || "./assets/v6/fss2026-night-1080.mp4",poster:"./assets/v6/fss2026-night-poster-1080.jpg",credit:"FORMULA STUDENT SPAIN 2026 / V\u00cdDEO ORIGINAL \u2197",url:"https://www.youtube.com/watch?v=zXaHyCGoVnM"},
    fuem: {src:"./assets/v3/fuem-ready-to-race.mp4",poster:"./assets/v3/fuem-ready-to-race-poster.jpg",credit:"FUEM EN MOVIMIENTO / REEL ORIGINAL @FUEM83 \u2197",url:"https://www.instagram.com/fuem83/reel/DasRRnrO1uA/"}
  };
  const qualityButton = document.querySelector('#video-quality');
  function updateQuality() {
    if (!qualityButton) return;
    const lite = video.dataset.quality === '900p-lite';
    qualityButton.hidden = hero.dataset.scene !== 'night';
    qualityButton.textContent = lite ? 'Calidad: ligera' : 'Calidad: HD';
    qualityButton.setAttribute('aria-pressed', String(lite));
    qualityButton.setAttribute('aria-label', lite ? "Usar v\u00eddeo Full HD de 1080p" : "Usar versi\u00f3n ligera del v\u00eddeo");
  }
  function selectScene(key, preservePause=false) {
    const scene=scenes[key];
    const wasPaused=video.paused;
    video.pause();
    video.autoplay=!reduce.matches&&(!preservePause||!wasPaused);
    video.poster=scene.poster;
    video.src=key==='night' ? video.dataset.nightSrc : scene.src;
    hero.dataset.scene=key;
    credit.href=scene.url;
    credit.textContent=scene.credit;
    document.querySelectorAll('[data-scene-choice]').forEach(other=>other.setAttribute('aria-pressed',String(other.dataset.sceneChoice===key)));
    updateQuality();
    video.load();
    if(!preservePause)video.dispatchEvent(new Event('fuem:scenechange'));
    if(!reduce.matches&&(!preservePause||!wasPaused))video.play().catch(()=>{});
  }
  document.querySelectorAll('[data-scene-choice]').forEach(button => button.addEventListener('click', () => {
    if (hero.dataset.scene !== button.dataset.sceneChoice) selectScene(button.dataset.sceneChoice);
  }));
  qualityButton?.addEventListener('click',()=>{
    const useLite=video.dataset.quality!=='900p-lite';
    video.dataset.quality=useLite?'900p-lite':'1080p';
    video.dataset.nightSrc=useLite?video.dataset.nightLite:video.dataset.nightHd;
    selectScene('night',true);
  });
  if(video)updateQuality();
})();
