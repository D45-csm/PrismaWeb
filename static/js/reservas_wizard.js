/* Asistente paso a paso para #reservaForm (no cambia ids, nombres ni la lógica de script.js) */
(function () {
  var form = document.getElementById('reservaForm');
  if (!form) return;
  var steps = Array.prototype.slice.call(form.querySelectorAll(':scope > .form-section-block'));
  if (steps.length < 2) return;
  var submitBlock = form.querySelector('.form-submit-block');
  var names = ['Modalidad', 'Tus datos', 'Postres', 'Detalles'];
  var icons = ['fa-utensils', 'fa-calendar-days', 'fa-cake-candles', 'fa-wand-magic-sparkles'];
  var cur = 0;

  form.classList.add('wizard');

  var prog = document.createElement('div');
  prog.className = 'wz-progress';
  prog.innerHTML = '<div class="wz-progress-fill"></div>' + steps.map(function (_, i) {
    return '<button type="button" class="wz-step" data-i="' + i + '"><span class="wz-dot"><i class="fas ' +
      (icons[i] || 'fa-circle') + '"></i></span><span class="wz-name">' + (names[i] || ('Paso ' + (i + 1))) + '</span></button>';
  }).join('');
  form.insertBefore(prog, steps[0]);

  var nav = document.createElement('div');
  nav.className = 'wz-nav';
  nav.innerHTML = '<button type="button" class="wz-btn wz-btn--back" hidden><i class="fas fa-arrow-left"></i> Atrás</button>' +
    '<button type="button" class="wz-btn wz-btn--next">Continuar <i class="fas fa-arrow-right"></i></button>';
  if (submitBlock) form.insertBefore(nav, submitBlock.nextSibling); else form.appendChild(nav);
  if (submitBlock) form.insertBefore(submitBlock, nav);

  var back = nav.querySelector('.wz-btn--back');
  var next = nav.querySelector('.wz-btn--next');
  var fill = prog.querySelector('.wz-progress-fill');
  var dots = prog.querySelectorAll('.wz-step');

  function fields(i) {
    return Array.prototype.slice.call(steps[i].querySelectorAll('input,select,textarea')).filter(function (f) {
      return !f.disabled && !f.closest('[hidden]') && f.type !== 'hidden';
    });
  }
  function validate(i) {
    var list = fields(i);
    for (var k = 0; k < list.length; k++) {
      if (!list[k].checkValidity()) { list[k].reportValidity(); return false; }
    }
    return true;
  }
  function show(i, scroll) {
    cur = i;
    steps.forEach(function (s, k) { s.classList.toggle('is-current', k === i); });
    dots.forEach(function (d, k) {
      d.classList.toggle('is-current', k === i);
      d.classList.toggle('is-done', k < i);
    });
    var pct = steps.length > 1 ? (i / (steps.length - 1)) * 84 : 0;
    fill.style.width = pct + '%';
    back.hidden = i === 0;
    form.classList.toggle('is-last', i === steps.length - 1);
    if (scroll !== false) {
      var top = form.closest('.luxury-form-card');
      if (top) window.scrollTo({ top: top.getBoundingClientRect().top + window.pageYOffset - 90, behavior: 'smooth' });
    }
  }

  next.addEventListener('click', function () {
    if (!validate(cur)) return;
    if (cur < steps.length - 1) show(cur + 1);
  });
  back.addEventListener('click', function () { if (cur > 0) show(cur - 1); });
  dots.forEach(function (d) {
    d.addEventListener('click', function () {
      var t = parseInt(d.getAttribute('data-i'), 10);
      if (t < cur) show(t);
    });
  });
  form.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA' && e.target.tagName !== 'BUTTON' && cur < steps.length - 1) {
      e.preventDefault();
      next.click();
    }
  });
  // El botón "Reservar ahora" flotante lleva al asistente
  show(0, false);
})();
