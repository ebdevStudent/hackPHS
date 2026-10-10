// Synthesized sound for the ball-drone simulator (WebAudio only, no audio files).
//   motors(thrust, airspeed)  4 detuned motors: blade-pass tones + harmonics + electrical whine + broadband prop noise
//   impact(speed, material)   metal clang (inharmonic partials) / concrete thud + grit / wood knock / brick
//   scrape(slip, material, rollSpeed)  sliding grit + rolling rumble with joint ticks
//   ambience(kind)            "industrial" | "rescue" | null
// Everything runs through a master bus with a compressor/limiter so nothing clips. init() must follow a user gesture.

const MAT = {
  metal: { band: 3200, q: 1.2, tick: 2600 },
  concrete: { band: 1400, q: 0.8, tick: 1500 },
  brick: { band: 1200, q: 0.8, tick: 1300 },
  wood: { band: 900, q: 1.0, tick: 1000 },
};

export class Sfx {
  constructor() { this.ctx = null; this.muted = false; this._amb = null; this._ambKind = null; }

  init() {
    if (this.ctx) { if (this.ctx.state === "suspended") this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    const c = this.ctx = new AC();
    this.comp = c.createDynamicsCompressor();
    this.comp.threshold.value = -16; this.comp.knee.value = 8; this.comp.ratio.value = 6; this.comp.attack.value = 0.004; this.comp.release.value = 0.2;
    this.master = c.createGain(); this.master.gain.value = this.muted ? 0 : 0.7;
    this.master.connect(this.comp); this.comp.connect(c.destination);
    this.motorBus = this._bus(0.9); this.sfxBus = this._bus(1.0); this.ambBus = this._bus(0.55); this.scrapeBus = this._bus(0.8);

    // white + pink-ish noise buffers (shared by every noisy voice)
    const len = c.sampleRate * 3;
    this.white = c.createBuffer(1, len, c.sampleRate);
    const w = this.white.getChannelData(0);
    for (let i = 0; i < len; i++) w[i] = Math.random() * 2 - 1;
    this.pink = c.createBuffer(1, len, c.sampleRate);
    const p = this.pink.getChannelData(0);
    let b0 = 0, b1 = 0, b2 = 0;
    for (let i = 0; i < len; i++) { const x = Math.random() * 2 - 1; b0 = 0.997 * b0 + 0.03 * x; b1 = 0.985 * b1 + 0.06 * x; b2 = 0.95 * b2 + 0.12 * x; p[i] = (b0 + b1 + b2 + x * 0.08) * 0.6; }

    this._buildMotors();
    this._buildScrape();
  }

  _bus(gain) { const g = this.ctx.createGain(); g.gain.value = gain; g.connect(this.master); return g; }
  _noise(buf = this.white, loop = true) { const s = this.ctx.createBufferSource(); s.buffer = buf; s.loop = loop; s.loopStart = Math.random(); return s; }

  setMute(m) { this.muted = m; if (this.master) this.master.gain.setTargetAtTime(m ? 0 : 0.7, this.ctx.currentTime, 0.05); }

  // ---------------------------------------------------------------- motors
  _buildMotors() {
    const c = this.ctx;
    this.motorsV = [];
    const detune = [1.0, 1.013, 0.991, 1.021];
    for (let k = 0; k < 4; k++) {
      const out = c.createGain(); out.gain.value = 0; out.connect(this.motorBus);
      const bpf = c.createBiquadFilter(); bpf.type = "lowpass"; bpf.frequency.value = 5000; bpf.Q.value = 0.5; bpf.connect(out);
      const mk = (type, g) => { const o = c.createOscillator(); o.type = type; const gg = c.createGain(); gg.gain.value = g; o.connect(gg); gg.connect(bpf); o.start(); return o; };
      const v = { out, det: detune[k], bp: mk("triangle", 0.55), h2: mk("sine", 0.22), h3: mk("sawtooth", 0.05), whine: mk("square", 0.012), drift: Math.random() * 6 };
      this.motorsV.push(v);
    }
    // broadband prop noise (one shared source, filter opens with rpm) + low airflow wash
    this.propNoise = this._noise(this.pink); this.propBP = c.createBiquadFilter(); this.propBP.type = "bandpass"; this.propBP.frequency.value = 900; this.propBP.Q.value = 0.6;
    this.propNoiseG = c.createGain(); this.propNoiseG.gain.value = 0;
    this.propNoise.connect(this.propBP); this.propBP.connect(this.propNoiseG); this.propNoiseG.connect(this.motorBus); this.propNoise.start();
    this.wash = this._noise(this.pink); this.washLP = c.createBiquadFilter(); this.washLP.type = "lowpass"; this.washLP.frequency.value = 260;
    this.washG = c.createGain(); this.washG.gain.value = 0;
    this.wash.connect(this.washLP); this.washLP.connect(this.washG); this.washG.connect(this.motorBus); this.wash.start();
  }

  // thrust: fraction 0..1 (all motors) or array of 4 fractions. rpm ∝ √thrust. airspeed in m/s.
  motors(thrust, airspeed = 0) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    const fr = Array.isArray(thrust) ? thrust : [thrust, thrust, thrust, thrust];
    let mean = 0;
    this.motorsV.forEach((v, k) => {
      const f = Math.max(0, Math.min(1, fr[k] ?? 0));
      v.drift += 0.016;
      const rpm = f > 0.005 ? 5000 + 25000 * Math.sqrt(f) * (1 + 0.004 * Math.sin(v.drift * 1.7 + k)) : 0;
      mean += rpm / 4;
      const bpf = rpm / 60 * 3 * v.det;                                 // 3-blade blade-pass frequency
      const on = rpm > 0;
      v.bp.frequency.setTargetAtTime(Math.max(20, bpf), t, 0.06);
      v.h2.frequency.setTargetAtTime(Math.max(20, bpf * 2), t, 0.06);
      v.h3.frequency.setTargetAtTime(Math.max(20, bpf * 3.01), t, 0.06);
      v.whine.frequency.setTargetAtTime(Math.max(20, rpm / 60 * 7), t, 0.06);   // 14-pole motor: 7 electrical cycles per rev
      v.out.gain.setTargetAtTime(on ? 0.018 + 0.05 * f : 0, t, on ? 0.05 : 0.25);
    });
    const mf = mean / 30000;
    this.propBP.frequency.setTargetAtTime(500 + 3500 * mf, t, 0.08);
    this.propNoiseG.gain.setTargetAtTime(mf > 0.01 ? 0.05 + 0.22 * mf * mf : 0, t, 0.08);
    this.washLP.frequency.setTargetAtTime(180 + airspeed * 90, t, 0.2);
    this.washG.gain.setTargetAtTime(Math.min(0.35, airspeed * 0.06), t, 0.2);
  }

