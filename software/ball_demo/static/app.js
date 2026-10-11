const element = (id) => document.getElementById(id);
const displayName = (value) => value.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase());

let operatorToken = '';
let lastUpdate = 0;
let currentState = null;
let playback = null;
let playbackIndex = 0;
let playing = false;
let playbackClock = 0;

const settingFields = {
  gain: 'gain', max_yaw: 'max-yaw', deadband: 'deadband', smoothing: 'smoothing',
  slew_per_s: 'slew', direction: 'direction', hue_low: 'hue-low', hue_high: 'hue-high',
  saturation_min: 'saturation-min', value_min: 'value-min', min_area: 'min-area', max_area: 'max-area',
  target_mode: 'target-mode', tag_id: 'tag-id', tag_size_m: 'tag-size', land_range_m: 'land-range',
  camera_hfov_deg: 'camera-hfov',
};
const textSettings = new Set(['target_mode']);

function renderState(state) {
  currentState = state;
  lastUpdate = Date.now();
  element('connection').textContent = 'Connected';
  element('connection').classList.remove('stale');
  element('source-label').textContent = state.source_label;
  element('synthetic-banner').classList.toggle('hidden', !state.synthetic_fallback);
  element('scenario-label').textContent = displayName(state.source.scenario || state.source.kind);
  element('preview').alt = `${state.source_label.toLowerCase()} video with target detection outline`;
  element('session-id').textContent = `Session ${state.session}`;
  element('state').textContent = state.judge?.active ? `JUDGE · yaw ${state.judge.yaw}` : state.state;
  element('state').dataset.state = state.state;
  const yawUnit = document.createElement('em');
  yawUnit.textContent = ' / 1000';
  element('yaw').replaceChildren(String(state.yaw), yawUnit);
  element('error').textContent = state.detection ? state.detection.error.toFixed(3) : '—';
  element('assistance').textContent = state.enabled ? 'Enabled' : 'Disabled';
  element('frame-age').textContent = state.frame_age_ms === null ? '—' : `${Math.round(state.frame_age_ms)} ms`;
  element('ack-age').textContent = `${Math.round(state.ack_age_ms)} ms`;
  element('ack-yaw').textContent = state.ack_yaw;
  element('quality').textContent = state.detection ? `${Math.round(state.detection.quality * 100)} / 100` : '—';
  element('bridge').textContent = state.bridge;
  element('yaw-marker').style.left = `${50 + state.yaw / 20}%`;
  element('fault-box').classList.toggle('hidden', !state.fault);
  element('fault-box').textContent = state.fault ? `${state.fault}. Assistance disabled; requested yaw is zero.` : '';
  element('limits-note').textContent = `Acquire: ${state.settings.acquire_frames} frames. Frame limit: ${state.settings.stale_ms} ms. ACK limit: ${state.settings.ack_ms} ms.`;
  const guidance = state.guidance;
  element('guidance').classList.toggle('hidden', !guidance);
  if (guidance) {
    const seen = (guidance.tags_seen || []).map((t) => `${t.id}${t.name ? ` ${t.name}` : ''}`).join(', ');
    element('guidance').textContent = `${guidance.stage}: ${guidance.cue}${seen ? ` · tags in view: ${seen}` : ''}`;
    element('guidance').dataset.stage = guidance.stage;
  }
  renderFallback(state);
  if (typeof renderNavigation === 'function') renderNavigation(state.navigation);
}

function videoIsStale(state) {
  return state.frame_age_ms === null || state.frame_age_ms >= state.settings.stale_ms;
}

function renderFallback(state) {
  const stale = videoIsStale(state);
  element('video-stale').classList.toggle('hidden', !stale);
  if (stale) {
    element('error').textContent = '—';
    element('quality').textContent = '—';
  }
  element('steering-status').textContent = state.steering_status;
  element('steering-status').classList.toggle('available', Boolean(state.steering_available));
  const marker = element('error-marker');
  marker.classList.toggle('hidden', !state.detection || stale);
  if (state.detection) marker.style.left = `${50 + Math.max(-1, Math.min(1, state.detection.error)) * 50}%`;
}

// Operator lease: assistance enabled from this page stays on only while heartbeats arrive.
setInterval(() => {
  if (!operatorToken) return;
  fetch('/api/operator/heartbeat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${operatorToken}` },
    body: '{}',
  }).catch(() => {});
}, 300);

