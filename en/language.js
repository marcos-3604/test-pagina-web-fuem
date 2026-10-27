// Keep the visitor on the equivalent page, including its section when available.
document.querySelectorAll("[data-language]").forEach(link => {
  const target=new URL(link.href);
  target.hash=location.hash;
  link.href=target.href;
  link.addEventListener("click",()=>{
    try { localStorage.setItem("fuem-language",link.dataset.language); } catch {}
  });
});
