// HUD: flight telemetry, contact/physics readout, minimap, picture-in-picture frame, FPV OSD, toasts. No objectives.
import { P } from "./drone.js";

const $ = id => document.getElementById(id);
const deg = r => r * 180 / Math.PI;

export class Hud {
  constructor() {
    this.overlay = $("overlay"); this.g = this.overlay.getContext("2d");
    this.mm = $("minimap"); this.mg = this.mm.getContext("2d");
    this.resize();
  }

  resize() {
    const dpr = this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.overlay.width = innerWidth * dpr; this.overlay.height = innerHeight * dpr;
    this.mm.width = 260 * dpr; this.mm.height = 200 * dpr;
  }

  show(on) { $("hud").classList.toggle("hidden", !on); }
  toggleHelp() { const e = $("help"); e.classList.remove("hidden"); e.classList.toggle("faded"); }
  toggleTelemetry() { $("telemetry").classList.toggle("hidden"); }
  toggleMap() { this.mm.classList.toggle("hidden"); }
  loading(on, text = "") { $("loading").classList.toggle("hidden", !on); $("loading-text").textContent = text; }

  setLevel(lv) {
    $("l-title").textContent = lv.title; $("l-sub").textContent = lv.subtitle || "";
    this._foot = null;
    // title and key help show briefly, then get out of the way
    for (const id of ["level", "help"]) { $(id).classList.remove("faded"); clearTimeout(this["_t" + id]); this["_t" + id] = setTimeout(() => $(id).classList.add("faded"), id === "level" ? 4000 : 7000); }
  }

  telemetry(d, { agl, cam, post, fps, impacts, debug, time }) {
    const t = d.t, v = d.vel, hs = Math.hypot(v.x, v.z);
    this.power(d.armed);
    const f = Math.round(fps), fe = $("s-fps"); set("s-fps", f); fe.className = f >= 50 ? "good" : f >= 30 ? "ok" : "bad";
    set("s-spd", hs.toFixed(1)); set("s-alt", agl.toFixed(1)); set("s-bat", Math.round(d.battery * 100)); set("s-spin", Math.round(t.spinRpm || 0));
    set("s-volt", d.voltage.toFixed(1)); $("s-volt").style.color = d.lowV ? "var(--bad)" : "";
    const le = $("s-led"); set("s-led", d.leds ? "ON" : "OFF"); le.classList.toggle("on", d.leds);
    const sc = $("s-cage"); if (sc.textContent !== t.contact) { sc.textContent = t.contact; sc.className = "state " + t.contact.toLowerCase(); }
    $("warn").classList.toggle("hidden", !(d.lowV || d.landing)); $("warn").textContent = d.landing ? "LOW VOLTAGE — AUTO-LAND" : "LOW BATTERY — LAND";
    if ($("telemetry").classList.contains("hidden")) return;
    set("t-speed", hs.toFixed(1)); set("t-vs", (v.y >= 0 ? "+" : "") + v.y.toFixed(1)); set("t-agl", agl.toFixed(2));
    set("t-hdg", String(Math.round(((-deg(d.yaw) % 360) + 360) % 360)).padStart(3, "0") + "°");
    set("t-att", `${deg(d.roll).toFixed(0)}° / ${deg(d.pitch).toFixed(0)}°`);
    set("t-thrust", `${d.thrust.toFixed(1)} N · ${Math.round(d.thrustFrac() * 100)}%`);
    set("t-power", `${Math.round(t.power || 0)} W`);
    set("t-batt", `${Math.round(d.battery * 100)}% · ${(d.voltage / 2).toFixed(2)} V/cell`);
    set("t-va", `${d.voltage.toFixed(2)} V · ${d.current.toFixed(1)} A`); set("t-mah", `${Math.round(d.mAh)} / ${d.spec.capacityMah} mAh`);
    const s = d.spec; set("t-auw", s.auw_g.toFixed(1)); set("t-tw", (d.thrustMax() / (s.mass * 9.81)).toFixed(2) + " : 1");
    set("t-split", `${s.quad_g.toFixed(1)} · ${s.cage_g.toFixed(1)} · ${s.battery.g}`); set("t-pack", s.battery.name);
    $("t-batt-bar").style.width = Math.round(d.battery * 100) + "%";
    $("t-batt-bar").classList.toggle("low", d.battery < 0.2);
    set("t-spin", `${Math.round(t.spinRpm || 0)} rpm`);
    const c = $("t-contact"); c.textContent = t.contact; c.className = "state " + t.contact.toLowerCase();
    set("t-normal", t.contact === "FREE" ? "—" : `${(t.normalForce || 0).toFixed(1)} N`);
    const recent = time - (t.impactT ?? -99);
    set("t-impact", t.impact ? `${t.impact.toFixed(2)} m/s · ${t.peakG.toFixed(0)} g` : "—");
    $("t-impact").classList.toggle("flash", recent < 0.6);
    set("t-hits", impacts);
    set("m-cam", cam.toUpperCase() + (post ? " · PBR+AO" : " · FAST")); set("m-fps", Math.round(fps));
  }

  power(armed) {
    if (this._armed === armed) return;
    this._armed = armed;
    const b = $("s-pwr"); b.className = "pwr " + (armed ? "on" : "off"); $("s-pwr-state").textContent = armed ? "ON" : "OFF";
    set("t-motors", armed ? "ARMED" : "OFF");
  }

  pip(rect, label) {
    const f = $("pip-frame");
    if (!rect) { f.classList.add("hidden"); return; }
    f.classList.remove("hidden");
    Object.assign(f.style, { left: rect.x + "px", top: (innerHeight - rect.y - rect.h) + "px", width: rect.w + "px", height: rect.h + "px" });
    $("pip-label").textContent = label;
  }

