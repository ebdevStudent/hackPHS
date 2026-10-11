// Drone specification — every number traces to the HackPHS 2026 document (BOM p.3, hardware p.10, CAD p.6,
// review p.20–26) or to the part vendors' published data. Masses in grams.
//
// The one value that is not published for this exact combination is the static thrust of a 1103 11000KV motor on a
// Gemfan 2015 two-blade prop at 2S. Happymodel's official EX1103 table (7.4 V, 2023R tri-blade) is used for the
// efficiency curve and the 2015 two-blade is taken as ~70 g max per motor at 7.6 V. Replace MOTOR.thrustMax_g with
// your bench measurement (the document asks the team to measure it).

export const PARTS = [
  // ---- airborne system (BOM p.3 / hardware p.10)
  { group: "Quad", name: "BetaFPV Meteor85 frame (PP, 87.7 mm wheelbase)", qty: 1, g: 11.32, src: "BetaFPV / GetFPV listing" },
  { group: "Quad", name: "HGLRC Specter F411 1-2S AIO (FC + 10A ESC + ELRS + 400 mW VTX)", qty: 1, g: 4.9, src: "HGLRC listing" },
  { group: "Quad", name: "Happymodel EX1103 11000KV motor", qty: 4, g: 3.8, src: "Pyrodrone / Happymodel" },
  { group: "Quad", name: "Gemfan 2015 2-blade prop, 1.5 mm shaft", qty: 4, g: 0.5, src: "Gemfan / GetFPV" },
  { group: "Quad", name: "Caddx Ant 14×14 mm analog camera", qty: 1, g: 2.0, src: "Caddx / HobbyKing" },
  { group: "Quad", name: "XT30 pigtail, 30 AWG wiring, strap, antenna, screws", qty: 1, g: 3.5, src: "estimate" },
  // ---- two-ring gimbal (P1B, no outer cage): ring sizes and masses from docs/22-motion-physics.md §2.3
  { group: "Gimbal", name: "Gimbal ring, outer (R 96.5 mm, PETG)", qty: 1, g: 16.5, src: "docs/22 §2.3 estimate" },
  { group: "Gimbal", name: "Gimbal ring, inner (R 86.5 mm, PETG)", qty: 1, g: 14.8, src: "docs/22 §2.3 estimate" },
  { group: "Gimbal", name: "6 × MR52ZZ bearings + Ø2 mm steel pivot pins", qty: 1, g: 1.6, src: "6 × 0.2 g + pins" },
  { group: "Gimbal", name: "Centre mount TPU/PETG + silicone dampers", qty: 1, g: 3.5, src: "estimate" },
];

// 2S LiHV battery test set (BOM p.3/p.5, review p.24–26: 450 baseline, ~550, ~650–680, 750–850 high-energy)
export const BATTERIES = {
  450: { name: "Tattu 450 mAh 2S LiHV 95C", g: 29, Rint: 0.040, src: "GetFPV listing (29 g)" },
  550: { name: "2S LiHV 550 mAh (mid)", g: 32, Rint: 0.045, src: "typical 2S 550 HV pack" },
  650: { name: "2S LiHV 650 mAh", g: 35, Rint: 0.048, src: "typical 2S 650 HV pack" },
  850: { name: "RDQ 850 mAh 2S LiHV 60C", g: 37, Rint: 0.055, src: "RDQ / WREKD listing (37 g)" },
};

export const MOTOR = {
  kv: 11000, propDia_m: 0.0508, thrustMax_g: 70, refVolt: 7.6,   // per motor, static, fresh 2S under load ≈ 7.6 V
  // Happymodel EX1103 11000KV, 7.4 V benchmark: thrust (g) → electrical power (W) per motor
  curve: [[0, 0.4], [23, 7.92], [40.9, 15.69], [56.6, 23.46], [68.6, 29.97], [81.8, 37.30], [95, 45.81]],
};

