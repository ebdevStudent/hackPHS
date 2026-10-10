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
  // ---- rolling cage (BOM p.3; icosahedral per review p.20)
  { group: "Cage", name: "1.0 mm carbon rod, 110 mm (cut from 1 × 500 mm stock)", qty: 30, g: 0.134, src: "CF 1.55 g/cm³" },
  { group: "Cage", name: "5-way hub, printed TPU 95A (minimal/hollow)", qty: 12, g: 0.8, src: "estimate, TPU 1.21 g/cm³" },
  { group: "Cage", name: "Gimbal ring, outer (R 92 mm, 5 × 3 mm PETG)", qty: 1, g: 7.4, src: "PETG 1.27 g/cm³" },
  { group: "Cage", name: "Gimbal ring, inner (R 85 mm, 5 × 3 mm PETG)", qty: 1, g: 6.8, src: "PETG 1.27 g/cm³" },
  { group: "Cage", name: "MR52 bearings + Ø2 mm steel pivot pins", qty: 1, g: 1.6, src: "6 × 0.2 g + pins" },
  { group: "Cage", name: "Centre mount TPU/PETG + silicone dampers", qty: 1, g: 3.5, src: "estimate" },
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

export const CAGE = {
  shape: "icosahedron", circumradius: 0.1125, hubRadius: 0.005, rodRadius: 0.0005,
  edge: 0.1125 / 0.9510565, ringBig: [0.087, 0.092], ringSmall: [0.080, 0.085],
  muHub: 0.75, muRod: 0.30, eHub: 0.35,     // TPU hub on hard floor; carbon rod; flexible 1 mm cage absorbs energy
};

export const INSTALL_LOSS = 1.12;       // cage rods / rings / ducts in the prop wash raise hover power (review p.25)
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
  const quad = sum("Quad"), cage = sum("Cage"), auw = quad + cage + bat.g;
  const thrustTotal = 4 * MOTOR.thrustMax_g;
  // rotating cage parts: rods + hubs at ~R, half of each ring (rings turn partially with the cage)
  const shell = (30 * 0.134 + 12 * 0.8) / 1000, rings = (7.4 + 6.8) / 2 / 1000;
  const I = (2 / 3) * shell * CAGE.circumradius ** 2 + 0.5 * rings * 0.088 ** 2 * 2;
  const hoverW = 4 * motorPower(auw / 4) * INSTALL_LOSS + AVIONICS_W;
  const usableWh = capacityMah / 1000 * 7.6 * 0.85;
  return {
    capacityMah, battery: bat, quad_g: quad, cage_g: cage, auw_g: auw, mass: auw / 1000,
    thrustMax_N: thrustTotal / 1000 * 9.81, tw: thrustTotal / auw, I,
    hoverW, hoverMin: usableWh / hoverW * 60, usableWh,
  };
}

function interp(tab, x) {
  if (x <= tab[0][0]) return tab[0][1];
  for (let i = 1; i < tab.length; i++) if (x <= tab[i][0]) { const [x0, y0] = tab[i - 1], [x1, y1] = tab[i]; return y0 + (y1 - y0) * (x - x0) / (x1 - x0); }
  const [x0, y0] = tab[tab.length - 2], [x1, y1] = tab[tab.length - 1]; return y1 + (y1 - y0) * (x - x1) / (x1 - x0);
}
