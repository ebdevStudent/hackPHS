/* Browser-local inspection never posts playback to the shared backend. */
const navFinite = value => typeof value === 'number' && Number.isFinite(value);
const navVector = value => Array.isArray(value) && value.length === 3 && value.every(navFinite);
function navFiniteTree(value) {
  if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Nonfinite navigation data');
  if (Array.isArray(value)) value.forEach(navFiniteTree);
  else if (value && typeof value === 'object') Object.values(value).forEach(navFiniteTree);
}
function validateNavigation(value) {
  navFiniteTree(value);
  if (!value || typeof value !== 'object' || typeof value.status !== 'string' || typeof value.available !== 'boolean' ||
      typeof value.guidance_enabled !== 'boolean' || value.physical_output !== false || value.control_authority !== 'advisory_only' ||
      typeof value.authority_text !== 'string' || !Array.isArray(value.route) || !value.route.every(navVector) || value.route.length > 200002 ||
      (value.next_waypoint !== null && !navVector(value.next_waypoint)) ||
      (value.pose_age_s !== null && (!navFinite(value.pose_age_s) || value.pose_age_s < 0)) ||
      (value.clearance_m !== null && (!navFinite(value.clearance_m) || value.clearance_m < 0))) throw new Error('Invalid navigation snapshot');
  if (value.route_headings_rad !== undefined && (!Array.isArray(value.route_headings_rad) ||
      (value.route_headings_rad.length && value.route_headings_rad.length !== value.route.length) ||
      !value.route_headings_rad.every(v => navFinite(v) && Math.abs(v) <= Math.PI))) throw new Error('Invalid route headings');
  if (value.route_tag_ids !== undefined && (!Array.isArray(value.route_tag_ids) ||
      (value.route_tag_ids.length && value.route_tag_ids.length !== value.route.length) ||
      !value.route_tag_ids.every(ids => Array.isArray(ids) && ids.length >= 2 && new Set(ids).size === ids.length && ids.every(id => Number.isInteger(id) && id >= 0 && id < 587)))) throw new Error('Invalid route tag visibility');
  if (value.waypoint_heading_rad !== undefined && value.waypoint_heading_rad !== null && !navFinite(value.waypoint_heading_rad)) throw new Error('Invalid waypoint heading');
  if (!value.guidance_enabled && (value.route.length || value.next_waypoint !== null)) throw new Error('Inactive guidance has a route');
  if (value.mission !== undefined && value.mission !== null) {
    const mission = value.mission;
    if (mission.physical_output !== false || mission.physical_acceptance !== false || mission.uncertainty_provisional !== true ||
        !['unloaded', 'ready', 'running', 'waiting_for_localization', 'waiting_for_target', 'reacquiring_target', 'snapshot_pending', 'target_complete', 'complete', 'aborted', 'fault'].includes(mission.status) ||
        !['not_requested', 'not_required', 'requested', 'saved', 'failed'].includes(mission.snapshot_status) ||
        !Number.isInteger(mission.target_count) || mission.target_count < 0 || mission.target_count > 100 ||
        (mission.target_index !== null && (!Number.isInteger(mission.target_index) || mission.target_index < 0 || mission.target_index >= mission.target_count)) ||
        (mission.snapshot_sha256 !== null && !/^[a-f0-9]{64}$/.test(mission.snapshot_sha256)) ||
        ((mission.snapshot_sha256 === null) !== (mission.snapshot_source === null)) ||
        ((mission.status === 'unloaded') !== (mission.mission_id === null)) ||
        ((mission.target_index === null) !== ['complete', 'aborted', 'unloaded'].includes(mission.status)) ||
        (mission.target_index !== null && (!mission.target_id || !mission.target_name || !mission.arrival)) ||
        (mission.status === 'snapshot_pending' && mission.snapshot_status !== 'requested') ||
        (mission.status === 'target_complete' && !['saved', 'not_required'].includes(mission.snapshot_status)) ||
        (mission.status === 'aborted' && mission.snapshot_status !== 'not_requested')) throw new Error('Invalid inspection mission state');
  }
  if (value.pose !== null) {
    const pose = value.pose;
    const t = pose.map_from_aircraft;
    if (!pose || !['vision_estimate', 'synthetic_estimate', 'recorded_estimate'].includes(pose.source) ||
        !Array.isArray(t) || t.length !== 4 || !t.every(row => Array.isArray(row) && row.length === 4 && row.every(navFinite)) ||
        t[3].some((x, i) => Math.abs(x - (i === 3 ? 1 : 0)) > 1e-8) || !pose.timing || !navFinite(pose.timing.host_received_s) ||
        !navFinite(pose.uncertainty_m) || pose.uncertainty_m < 0 || !Array.isArray(pose.tag_ids) || !pose.tag_ids.length ||
        !pose.tag_ids.every(id => Number.isInteger(id) && id >= 0 && id < 587)) throw new Error('Invalid estimated pose');
    const r = t.slice(0, 3).map(row => row.slice(0, 3));
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
      const dot = r.reduce((sum, row) => sum + row[i] * row[j], 0);
      if (Math.abs(dot - (i === j ? 1 : 0)) > 1e-6) throw new Error('Invalid pose rotation');
    }
    const det = r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1]) - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0]) + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]);
    if (Math.abs(det - 1) > 1e-6) throw new Error('Invalid pose handedness');
  }
}
function validateNavigationMap(map) {
  navFiniteTree(map);
  const box = b => b && navVector(b.minimum) && navVector(b.maximum) && b.minimum.every((v, i) => v < b.maximum[i]);
  if (!map || map.units !== 'm' || map.axes !== 'right_handed_z_up' || !box(map.permitted) ||
      !Array.isArray(map.observed_free) || !map.observed_free.length || map.observed_free.length > 1000 || !map.observed_free.every(box) ||
      !Array.isArray(map.occupied) || map.occupied.length > 1000 || !map.occupied.every(box)) throw new Error('Invalid navigation map');
}
function validateNavigationReplay(value) {
  navFiniteTree(value);
  if (!value || value.schema_version !== 1 || value.physical_output !== false || value.physical_telemetry !== null || typeof value.label !== 'string' ||
      !Array.isArray(value.samples) || !value.samples.length || value.samples.length > 100000) throw new Error('Use a navigation replay/demo export');
  validateNavigationMap(value.map);
  let previous = -1;
  for (const sample of value.samples) {
    if (!navFinite(sample.t) || sample.t < previous || sample.t < 0) throw new Error('Unordered navigation replay');
    previous = sample.t;
    validateNavigation(sample);
    if ('simulation_truth_position_m' in sample && !navVector(sample.simulation_truth_position_m)) throw new Error('Invalid simulation truth');
    if ('mock_velocity_m_s' in sample && !navVector(sample.mock_velocity_m_s)) throw new Error('Invalid mock output');
  }
}

