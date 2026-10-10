// Backend calls (all fail soft: the simulator runs fine without the Python backend).
async function call(path) {
  try { const r = await fetch(path); if (!r.ok) throw new Error(r.status); return await r.json(); } catch { return null; }
}
export const api = {
  health: () => call("/api/health"),
  telemetry: () => call("/api/telemetry"),   // data posted by the physical drone / ground station
};
