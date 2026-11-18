// Security dashboard: polls /api/incidents, draws table + map, updates status.
(function () {
  var map = null, layer = null, first = true;
  if (window.L) {
    map = L.map('map').setView([25.18, 75.83], 13);           // default view; auto-fits to incidents
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
    layer = L.layerGroup().addTo(map);
  } else { document.getElementById('map').textContent = 'Map needs internet (Leaflet could not load). The table below still works.'; }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var colors = { high: '#c62a20', medium: '#b7791f', low: '#0f6b5c' };

  function load() {
    var qs = new URLSearchParams({ status: val('f-status'), severity: val('f-sev'), q: val('f-q') });
    fetch('/api/incidents?' + qs).then(function (r) { return r.json(); }).then(render).catch(function () {});
  }
  function val(id) { return document.getElementById(id).value; }

  function render(rows) {
    var active = rows.filter(function (r) { return r.status !== 'resolved'; });
    document.getElementById('stats').innerHTML =
      '<div><b>' + active.length + '</b>active</div><div><b>' + active.filter(function (r) { return r.severity === 'high'; }).length +
      '</b>high severity</div><div><b>' + rows.filter(function (r) { return r.status === 'responding'; }).length + '</b>responding</div><div><b>' + rows.length + '</b>shown</div>';

    document.getElementById('rows').innerHTML = rows.length ? rows.map(function (r) {
      var where = (r.lat != null) ? '<a target="_blank" rel="noopener" href="https://www.openstreetmap.org/?mlat=' + r.lat + '&mlon=' + r.lng + '#map=18/' + r.lat + '/' + r.lng + '">map</a>' : 'no GPS';
      var opts = ['open', 'responding', 'resolved'].map(function (s) { return '<option' + (s === r.status ? ' selected' : '') + '>' + s + '</option>'; }).join('');
      return '<tr class="' + esc(r.severity) + ' ' + esc(r.status) + '"><td><a href="/incident/' + r.id + '">' + r.id + '</a></td><td>' + esc(r.created_at.slice(5, 16)) +
        '</td><td>' + esc(r.user_name) + '<br><span class="note">' + esc(r.user_phone) + '</span></td><td>' + esc(r.message) +
        '</td><td>' + esc(r.category.replace('_', ' ')) + '</td><td><span class="badge sev-' + esc(r.severity) + '">' + esc(r.severity) + '</span></td><td>' + where +
        '</td><td><select data-id="' + r.id + '" aria-label="Status of incident ' + r.id + '">' + opts + '</select></td></tr>';
    }).join('') : '<tr><td colspan="8">No incidents match.</td></tr>';

    if (map) {
      layer.clearLayers(); var pts = [];
      active.forEach(function (r) {
        if (r.lat == null) return; pts.push([r.lat, r.lng]);
        L.circleMarker([r.lat, r.lng], { radius: 9, color: colors[r.severity] || '#333', fillOpacity: .7 })
          .bindPopup('<b>#' + r.id + ' ' + esc(r.category) + '</b><br>' + esc(r.message)).addTo(layer);
      });
      if (pts.length && first) { map.fitBounds(pts, { maxZoom: 17, padding: [30, 30] }); first = false; }
    }
  }

  document.getElementById('rows').addEventListener('change', function (e) {
    if (e.target.tagName !== 'SELECT') return;
    fetch('/api/incident/' + e.target.dataset.id + '/status', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: e.target.value }) }).then(load);
  });
  ['f-status', 'f-sev'].forEach(function (id) { document.getElementById(id).addEventListener('change', load); });
  document.getElementById('f-q').addEventListener('input', function () { clearTimeout(window._t); window._t = setTimeout(load, 300); });
  load(); setInterval(load, 5000);
})();