let navPlayback = null, navIndex = 0, navPlaying = false, navClock = 0, navMap = null, navMapID = null;
function navCoordinates(value) { return value ? value.map(n => n.toFixed(3)).join(', ') : '—'; }
function drawNavigation(state, map) {
  const canvas = element('nav-map'), ctx = canvas.getContext('2d');
  ctx.fillStyle = '#162028'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (!map) { ctx.fillStyle = '#b6c4ce'; ctx.fillText('Map unavailable · unknown space is not free', 18, 28); return; }
  const minimum = map.permitted.minimum, maximum = map.permitted.maximum;
  const scale = Math.min((canvas.width - 40) / (maximum[0] - minimum[0]), (canvas.height - 40) / (maximum[1] - minimum[1]));
  const xy = point => [20 + (point[0] - minimum[0]) * scale, canvas.height - 20 - (point[1] - minimum[1]) * scale];
  const boxes = (list, color) => {
    ctx.fillStyle = color;
    for (const box of list) {
      const low = xy(box.minimum), high = xy(box.maximum);
      ctx.fillRect(low[0], high[1], high[0] - low[0], low[1] - high[1]);
    }
  };
  boxes(map.observed_free, '#344a58'); boxes(map.occupied, '#936550');
  if (state.route.length) {
    ctx.strokeStyle = '#b8dceb'; ctx.lineWidth = 2; ctx.beginPath();
    state.route.forEach((point, i) => { const p = xy(point); i ? ctx.lineTo(...p) : ctx.moveTo(...p); }); ctx.stroke();
    if (state.route_headings_rad?.length === state.route.length) {
      ctx.strokeStyle = '#f1c878'; ctx.lineWidth = 1;
      state.route.forEach((point, i) => {
        const p = xy(point), yaw = state.route_headings_rad[i], dx = Math.cos(yaw) * 8, dy = -Math.sin(yaw) * 8;
        ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(p[0] + dx, p[1] + dy); ctx.stroke();
      });
    }
  }
  if (state.pose) {
    const p = xy(state.pose.map_from_aircraft.slice(0, 3).map(row => row[3]));
    ctx.fillStyle = '#b8dceb'; ctx.beginPath(); ctx.arc(...p, 4, 0, 2 * Math.PI); ctx.fill();
  }
  ctx.fillStyle = '#b6c4ce'; ctx.font = '12px monospace';
  ctx.fillText('XY projection · route clearance checked in 3D · dark = unknown', 12, 16);
}
function paintNavigation(state, map, label) {
  element('nav-label').textContent = label;
  element('nav-status').textContent = state?.status || 'Navigation not configured';
  element('nav-authority').textContent = state?.authority_text || 'Pilot controls movement, height, arming and takeover. Navigation is advisory.';
  element('nav-position').textContent = navCoordinates(state?.pose?.map_from_aircraft.slice(0, 3).map(row => row[3]));
  element('nav-waypoint').textContent = navCoordinates(state?.next_waypoint);
  element('nav-age').textContent = state?.pose_age_s == null ? '—' : `${Math.round(state.pose_age_s * 1000)} ms / ${state.clearance_m == null ? '—' : state.clearance_m.toFixed(3) + ' m'}`;
  const mission = state?.mission;
  element('nav-mission-status').textContent = mission ?
    `${mission.mission_id || 'Mission'} · ${mission.status}${mission.target_id ? ` · ${mission.target_index + 1}/${mission.target_count} ${mission.target_name}` : ''} · snapshot ${mission.snapshot_status}` :
    'No inspection mission loaded.';
  drawNavigation(state || {route: [], pose: null}, map);
}
function renderNavigation(value) {
  if (navPlayback) return;
  try {
    if (value) validateNavigation(value);
    paintNavigation(value, navMap, value?.example ? 'EXAMPLE / SYNTHETIC' : value?.pose?.source === 'recorded_estimate' ? 'RECORDED ESTIMATE' : 'VISION ESTIMATE');
    const id = value ? `${value.map_id}:${value.map_version}` : null;
    if (id !== navMapID) {
      navMapID = id;
      fetch('/api/navigation/map').then(r => r.json()).then(map => {
        if (map) validateNavigationMap(map);
        navMap = map;
        if (!navPlayback) paintNavigation(currentState?.navigation, navMap, value?.example ? 'EXAMPLE / SYNTHETIC' : 'VISION ESTIMATE');
      }).catch(() => { navMap = null; });
    }
  } catch (error) { paintNavigation(null, null, 'INVALID'); element('nav-status').textContent = error.message; }
}
function navigationDisconnected() {
  if (!navPlayback) { paintNavigation(null, null, 'OFFLINE'); element('nav-status').textContent = 'Connection lost · guidance suppressed'; }
}

