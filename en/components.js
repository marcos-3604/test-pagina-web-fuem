(() => {
  const stage = document.querySelector("#component-stage");
  const toggle = document.querySelector("#explode-toggle");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  const parts = {
    body: ["EXTERIOR STRUCTURE","BODYWORK","It gives the car its shape and brings its systems together visually. Its design and manufacture connect the work of several team departments."],
    "front-wheel": ["CONTACT WITH THE TRACK","FRONT WHEEL","It transfers steering, cornering and braking forces to the track. Tyre, rim and suspension work together to give the driver precise control."],
    "rear-wheel": ["TRACTION AND GRIP","REAR WHEEL","It transfers power to the ground. Grip and setup affect acceleration and the car\u2019s behaviour as it exits a corner."],
    "front-wing": ["AERODYNAMICS","FRONT WING","It is one of the first components to meet the airflow. Its geometry contributes to the car\u2019s aerodynamic development and balance."],
    "rear-wing": ["AERODYNAMICS","REAR WING","The rear assembly contributes to the car\u2019s aerodynamic behaviour. Its development brings together design, simulation, manufacturing and validation."]
  };
  if (stage && toggle) {
    toggle.addEventListener("click", () => {
      const expanded = !stage.classList.contains("exploded");
      stage.classList.toggle("exploded", expanded);
      toggle.setAttribute("aria-pressed", String(expanded));
      toggle.firstChild.textContent = expanded ? "Assemble components " : "Separate components ";
      document.querySelector("#stage-mode").textContent = expanded ? "EXPLODED VIEW" : "ASSEMBLED";
      stage.setAttribute("aria-label", expanded ? "Separated exterior components of the car: bodywork, wheels and wings" : "Photographic view of the car with its components assembled");
      const bounds=stage.getBoundingClientRect();
      if(bounds.bottom>innerHeight-25 || bounds.top<10)stage.scrollIntoView({behavior:reduce.matches?"instant":"smooth",block:"center"});
    });
    document.querySelectorAll("[data-part]").forEach(button => button.addEventListener("click", () => {
      const key = button.dataset.part;
      stage.dataset.selected = key;
      stage.classList.add("has-selection");
      document.querySelectorAll("[data-part]").forEach(other => other.setAttribute("aria-pressed", String(other === button)));
      const [category,title,copy] = parts[key];
      document.querySelector("#part-category").textContent = category;
      document.querySelector("#part-title").textContent = title;
      document.querySelector("#part-copy").textContent = copy;
    }));
  }

  const video = document.querySelector("#hero-video");
  const hero = document.querySelector(".home-hero");
  const credit = document.querySelector("#hero-media-credit");
  const scenes = {
    night: {src:video?.dataset.nightSrc || "../assets/v6/fss2026-night-1080.mp4",poster:"../assets/v6/fss2026-night-poster-1080.jpg",credit:"FORMULA STUDENT SPAIN 2026 / ORIGINAL VIDEO \u2197",url:"https://www.youtube.com/watch?v=zXaHyCGoVnM"},
    fuem: {src:"../assets/v3/fuem-ready-to-race.mp4",poster:"../assets/v3/fuem-ready-to-race-poster.jpg",credit:"FUEM IN MOTION / ORIGINAL REEL @FUEM83 \u2197",url:"https://www.instagram.com/fuem83/reel/DasRRnrO1uA/"}
  };
  const qualityButton = document.querySelector("#video-quality");
  function updateQuality() {
    if (!qualityButton) return;
    const lite = video.dataset.quality === "900p-lite";
    qualityButton.hidden = hero.dataset.scene !== "night";
    qualityButton.textContent = lite ? "Quality: lightweight" : "Quality: HD";
    qualityButton.setAttribute("aria-pressed", String(lite));
    qualityButton.setAttribute("aria-label", lite ? "Use the 1080p Full HD video" : "Use the lightweight video");
  }
  function selectScene(key, preservePause=false) {
    const scene=scenes[key];
    const wasPaused=video.paused;
    video.pause();
    video.autoplay=!reduce.matches&&(!preservePause||!wasPaused);
    video.poster=scene.poster;
    video.src=key==="night" ? video.dataset.nightSrc : scene.src;
    hero.dataset.scene=key;
    credit.href=scene.url;
    credit.textContent=scene.credit;
    document.querySelectorAll("[data-scene-choice]").forEach(other=>other.setAttribute("aria-pressed",String(other.dataset.sceneChoice===key)));
    updateQuality();
    video.load();
    if(!preservePause)video.dispatchEvent(new Event("fuem:scenechange"));
    if(!reduce.matches&&(!preservePause||!wasPaused))video.play().catch(()=>{});
  }
  document.querySelectorAll("[data-scene-choice]").forEach(button => button.addEventListener("click", () => {
    if (hero.dataset.scene !== button.dataset.sceneChoice) selectScene(button.dataset.sceneChoice);
  }));
  qualityButton?.addEventListener("click",()=>{
    const useLite=video.dataset.quality!=="900p-lite";
    video.dataset.quality=useLite?"900p-lite":"1080p";
    video.dataset.nightSrc=useLite?video.dataset.nightLite:video.dataset.nightHd;
    selectScene("night",true);
  });
  if(video)updateQuality();
})();