// Two-ring gimbal, no cage (P1B chain, docs/22 §3). In three.js axes (Y up, nose −Z): the outer ring turns about the
// vertical Y axis, the inner ring about X inside it, and the aircraft about Z (its fore-aft axis) inside the inner ring.
// Radii are the outer edge of each ring band; both bands stay clear of the 2-inch prop disks (tips at ≤ 70 mm).
export const GIMBAL = {
  outer: { r: 0.0965, band: 0.006, width: 0.010 },     // radial band thickness and axial width (drawn bold so it reads)
  inner: { r: 0.0865, band: 0.006, width: 0.010 },
  pin: 0.001, bearing: { od: 0.005, w: 0.0025 },      // Ø2 mm steel pins in MR52ZZ (2 × 5 × 2.5 mm) bearings
  envelope: 0.102,                                     // contact sphere: outer ring + its yaw bearings and hubs
  mu: 0.30, e: 0.35, rollRes: 0.03,                    // PETG ring on a hard floor; restitution; rolling resistance
};

export const INSTALL_LOSS = 1.12;       // gimbal rings / mount arms in the prop wash raise hover power (review p.25)
export const AVIONICS_W = 1.6;          // F411 AIO + ELRS + Caddx Ant + VTX at 25 mW indoors
export const INSPECTION_LED_W = 0.6;    // two small switchable white LEDs (review p.22)

// LiHV cell open-circuit voltage vs state of charge
const OCV = [[0, 3.30], [0.05, 3.50], [0.1, 3.62], [0.2, 3.70], [0.3, 3.75], [0.4, 3.80], [0.5, 3.86], [0.6, 3.93], [0.7, 4.02], [0.8, 4.12], [0.9, 4.24], [1, 4.35]];
export function cellOCV(soc) { return interp(OCV, Math.max(0, Math.min(1, soc))); }

// electrical power (W) one motor draws for a given static thrust (g)
export function motorPower(thrust_g) { return interp(MOTOR.curve, Math.max(0, thrust_g)); }

export function buildSpec(capacityMah = 550) {
  const bat = BATTERIES[capacityMah] || BATTERIES[550];
  const sum = grp => PARTS.filter(p => !grp || p.group === grp).reduce((s, p) => s + p.qty * p.g, 0);
  const quad = sum("Quad"), gimbal = sum("Gimbal"), auw = quad + gimbal + bat.g;
  const thrustTotal = 4 * MOTOR.thrustMax_g;
  // parts that turn when the gimbal is spun by a contact: both rings (thin hoop about a diameter: ½·m·r²)
  const ring = (g, r) => 0.5 * g / 1000 * r ** 2;
  const I = ring(16.5, GIMBAL.outer.r - GIMBAL.outer.band / 2) + ring(14.8, GIMBAL.inner.r - GIMBAL.inner.band / 2);
  const hoverW = 4 * motorPower(auw / 4) * INSTALL_LOSS + AVIONICS_W;
  const usableWh = capacityMah / 1000 * 7.6 * 0.85;
  return {
    capacityMah, battery: bat, quad_g: quad, gimbal_g: gimbal, auw_g: auw, mass: auw / 1000,
    thrustMax_N: thrustTotal / 1000 * 9.81, tw: thrustTotal / auw, I,
    hoverW, hoverMin: usableWh / hoverW * 60, usableWh,
  };
}

function interp(tab, x) {
  if (x <= tab[0][0]) return tab[0][1];
  for (let i = 1; i < tab.length; i++) if (x <= tab[i][0]) { const [x0, y0] = tab[i - 1], [x1, y1] = tab[i]; return y0 + (y1 - y0) * (x - x0) / (x1 - x0); }
  const [x0, y0] = tab[tab.length - 2], [x1, y1] = tab[tab.length - 1]; return y1 + (y1 - y0) * (x - x1) / (x1 - x0);
}