// Normalised position of a click on the letterboxed (object-fit: contain) preview, or null.
function picturePosition(image, clientX, clientY) {
  const box = image.getBoundingClientRect();
  if (!image.naturalWidth || !image.naturalHeight || !box.width || !box.height) return null;
  const scale = Math.min(box.width / image.naturalWidth, box.height / image.naturalHeight);
  const width = image.naturalWidth * scale, height = image.naturalHeight * scale;
  const x = (clientX - box.left - (box.width - width) / 2) / width;
  const y = (clientY - box.top - (box.height - height) / 2) / height;
  return x >= 0 && x <= 1 && y >= 0 && y <= 1 ? { x, y } : null;
}

function setPicking(on) {
  element('pick-toggle').setAttribute('aria-pressed', String(on));
  element('preview').parentElement.classList.toggle('picking', on);
  if (on) element('operator-message').textContent = 'Click the coloured target in the video.';
}
element('pick-toggle').onclick = () => setPicking(element('pick-toggle').getAttribute('aria-pressed') !== 'true');
element('preview').onclick = async (event) => {
  if (!operatorToken || element('pick-toggle').getAttribute('aria-pressed') !== 'true') return;
  const position = picturePosition(element('preview'), event.clientX, event.clientY);
  if (!position) return;
  setPicking(false);
  try {
    const response = await fetch('/api/operator/pick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${operatorToken}` },
      body: JSON.stringify({ ...position, apply: true }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : JSON.stringify(result.detail));
    renderState(result.snapshot);
    populateOperatorFields();
    const values = result.settings;
    element('operator-message').textContent = (result.warnings[0] || `Colour range set: hue ${values.hue_low}–${values.hue_high}, saturation ≥ ${values.saturation_min}, value ≥ ${values.value_min}.`) + ' Assistance disabled.';
  } catch (error) {
    element('operator-message').textContent = error.message;
  }
};

function markDisconnected(message) {
  element('connection').textContent = message;
  element('connection').classList.add('stale');
  element('video-stale').classList.remove('hidden');
  element('error-marker').classList.add('hidden');
  if (typeof navigationDisconnected === 'function') navigationDisconnected();
}

const stateStream = new EventSource('/api/events');
stateStream.onmessage = (event) => renderState(JSON.parse(event.data));
stateStream.onerror = () => markDisconnected('Disconnected');
stateStream.onopen = async () => {
  try {
    const response = await fetch('/api/state');
    if (!response.ok) throw new Error('State unavailable');
    renderState(await response.json());
    element('preview').src = '/api/preview';
  } catch {
    markDisconnected('Reconnecting');
  }
};
setInterval(() => {
  if (Date.now() - lastUpdate > 1500) markDisconnected('Stale / reconnecting');
}, 500);

function selectView(view) {
  for (const name of ['monitor', 'sandbox']) {
    const selected = name === view;
    element(`${name}-view`).classList.toggle('hidden', !selected);
    element(`${name}-tab`).classList.toggle('selected', selected);
    element(`${name}-tab`).setAttribute('aria-selected', String(selected));
  }
  if (view === 'monitor') {
    playing = false;
    element('sandbox-play').textContent = 'Play';
  } else {
    drawPlayback();
  }
  document.title = `Ball Drone — ${displayName(view)}`;
}
element('monitor-tab').onclick = () => selectView('monitor');
element('sandbox-tab').onclick = () => selectView('sandbox');

// Operator commands go out one at a time, in order. A disable also cancels any enable still
// waiting in the queue, so a neutral request can never be overtaken by an older enable.
let commandChain = Promise.resolve();
let neutralEpoch = 0;
function operatorAction(path, data) {
  const neutral = (path === 'assist' && data.enabled === false) || (path === 'navigation' && data.action === 'disable');
  if (neutral) neutralEpoch += 1;
  const epoch = neutralEpoch;
  const run = () => {
    if (((path === 'assist' && data.enabled === true) || (path === 'navigation' && data.action === 'resume')) && epoch !== neutralEpoch) {
      throw new Error('Enable cancelled: a disable was requested');
    }
    return sendOperator(path, data);
  };
  const result = commandChain.then(run, run);
  commandChain = result.catch(() => {});
  return result;
}

async function sendOperator(path, data) {
  const response = await fetch(`/api/operator/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${operatorToken}` },
    body: JSON.stringify(data),
  });
  const state = await response.json();
  if (!response.ok) throw new Error(typeof state.detail === 'string' ? state.detail : JSON.stringify(state.detail));
  renderState(state);
  return state;
}

