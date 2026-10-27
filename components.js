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

})();