  engine(throttle, on) { this.motors(on ? throttle : 0, 0); }

  // ---------------------------------------------------------------- impacts
  _env(g, t, peak, decay, attack = 0.002) {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak), t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
  }

  _burst(t, dur, type, freq, q, peak, decay, dest = this.sfxBus) {
    const c = this.ctx, s = this._noise(this.white, false);
    const f = c.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q;
    const g = c.createGain(); this._env(g, t, peak, decay);
    s.connect(f); f.connect(g); g.connect(dest); s.start(t, Math.random() * 2); s.stop(t + dur);
  }

  _tone(t, freq, peak, decay, type = "sine", glideTo = null, dest = this.sfxBus) {
    const c = this.ctx, o = c.createOscillator(), g = c.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    if (glideTo) o.frequency.exponentialRampToValueAtTime(glideTo, t + decay);
    this._env(g, t, peak, decay);
    o.connect(g); g.connect(dest); o.start(t); o.stop(t + decay + 0.05);
  }

  impact(speed, material = "concrete") {
    if (!this.ctx) return;
    const t = this.ctx.currentTime, v = Math.max(0, Math.min(1, speed / 4));
    if (v < 0.02) return;
    const amp = 0.08 + 0.55 * v;
    // the cage itself: a short plasticky rattle of 60 joints + carbon rods flexing
    this._burst(t, 0.12, "bandpass", 2400 + Math.random() * 600, 2.5, amp * 0.25, 0.07);
    if (material === "metal") {
      const f0 = 330 + Math.random() * 260;
      for (const [ratio, a, d] of [[1, 1, 0.9], [2.76, 0.6, 0.6], [5.4, 0.35, 0.35], [8.93, 0.2, 0.22], [13.3, 0.12, 0.12]])
        this._tone(t, f0 * ratio * (1 + (Math.random() - 0.5) * 0.01), amp * 0.32 * a, d * (0.5 + v * 0.7));
      this._burst(t, 0.05, "highpass", 4000, 0.7, amp * 0.35, 0.03);
      this._tone(t, 90, amp * 0.4, 0.12, "sine", 50);
    } else if (material === "wood") {
      this._burst(t, 0.15, "bandpass", 650 + Math.random() * 200, 4, amp * 0.6, 0.11);
      this._tone(t, 170 + Math.random() * 40, amp * 0.5, 0.16, "sine", 120);
      this._tone(t, 420, amp * 0.18, 0.08, "triangle");
    } else {                                               // concrete / brick / other: dull thud + grit
      const bright = material === "brick" ? 1.15 : 1;
      this._tone(t, 75, amp * 0.85, 0.16, "sine", 42);
      this._burst(t, 0.18, "lowpass", 700 * bright, 0.7, amp * 0.6, 0.12);
      this._burst(t + 0.005, 0.25, "highpass", 2500 * bright, 0.5, amp * 0.12 * (0.4 + v), 0.18);   // grit trickle
    }
  }

  hit(strength) { this.impact(strength, "concrete"); }

  // ---------------------------------------------------------------- scrape / rolling
  _buildScrape() {
    const c = this.ctx;
    this.scr = this._noise(this.white); this.scrBP = c.createBiquadFilter(); this.scrBP.type = "bandpass"; this.scrBP.frequency.value = 1400; this.scrBP.Q.value = 0.8;
    this.scrG = c.createGain(); this.scrG.gain.value = 0;
    this.scr.connect(this.scrBP); this.scrBP.connect(this.scrG); this.scrG.connect(this.scrapeBus); this.scr.start();
    this.rum = this._noise(this.pink); this.rumLP = c.createBiquadFilter(); this.rumLP.type = "lowpass"; this.rumLP.frequency.value = 160;
    this.rumG = c.createGain(); this.rumG.gain.value = 0;
    this.rum.connect(this.rumLP); this.rumLP.connect(this.rumG); this.rumG.connect(this.scrapeBus); this.rum.start();
    this._tickPhase = 0; this._tickT = 0;
  }

  // slipSpeed: sliding speed at the contact (m/s). rollSpeed: rolling surface speed (m/s, = ω·R). Call every frame.
  scrape(slipSpeed, material = "concrete", rollSpeed = 0) {
    if (!this.ctx) return;
    const c = this.ctx, t = c.currentTime, m = MAT[material] || MAT.concrete;
    const s = Math.max(0, Math.min(1, slipSpeed / 2)), r = Math.max(0, Math.min(1, rollSpeed / 3));
    this.scrBP.frequency.setTargetAtTime(m.band * (0.8 + s * 0.5), t, 0.05);
    this.scrBP.Q.value = m.q;
    this.scrG.gain.setTargetAtTime(slipSpeed > 0.03 ? 0.04 + 0.3 * s : 0, t, 0.04);
    this.rumLP.frequency.setTargetAtTime(110 + 220 * r, t, 0.1);
    this.rumG.gain.setTargetAtTime(rollSpeed > 0.05 ? 0.06 + 0.35 * r : 0, t, 0.08);
    // joints ticking on the surface: one tick per ~75 mm of rolled distance (the cage edge length)
    const dt = this._tickT ? Math.min(0.1, t - this._tickT) : 0; this._tickT = t;
    if (rollSpeed > 0.05) {
      this._tickPhase += rollSpeed * dt / 0.075;
      while (this._tickPhase >= 1) {
        this._tickPhase -= 1;
        this._burst(t + Math.random() * 0.01, 0.03, "bandpass", m.tick * (0.85 + Math.random() * 0.3), 3, 0.03 + 0.1 * r, 0.018, this.scrapeBus);
      }
    } else this._tickPhase = 0;
  }

  // ---------------------------------------------------------------- ambience
  ambience(kind) {
    if (!this.ctx || kind === this._ambKind) return;
    this._ambKind = kind;
    if (this._amb) {                                       // fade out and stop the previous bed
      const old = this._amb; const t = this.ctx.currentTime;
      old.gain.gain.setTargetAtTime(0, t, 0.4); old.timers.forEach(clearTimeout);
      setTimeout(() => { old.nodes.forEach(n => { try { n.stop(); } catch { /* not a source */ } }); old.gain.disconnect(); }, 2500);
      this._amb = null;
    }
    if (!kind) return;
    const c = this.ctx, g = c.createGain(); g.gain.value = 0; g.connect(this.ambBus);
    g.gain.setTargetAtTime(1, c.currentTime, 0.8);
    const amb = { gain: g, nodes: [], timers: [] };
    this._amb = amb;
    const src = (node) => { amb.nodes.push(node); node.start(); return node; };
    const lfo = (freq, depth, target, offset) => {
      const o = c.createOscillator(); o.frequency.value = freq; const d = c.createGain(); d.gain.value = depth;
      o.connect(d); d.connect(target); if (offset !== undefined) target.value = offset; src(o);
    };
    const every = (minS, maxS, fn) => {
      const loop = () => { if (this._amb !== amb) return; fn(); amb.timers.push(setTimeout(loop, (minS + Math.random() * (maxS - minS)) * 1000)); };
      amb.timers.push(setTimeout(loop, (minS + Math.random() * (maxS - minS)) * 500));
    };

    if (kind === "industrial") {
      // electrical hum of the hall (50 Hz mains + harmonics), heavily low-passed
      const humLP = c.createBiquadFilter(); humLP.type = "lowpass"; humLP.frequency.value = 400; humLP.connect(g);
      for (const [f, a] of [[50, 0.05], [100, 0.035], [150, 0.015], [300, 0.006]]) {
        const o = c.createOscillator(); o.frequency.value = f; const gg = c.createGain(); gg.gain.value = a; o.connect(gg); gg.connect(humLP); src(o);
      }
      // distant machinery: low rumbling noise with slow swells
      const mach = this._noise(this.pink), mLP = c.createBiquadFilter(); mLP.type = "lowpass"; mLP.frequency.value = 220;
      const mG = c.createGain(); mG.gain.value = 0.25; mach.connect(mLP); mLP.connect(mG); mG.connect(g); src(mach);
      lfo(0.07, 0.12, mG.gain);
      // ventilation air
      const vent = this._noise(this.pink), vBP = c.createBiquadFilter(); vBP.type = "bandpass"; vBP.frequency.value = 600; vBP.Q.value = 0.4;
      const vG = c.createGain(); vG.gain.value = 0.05; vent.connect(vBP); vBP.connect(vG); vG.connect(g); src(vent);
      // occasional distant clank and steam hiss
      every(4, 11, () => {
        const t = c.currentTime, f0 = 180 + Math.random() * 200;
        for (const [r, a] of [[1, 0.05], [2.7, 0.03], [5.2, 0.015]]) this._tone(t, f0 * r, a, 0.9, "sine", null, g);
      });
      every(7, 16, () => {
        const t = c.currentTime, d = 1.2 + Math.random() * 2.5;
        const s = this._noise(this.white, false), f = c.createBiquadFilter(); f.type = "highpass"; f.frequency.value = 3000;
        const gg = c.createGain(); gg.gain.setValueAtTime(0.0001, t); gg.gain.linearRampToValueAtTime(0.06, t + 0.15); gg.gain.linearRampToValueAtTime(0.0001, t + d);
        s.connect(f); f.connect(gg); gg.connect(g); s.start(t); s.stop(t + d + 0.1);
      });
    } else if (kind === "rescue") {
      // night wind: band-passed noise whose centre and level wander
      const wind = this._noise(this.pink), wBP = c.createBiquadFilter(); wBP.type = "bandpass"; wBP.Q.value = 0.9;
      const wG = c.createGain(); wG.gain.value = 0.22; wind.connect(wBP); wBP.connect(wG); wG.connect(g); src(wind);
      lfo(0.05, 260, wBP.frequency, 520); lfo(0.11, 0.12, wG.gain);
      // distant siren wail (heavily low-passed / quiet = far away)
      every(18, 40, () => {
        const t = c.currentTime, dur = 7 + Math.random() * 5;
        const o = c.createOscillator(); o.type = "sawtooth";
        const lp = c.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 1100;
        const gg = c.createGain(); gg.gain.setValueAtTime(0.0001, t); gg.gain.linearRampToValueAtTime(0.018, t + 1.5); gg.gain.linearRampToValueAtTime(0.0001, t + dur);
        for (let k = 0; k * 2.4 < dur; k++) { o.frequency.setValueAtTime(620, t + k * 2.4); o.frequency.linearRampToValueAtTime(1250, t + k * 2.4 + 1.2); o.frequency.linearRampToValueAtTime(620, t + k * 2.4 + 2.4); }
        o.connect(lp); lp.connect(gg); gg.connect(g); o.start(t); o.stop(t + dur + 0.1);
      });
      // water drips
      every(0.6, 3.5, () => { const t = c.currentTime, f = 1200 + Math.random() * 1600; this._tone(t, f, 0.03, 0.09, "sine", f * 1.6, g); });
      // structure creaks: slow, low, band-passed sawtooth gliss
      every(6, 15, () => {
        const t = c.currentTime, d = 0.6 + Math.random() * 1.2;
        const o = c.createOscillator(); o.type = "sawtooth"; o.frequency.setValueAtTime(70 + Math.random() * 60, t); o.frequency.linearRampToValueAtTime(110 + Math.random() * 90, t + d);
        const bp = c.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 450; bp.Q.value = 6;
        const gg = c.createGain(); gg.gain.setValueAtTime(0.0001, t); gg.gain.linearRampToValueAtTime(0.035, t + d * 0.3); gg.gain.linearRampToValueAtTime(0.0001, t + d);
        o.connect(bp); bp.connect(gg); gg.connect(g); o.start(t); o.stop(t + d + 0.05);
      });
      // settling debris trickle
      every(9, 22, () => this._burst(c.currentTime, 1.2, "bandpass", 2200, 0.6, 0.03, 0.9, g));
    }
  }

  // ---------------------------------------------------------------- simple UI tones (legacy)
  tone(freqs, dur = 0.12, type = "sine", vol = 0.25, gap = 0.09) {
    if (!this.ctx) return;
    const t0 = this.ctx.currentTime;
    freqs.forEach((f, i) => this._tone(t0 + i * gap, f, vol, dur, type));
  }
  blip() { this.tone([1400], 0.05, "square", 0.05); }
  warn() { this.tone([880, 880], 0.08, "square", 0.08, 0.15); }
}