function bindAction(id, path, data, message) {
  element(id).onclick = async () => {
    try {
      await operatorAction(path, data());
      element('operator-message').textContent = message;
    } catch (error) {
      element('operator-message').textContent = error.message;
    }
  };
}

function renderSourceFields() {
  const synthetic = element('source-kind').value === 'synthetic';
  element('scenario-field').classList.toggle('hidden', !synthetic);
  element('source-path-field').classList.toggle('hidden', synthetic);
}
element('source-kind').onchange = renderSourceFields;

function populateOperatorFields() {
  if (!currentState) return;
  for (const [setting, id] of Object.entries(settingFields)) element(id).value = currentState.settings[setting];
  element('source-kind').value = currentState.source.kind;
  element('operator-scenario').value = currentState.source.scenario || 'moving';
  element('source-path').value = currentState.source.path ?? currentState.source.device ?? '';
  renderSourceFields();
}

element('operator-open').onclick = () => element('login').showModal();
element('login-cancel').onclick = () => element('login').close();
// Locking hands back control: request neutral first, then forget the token.
element('operator-lock').onclick = async () => {
  try {
    await operatorAction('assist', { enabled: false });
  } catch (error) {
    element('operator-message').textContent = `Disable before lock failed: ${error.message}`;
  }
  operatorToken = '';
  element('operator-panel').classList.add('hidden');
};
element('login-form').onsubmit = async (event) => {
  event.preventDefault();
  operatorToken = element('token').value;
  try {
    const response = await fetch('/api/operator/access', { headers: { Authorization: `Bearer ${operatorToken}` } });
    if (!response.ok) throw new Error('Operator token required');
    populateOperatorFields();
    selectView('monitor');
    element('operator-panel').classList.remove('hidden');
    element('login').close();
    element('token').value = '';
    element('login-error').textContent = '';
  } catch (error) {
    operatorToken = '';
    element('login-error').textContent = error.message;
  }
};

bindAction('enable', 'assist', () => ({ enabled: true }), 'Assistance enabled. Waiting for stable acquisition.');
bindAction('disable', 'assist', () => ({ enabled: false }), 'Assistance disabled. Requested yaw: 0.');
bindAction('reset', 'reset', () => ({}), 'Reset to synthetic input; assistance disabled.');
bindAction('fault-apply', 'fault', () => ({ fault: element('bridge-fault').value }), 'Bridge setting applied.');
bindAction('source-apply', 'source', () => {
  const kind = element('source-kind').value;
  const source = { kind };
  if (kind === 'synthetic') source.scenario = element('operator-scenario').value;
  if (kind === 'recorded') source.path = element('source-path').value;
  if (kind === 'camera') source.device = Number(element('source-path').value || 0);
  return source;
}, 'Source changed. Assistance disabled.');
bindAction('settings-apply', 'settings', () => Object.fromEntries(
  Object.entries(settingFields).map(([setting, id]) => [setting, textSettings.has(setting) ? element(id).value : Number(element(id).value)]),
), 'Settings applied. Assistance disabled.');

function renderRoster(roster) {
  const list = element('roster-list');
  const rows = [...roster.people.map((p) => ({ ...p, role: 'follow' })), ...roster.landing_sites.map((s) => ({ ...s, role: 'landing pad' }))]
    .sort((a, b) => a.tag_id - b.tag_id);
  list.replaceChildren(...(rows.length ? rows.map((row) => {
    const item = document.createElement('li');
    item.textContent = `ID ${row.tag_id} · ${row.name} · ${row.role} · ${(row.size_m * 100).toFixed(1)} cm${row.enabled ? '' : ' (disabled)'}`;
    return item;
  }) : [Object.assign(document.createElement('li'), { textContent: `No tags yet${roster.path ? ` in ${roster.path}` : ''}.` })]));
}
async function loadRoster(reload = false) {
  try {
    const response = await fetch(reload ? '/api/operator/roster/reload' : '/api/operator/roster', {
      method: reload ? 'POST' : 'GET', headers: { Authorization: `Bearer ${operatorToken}` } });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Roster unavailable');
    renderRoster(body);
    if (reload) element('operator-message').textContent = 'Tags reloaded. Assistance disabled.';
  } catch (error) {
    element('operator-message').textContent = error.message;
  }
}
element('roster-reload').onclick = () => loadRoster(true);