  // Betaflight-style OSD drawn over the FPV view.
  osd(d, agl, shake) {
    const g = this.g, dpr = this.dpr, W = innerWidth, H = innerHeight;
    g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
    if (!d) return;
    const cx = W / 2 + (Math.random() - 0.5) * shake * 10, cy = H / 2 + (Math.random() - 0.5) * shake * 10;
    g.save(); g.translate(cx, cy); g.rotate(d.roll);
    g.strokeStyle = "rgba(255,255,255,0.85)"; g.lineWidth = 2; g.shadowColor = "rgba(0,0,0,0.8)"; g.shadowBlur = 3;
    const py = deg(d.pitch) * 6;
    g.beginPath(); g.moveTo(-140, py); g.lineTo(-40, py); g.moveTo(40, py); g.lineTo(140, py); g.stroke();
    g.restore();
    g.strokeStyle = "rgba(255,255,255,0.9)"; g.lineWidth = 2; g.shadowColor = "rgba(0,0,0,0.8)"; g.shadowBlur = 3;
    g.beginPath(); g.moveTo(cx - 18, cy); g.lineTo(cx - 6, cy); g.lineTo(cx, cy + 6); g.lineTo(cx + 6, cy); g.lineTo(cx + 18, cy); g.stroke();
    g.font = "600 17px Cascadia Mono, Consolas, monospace"; g.fillStyle = "#fff"; g.textAlign = "left";
    const hs = Math.hypot(d.vel.x, d.vel.z);
    g.fillText(`${(hs * 3.6).toFixed(0)} KM/H`, W * 0.18, cy + 6);
    g.textAlign = "right"; g.fillText(`${agl.toFixed(1)} M`, W * 0.82, cy + 6);
    g.textAlign = "center";
    // Betaflight-style OSD row: pack voltage, current, mAh drawn, flight time
    g.fillStyle = d.lowV ? "#ff5a4f" : "#fff";
    g.fillText(`${d.voltage.toFixed(1)}V   ${d.current.toFixed(1)}A   ${Math.round(d.mAh)}MAH   ${fmt(this.flightTime || 0)}`, W / 2, H - 120);
    g.fillStyle = "#fff"; g.fillText(d.t.contact + (d.leds ? "   LED" : ""), W / 2, H - 96);
    if (!d.armed) { g.font = "700 26px Cascadia Mono, Consolas, monospace"; g.fillStyle = "#ff5a4f"; g.fillText("DISARMED", W / 2, cy - 60); }
    g.fillText(`${String(Math.round(((-deg(d.yaw) % 360) + 360) % 360)).padStart(3, "0")}`, W / 2, 90);
  }

  minimap(lv, d) {
    if (this.mm.classList.contains("hidden")) return;
    const g = this.mg, dpr = this.dpr, W = 260, H = 200, b = lv.level.bounds;
    const sc = Math.min((W - 14) / (b.maxX - b.minX), (H - 14) / (b.maxZ - b.minZ));
    const ox = W / 2 - (b.minX + b.maxX) / 2 * sc, oz = H / 2 - (b.minZ + b.maxZ) / 2 * sc;
    const Pm = (x, z) => [ox + x * sc, oz + z * sc];
    g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
    if (!this._foot) {
      const c = document.createElement("canvas"); c.width = W * dpr; c.height = H * dpr; const h = c.getContext("2d"); h.setTransform(dpr, 0, 0, dpr, 0, 0);
      h.fillStyle = "rgba(170,200,220,0.5)";
      for (const f of lv.level.minimap) {
        h.save(); const [x, y] = Pm(f.x, f.z); h.translate(x, y); h.rotate(-(f.rot || 0));
        if (f.round) { h.beginPath(); h.arc(0, 0, f.w / 2 * sc, 0, 7); h.fill(); } else h.fillRect(-f.w / 2 * sc, -f.d / 2 * sc, Math.max(1, f.w * sc), Math.max(1, f.d * sc));
        h.restore();
      }
      this._foot = c;
    }
    g.drawImage(this._foot, 0, 0, W, H);
    const [dx, dz] = Pm(d.pos.x, d.pos.z), f = d.forward;
    g.fillStyle = "#33c3ff"; g.beginPath(); g.arc(dx, dz, 4, 0, 7); g.fill();
    g.strokeStyle = "#33c3ff"; g.lineWidth = 2; g.beginPath(); g.moveTo(dx, dz); g.lineTo(dx + f.x * 14, dz + f.z * 14); g.stroke();
  }

  link(t) {
    const el = $("link");
    if (!t) { el.classList.add("hidden"); return; }
    el.classList.remove("hidden");
    // Posted telemetry is untrusted text: build nodes, never HTML strings.
    const body = $("link-body");
    body.replaceChildren();
    const dot = document.createElement("span"); dot.className = "dot"; body.append(dot);
    body.append(`${String(t.source || "drone")} · ${Number(t.age).toFixed(1)} s ago`);
    for (const [k, v] of Object.entries(t.data || {}).slice(0, 6)) {
      const value = document.createElement("b");
      value.textContent = typeof v === "number" ? v.toFixed(2) : String(v);
      body.append(document.createElement("br"), `${k}: `, value);
    }
  }

  toast(text, life = 2.4) {
    const d = document.createElement("div"); d.className = "toast"; d.style.setProperty("--life", life + "s"); d.textContent = text;
    $("toasts").appendChild(d); setTimeout(() => d.remove(), (life + 0.7) * 1000);
  }
}

function fmt(s) { return Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0"); }
function set(id, v) { const e = $(id); if (e && e.textContent !== String(v)) e.textContent = v; }
export { P };
