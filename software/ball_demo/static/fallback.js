// Read-only manual-fallback screen: live video, target box (drawn by the server),
// centre/error indicator and the steering status. It sends no operator commands.
const $ = (id) => document.getElementById(id);
let lastUpdate = 0;

function render(state) {
  lastUpdate = Date.now();
  $('stale').classList.add('hidden');
  $('steering').textContent = state.steering_status;
  $('steering').classList.toggle('available', Boolean(state.steering_available));
  const stale = state.frame_age_ms === null || state.frame_age_ms >= state.settings.stale_ms;
  $('stale').textContent = stale ? 'Video stale · no fresh frames' : 'Video connection lost';
  $('stale').classList.toggle('hidden', !stale);
  const detection = stale ? null : state.detection;
  $('marker').classList.toggle('hidden', !detection);
  if (detection) $('marker').style.left = `${50 + Math.max(-1, Math.min(1, detection.error)) * 50}%`;
  $('target').textContent = detection ? 'Target tracked' : 'Target not found';
  $('error').textContent = detection ? `Centre error ${detection.error >= 0 ? '+' : ''}${detection.error.toFixed(3)}` : 'Centre error —';
  $('source').textContent = state.source_label;
  const live = state.source.kind === 'camera';
  $('source-warning').classList.toggle('hidden', live);
  $('source-warning').textContent = live ? '' : state.synthetic_fallback ? 'SYNTHETIC VIDEO — no camera configured, NOT live FPV' : `${state.source_label} input — not live FPV`;
}

const events = new EventSource('/api/events');
events.onmessage = (message) => render(JSON.parse(message.data));
events.onopen = () => { $('video').src = `/api/preview?${Date.now()}`; };
setInterval(() => {
  if (Date.now() - lastUpdate > 1500) {
    $('stale').textContent = 'Video connection lost';
    $('stale').classList.remove('hidden');
    $('marker').classList.add('hidden');
  }
}, 500);