async function judgeRequest(method, body) {
  try {
    const response = await fetch('/api/operator/judge', { method, headers: { Authorization: `Bearer ${operatorToken}`,
      'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Judge request failed');
    element('judge-info').textContent = `PIN ${data.pin} · judge page: ${location.origin}/judge · ` +
      `${data.active ? `ON (limit ±${data.max_yaw})` : 'off'}`;
    element('judge-max').value = data.max_yaw;
    if (body) element('operator-message').textContent = data.active ? 'Judge mode on: vision assistance disabled.' : 'Judge mode off. Yaw 0.';
  } catch (error) {
    element('operator-message').textContent = error.message;
  }
}
element('judge-on').onclick = () => judgeRequest('POST', { enabled: true, max_yaw: Number(element('judge-max').value) });
element('judge-off').onclick = () => judgeRequest('POST', { enabled: false });
document.querySelector('#judge-info').closest('details').addEventListener('toggle', (event) => { if (event.target.open) judgeRequest('GET'); });
document.querySelector('#roster-list').closest('details').addEventListener('toggle', (event) => { if (event.target.open) loadRoster(); });

async function loadPlayback() {
  playing = false;
  playbackIndex = 0;
  element('sandbox-play').textContent = 'Play';
  try {
    const response = await fetch(`/api/sandbox/${element('sandbox-scenario').value}`);
    if (!response.ok) throw new Error('Scene unavailable');
    playback = await response.json();
    drawPlayback();
  } catch (error) {
    element('sandbox-state').textContent = error.message;
  }
}

function drawPlayback() {
  if (!playback?.samples?.length) return;
  const sample = playback.samples[Math.min(playbackIndex, playback.samples.length - 1)];
  const canvas = element('sandbox-canvas');
  const context = canvas.getContext('2d');
  context.fillStyle = '#11171a';
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.strokeStyle = '#2b343b';
  context.lineWidth = 1;
  for (let x = 0; x < canvas.width; x += 80) {
    context.beginPath(); context.moveTo(x, 0); context.lineTo(x, canvas.height); context.stroke();
  }
  for (let y = 0; y < canvas.height; y += 80) {
    context.beginPath(); context.moveTo(0, y); context.lineTo(canvas.width, y); context.stroke();
  }
  context.strokeStyle = '#8d969d';
  context.beginPath(); context.moveTo(320, 0); context.lineTo(320, 480); context.stroke();
  if (sample.truth?.visible) {
    context.fillStyle = '#69dc32';
    context.beginPath(); context.arc(sample.truth.x, sample.truth.y, sample.truth.radius || 25, 0, 2 * Math.PI); context.fill();
  }
  if (sample.detection?.bbox) {
    context.strokeStyle = '#9ee07a'; context.lineWidth = 2; context.strokeRect(...sample.detection.bbox);
  }
  context.fillStyle = '#bac3ca'; context.font = '12px monospace';
  context.fillText(playback.label || 'REPLAY / NO BRIDGE OUTPUT', 14, 22);
  element('sandbox-time').textContent = `${sample.t.toFixed(2)} s`;
  element('sandbox-state').textContent = sample.state;
  element('sandbox-yaw').textContent = sample.yaw;
  renderPlaybackEvents(sample.t);
}

function renderPlaybackEvents(time) {
  const list = element('playback-events');
  list.replaceChildren();
  const events = playback.events || playback.samples
    .filter((sample, index) => index === 0 || sample.state !== playback.samples[index - 1].state)
    .map((sample) => ({ t: sample.t, type: 'state', data: { to: sample.state } }));
  for (const event of events.filter((item) => item.t <= time && !['command', 'ack'].includes(item.type)).slice(-6)) {
    const line = document.createElement('li');
    line.textContent = `${event.t.toFixed(2)} s · ${event.type} · ${event.data?.to || event.data?.reason || event.data?.action || ''}`;
    list.append(line);
  }
}

element('sandbox-scenario').onchange = loadPlayback;
element('sandbox-play').onclick = () => {
  if (!playback?.samples?.length) return;
  playing = !playing;
  if (playing) {
    if (playbackIndex === playback.samples.length - 1) playbackIndex = 0;
    playbackClock = performance.now() - playback.samples[playbackIndex].t * 1000;
  }
  element('sandbox-play').textContent = playing ? 'Pause' : 'Play';
};
element('sandbox-reset').onclick = () => {
  playbackIndex = 0; playing = false;
  element('sandbox-play').textContent = 'Play';
  drawPlayback();
};
setInterval(() => {
  if (!playing || !playback) return;
  const elapsed = (performance.now() - playbackClock) / 1000;
  while (playbackIndex < playback.samples.length - 1 && playback.samples[playbackIndex + 1].t <= elapsed) playbackIndex++;
  if (playbackIndex === playback.samples.length - 1) {
    playing = false;
    element('sandbox-play').textContent = 'Play';
  }
  drawPlayback();
}, 50);

element('replay-file').onchange = async (event) => {
  try {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > MAX_REPLAY_BYTES) throw new Error('Replay file is too large');
    const value = JSON.parse(await file.text());
    validateTrace(value);
    playback = value; playbackIndex = 0; playing = false;
    element('sandbox-play').textContent = 'Play';
    drawPlayback();
  } catch (error) {
    element('sandbox-state').textContent = error.message;
  }
};

async function initializeScenes() {
  try {
    const response = await fetch('/api/scenarios');
    if (!response.ok) throw new Error('Unable to load scenes');
    const scenes = await response.json();
    for (const id of ['operator-scenario', 'sandbox-scenario']) {
      for (const scene of scenes) {
        const option = document.createElement('option');
        option.value = scene; option.textContent = displayName(scene);
        element(id).append(option);
      }
      element(id).value = 'moving';
    }
    await loadPlayback();
  } catch (error) {
    element('sandbox-state').textContent = error.message;
  }
}
initializeScenes();

// Same rules as the native workstation: reject the whole file before replacing playback.
const MAX_REPLAY_BYTES = 20 * 1024 * 1024;
const STATES = ['MANUAL', 'SEARCHING', 'LOCKED', 'FAULT'];
const finite = (value) => typeof value === 'number' && Number.isFinite(value);
function validateDetection(detection) {
  if (detection === null || detection === undefined) return;
  if (typeof detection !== 'object' || Array.isArray(detection)) throw new Error('Invalid detection');
  for (const key of ['x', 'y', 'area', 'error', 'quality']) {
    if (key in detection && !finite(detection[key])) throw new Error('Invalid detection measurement');
  }
  if ('error' in detection && Math.abs(detection.error) > 1) throw new Error('Invalid detection error');
  if ('quality' in detection && (detection.quality < 0 || detection.quality > 1)) throw new Error('Invalid detection quality');
  if ('bbox' in detection) {
    const box = detection.bbox;
    if (!Array.isArray(box) || box.length !== 4 || !box.every(finite) || Math.min(box[2], box[3]) <= 0) throw new Error('Invalid detection bounds');
  }
}
function validateTrace(value) {
  if (!value || typeof value !== 'object' || !Array.isArray(value.samples) || !value.samples.length || value.samples.length > 100000) {
    throw new Error('Use an exported replay JSON with 1–100000 samples');
  }
  let previous = -1;
  for (const sample of value.samples) {
    if (!sample || typeof sample !== 'object' || !finite(sample.t) || sample.t < 0 || sample.t < previous) {
      throw new Error('Invalid or unordered replay timestamp');
    }
    previous = sample.t;
    if (!STATES.includes(sample.state) || !Number.isInteger(sample.yaw) || Math.abs(sample.yaw) > 1000) throw new Error('Invalid replay state or yaw');
    if (sample.state !== 'LOCKED' && sample.yaw !== 0) throw new Error('Replay yaw must be zero unless LOCKED');
    const truth = sample.truth ?? {};
    if (typeof truth !== 'object') throw new Error('Invalid replay geometry');
    if ('visible' in truth && typeof truth.visible !== 'boolean') throw new Error('Invalid target visibility');
    if (truth.visible && !(finite(truth.x) && finite(truth.y) && finite(truth.radius) && truth.radius > 0)) throw new Error('Invalid visible target');
    validateDetection(sample.detection);
  }
  if (value.events !== undefined && !Array.isArray(value.events)) throw new Error('Invalid replay events');
  for (const event of value.events ?? []) {
    if (!event || typeof event !== 'object' || !finite(event.t) || typeof event.type !== 'string') throw new Error('Invalid replay event');
  }
}
if (typeof module !== 'undefined') module.exports = { validateTrace, picturePosition };
