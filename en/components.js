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

})();