if (typeof document !== 'undefined') {
  bindAction('nav-goal-apply', 'navigation', () => ({action: 'goal', goal: element('nav-goal').value.trim().split(/\s+/).map(Number)}), 'Goal set. Restore guidance after acquisition.');
  bindAction('nav-resume', 'navigation', () => ({action: 'resume'}), 'Guidance restoration requested. Pilot keeps control.');
  bindAction('nav-disable', 'navigation', () => ({action: 'disable'}), 'Guidance stopped.');
  bindAction('nav-mission-start', 'navigation', () => ({action: 'mission_start'}), 'Mission dry run started. Guidance remains disabled until restored.');
  bindAction('nav-mission-advance', 'navigation', () => ({action: 'mission_advance'}), 'Mission advanced. Restore guidance for the next target.');
  bindAction('nav-mission-abort', 'navigation', () => ({action: 'mission_abort'}), 'Mission aborted. Guidance stopped.');
  element('nav-bundle-file').onchange = async event => {
    try {
      const file = event.target.files[0]; if (!file) return;
      if (file.size > 10000000) throw new Error('Bundle too large');
      await operatorAction('navigation/bundle', {bundle: JSON.parse(await file.text())});
      navMapID = null;
      element('operator-message').textContent = 'Navigation bundle loaded. Guidance disabled.';
    } catch (error) { element('operator-message').textContent = error.message; }
  };
  element('nav-mission-file').onchange = async event => {
    try {
      const file = event.target.files[0]; if (!file) return;
      if (file.size > 1000000) throw new Error('Mission file too large');
      await operatorAction('navigation/mission', {mission: JSON.parse(await file.text())});
      element('operator-message').textContent = 'Inspection mission loaded. Start its dry run when ready.';
    } catch (error) { element('operator-message').textContent = error.message; }
  };
  element('nav-replay-file').onchange = async event => {
    try {
      const file = event.target.files[0]; if (!file) return;
      if (file.size > 20 * 1024 * 1024) throw new Error('Replay too large');
      const candidate = JSON.parse(await file.text()); validateNavigationReplay(candidate);
      navPlayback = candidate; navIndex = 0; navPlaying = false;
      paintNavigation(candidate.samples[0], candidate.map, 'LOCAL REPLAY / ' + candidate.label);
    } catch (error) { element('nav-status').textContent = error.message; }
  };
  element('nav-replay-play').onclick = () => {
    if (!navPlayback) return;
    navPlaying = !navPlaying;
    if (navIndex === navPlayback.samples.length - 1) navIndex = 0;
    navClock = performance.now() - (navPlayback.samples[navIndex].t - navPlayback.samples[0].t) * 1000;
    element('nav-replay-play').textContent = navPlaying ? 'Pause replay' : 'Play replay';
  };
  element('nav-live').onclick = () => { navPlayback = null; navPlaying = false; element('nav-replay-play').textContent = 'Play replay'; renderNavigation(currentState?.navigation); };
  setInterval(() => {
    if (!navPlaying || !navPlayback) return;
    const t = (performance.now() - navClock) / 1000 + navPlayback.samples[0].t;
    while (navIndex < navPlayback.samples.length - 1 && navPlayback.samples[navIndex + 1].t <= t) navIndex++;
    paintNavigation(navPlayback.samples[navIndex], navPlayback.map, 'LOCAL REPLAY / ' + navPlayback.label);
    if (navIndex === navPlayback.samples.length - 1) { navPlaying = false; element('nav-replay-play').textContent = 'Play replay'; }
  }, 50);
}
if (typeof module !== 'undefined') module.exports = {validateNavigation, validateNavigationMap, validateNavigationReplay};
