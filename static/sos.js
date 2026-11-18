// Captures GPS (if allowed) and sends the SOS text + location to Flask.
(function () {
  var pos = null;
  var statusEl = document.getElementById('loc-status');
  var msg = document.getElementById('msg');
  var btn = document.getElementById('send');
  var errEl = document.getElementById('err');

  function setStatus(text, cls) { statusEl.textContent = text; statusEl.className = 'loc ' + (cls || ''); }

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(function (p) {
      pos = { lat: p.coords.latitude, lng: p.coords.longitude, accuracy: p.coords.accuracy };
      setStatus('Location ready (accurate to about ' + Math.round(p.coords.accuracy) + ' m)', 'ok');
    }, function () {
      setStatus('Location not available. Your SOS will still be sent. Mention where you are in your message.', 'warn');
    }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 });
  } else {
    setStatus('This browser has no location support. Mention where you are in your message.', 'warn');
  }

  document.querySelectorAll('.chip').forEach(function (c) {
    c.addEventListener('click', function () {
      msg.value = c.dataset.text; msg.focus();
      msg.setSelectionRange(msg.value.length, msg.value.length);
    });
  });

  btn.addEventListener('click', function () {
    var text = msg.value.trim();
    if (!text) { errEl.textContent = 'Please type what is happening, even a few words.'; errEl.hidden = false; msg.focus(); return; }
    errEl.hidden = true; btn.disabled = true; btn.textContent = 'SENDING…';
    var body = { text: text };
    if (pos) { body.lat = pos.lat; body.lng = pos.lng; body.accuracy = pos.accuracy; }
    fetch('/api/sos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.j.error || 'Could not send.');
        window.location = res.j.url;
      })
      .catch(function (e) {
        errEl.textContent = e.message + ' Call 112 if you are in danger.'; errEl.hidden = false;
        btn.disabled = false; btn.textContent = 'SEND SOS';
      });
  });
})();
