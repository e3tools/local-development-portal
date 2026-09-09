// Generates the sample imagery used by the demo portal into `public/img/`.
//
// Everything is drawn procedurally as SVG so the repo carries no third-party
// photography: the portal ships with fictional data, and the illustrations are
// honest placeholders for the photos a real deployment would hold. Output is
// deterministic (mulberry32, fixed seed per file) so re-running the script
// produces a byte-identical tree and never churns the diff.
//
//   node scripts/generate-sample-images.mjs
//
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "public", "img");

const W = 800;
const H = 500;

// Same PRNG as src/lib/rng.ts so the look stays stable across regenerations.
function createRng(seed) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return {
    next,
    int: (min, max) => Math.floor(next() * (max - min + 1)) + min,
    pick: (arr) => arr[Math.floor(next() * arr.length)],
    chance: (p) => next() < p,
  };
}

const n = (x) => Math.round(x * 100) / 100;

/** Sky/light conditions — the Sahelian palette range of northern Togo. */
const LIGHTS = [
  { id: "aube", skyTop: "#f3c98d", skyBot: "#fae4c4", sun: "#fff3dc", sunY: 190, haze: "#f6d9ae" },
  { id: "midi", skyTop: "#7fb9dd", skyBot: "#d8ecf6", sun: "#ffffff", sunY: 90, haze: "#cfe6f2" },
  { id: "harmattan", skyTop: "#cdbfa2", skyBot: "#e9e0cb", sun: "#f5ead0", sunY: 150, haze: "#ded2b6" },
  { id: "apresmidi", skyTop: "#9dc9e0", skyBot: "#f0e4c8", sun: "#fff6e0", sunY: 130, haze: "#e2dcc0" },
];

/** Ground/vegetation conditions — dry season through to the rains. */
const GROUNDS = [
  { id: "seche", far: "#b9b183", near: "#a09a68", soil: "#b98f5e", tree: "#6f7f4a", treeDark: "#5a6a3c" },
  { id: "humide", far: "#8fae63", near: "#6f9350", soil: "#a97d51", tree: "#4f7038", treeDark: "#3d5a2b" },
  { id: "fin-saison", far: "#a8ab6f", near: "#8b9457", soil: "#b0855a", tree: "#617a42", treeDark: "#4c6234" },
];

const horizon = 300;

function defs(light, ground, id) {
  return `<defs>
    <linearGradient id="sky-${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${light.skyTop}"/>
      <stop offset="100%" stop-color="${light.skyBot}"/>
    </linearGradient>
    <linearGradient id="ground-${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${ground.far}"/>
      <stop offset="100%" stop-color="${ground.near}"/>
    </linearGradient>
    <radialGradient id="sun-${id}" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="${light.sun}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="${light.sun}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="vig-${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#000" stop-opacity="0.10"/>
      <stop offset="35%" stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.14"/>
    </linearGradient>
  </defs>`;
}

/** Layered hills receding to the horizon. */
function hills(rng, ground) {
  const layers = [
    { y: horizon - 46, fill: ground.far, op: 0.55 },
    { y: horizon - 26, fill: ground.far, op: 0.75 },
    { y: horizon - 10, fill: ground.near, op: 0.9 },
  ];
  return layers
    .map(({ y, fill, op }) => {
      let d = `M0 ${H} L0 ${n(y + rng.int(-6, 6))}`;
      for (let x = 100; x <= W; x += 100) {
        const cy = y + rng.int(-22, 10);
        d += ` Q ${n(x - 50)} ${n(cy)} ${x} ${n(y + rng.int(-8, 8))}`;
      }
      d += ` L${W} ${H} Z`;
      return `<path d="${d}" fill="${fill}" opacity="${op}"/>`;
    })
    .join("");
}

/** Scattered acacia/karité canopies along the mid ground. */
function trees(rng, ground, count, yMin, yMax) {
  let out = "";
  for (let i = 0; i < count; i++) {
    const x = rng.int(20, W - 20);
    const y = rng.int(yMin, yMax);
    const s = (y - horizon + 60) / 90;
    const r = n(16 * s + rng.int(0, 6));
    const trunk = n(14 * s);
    out += `<g opacity="${n(0.75 + rng.next() * 0.25)}">
      <rect x="${n(x - 1.6 * s)}" y="${n(y - trunk)}" width="${n(3.2 * s)}" height="${trunk}" fill="${ground.treeDark}"/>
      <ellipse cx="${x}" cy="${n(y - trunk - r * 0.55)}" rx="${r}" ry="${n(r * 0.62)}" fill="${ground.tree}"/>
      <ellipse cx="${n(x - r * 0.45)}" cy="${n(y - trunk - r * 0.35)}" rx="${n(r * 0.6)}" ry="${n(r * 0.42)}" fill="${ground.treeDark}" opacity="0.5"/>
    </g>`;
  }
  return out;
}

/** Dry-season grass tufts in the foreground. */
function tufts(rng, ground, count) {
  let out = "";
  for (let i = 0; i < count; i++) {
    const x = rng.int(0, W);
    const y = rng.int(horizon + 90, H - 6);
    const h = rng.int(6, 16);
    out += `<path d="M${x} ${y} q ${rng.int(-4, 4)} ${-h * 0.6} ${rng.int(-6, 6)} ${-h}" stroke="${ground.treeDark}" stroke-width="1.6" fill="none" opacity="0.5"/>`;
  }
  return out;
}

function figure(x, baseY, s, tone = "#2f3a33") {
  return `<g fill="${tone}" opacity="0.85">
    <circle cx="${x}" cy="${n(baseY - 30 * s)}" r="${n(4.2 * s)}"/>
    <path d="M${n(x - 4.5 * s)} ${n(baseY - 26 * s)} h${n(9 * s)} l${n(2 * s)} ${n(14 * s)} h${n(-13 * s)} Z"/>
    <rect x="${n(x - 4 * s)}" y="${n(baseY - 12 * s)}" width="${n(3 * s)}" height="${n(12 * s)}"/>
    <rect x="${n(x + 1 * s)}" y="${n(baseY - 12 * s)}" width="${n(3 * s)}" height="${n(12 * s)}"/>
  </g>`;
}

// ---------------------------------------------------------------------------
// Sector structures. Each returns SVG drawn against the ground plane.
// ---------------------------------------------------------------------------

const ROOF = "#8d5b3f";
const ROOF_TIN = "#9aa7ad";
const WALL = "#e6dcc8";
const WALL_SHADE = "#cbbfa6";

function shadow(cx, cy, rx) {
  return `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${n(rx * 0.13)}" fill="#000" opacity="0.13"/>`;
}

const STRUCTURES = {
  // Forage / pompe à motricité humaine + château d'eau
  eau: () => {
    const bx = 300;
    const by = 430;
    return `${shadow(520, 434, 70)}
    <g>
      <path d="M486 434 l10 -84 h48 l10 84 Z" fill="#b8bfc4"/>
      <rect x="470" y="316" width="100" height="46" rx="6" fill="#d8dde0"/>
      <rect x="470" y="316" width="100" height="12" rx="6" fill="#eef1f2"/>
      <rect x="493" y="362" width="54" height="6" fill="#9aa2a8"/>
    </g>
    ${shadow(bx, by, 58)}
    <rect x="${bx - 46}" y="${by - 10}" width="92" height="12" rx="3" fill="#c9c3b2"/>
    <rect x="${bx - 6}" y="${by - 66}" width="12" height="58" fill="#7d878d"/>
    <path d="M${bx + 4} ${by - 60} q 34 -6 40 16" stroke="#5f6a70" stroke-width="7" fill="none" stroke-linecap="round"/>
    <rect x="${bx - 30}" y="${by - 72}" width="30" height="8" rx="4" fill="#3f4a50"/>
    <path d="M${bx + 30} ${by - 42} q 10 12 2 26" stroke="#8fc6e6" stroke-width="4" fill="none" opacity="0.85"/>
    <ellipse cx="${bx + 34}" cy="${by - 4}" rx="24" ry="7" fill="#8fc6e6" opacity="0.55"/>
    <g fill="#d9a441"><rect x="${bx + 54}" y="${by - 26}" width="20" height="24" rx="3"/><rect x="${bx + 78}" y="${by - 22}" width="17" height="20" rx="3"/></g>
    ${figure(238, by, 1.25)}
    ${figure(206, by + 4, 1.1, "#3a4640")}`;
  },

  // Salles de classe + drapeau
  education: () => `${shadow(400, 438, 190)}
    <rect x="230" y="352" width="330" height="82" fill="${WALL}"/>
    <rect x="230" y="404" width="330" height="30" fill="${WALL_SHADE}"/>
    <path d="M214 352 h362 l-22 -34 h-318 Z" fill="${ROOF_TIN}"/>
    <path d="M214 352 h362 l-6 8 h-350 Z" fill="#7f8b91"/>
    ${[0, 1, 2].map((i) => `<rect x="${262 + i * 104}" y="${372}" width="46" height="34" fill="#5d6b63"/><rect x="${262 + i * 104}" y="${372}" width="46" height="34" fill="none" stroke="${WALL_SHADE}" stroke-width="3"/>`).join("")}
    ${[0, 1].map((i) => `<rect x="${318 + i * 104}" y="${374}" width="26" height="60" fill="#6f5a44"/>`).join("")}
    <rect x="596" y="300" width="4" height="134" fill="#9aa2a8"/>
    <path d="M600 302 h44 l-10 12 10 12 h-44 Z" fill="#2e7d4f"/>
    ${figure(178, 438, 1.3)}${figure(198, 442, 1.15, "#3a4640")}${figure(602, 440, 1.2, "#33403a")}`,

  // Unité de soins périphériques
  sante: () => `${shadow(400, 436, 165)}
    <rect x="268" y="346" width="264" height="90" fill="${WALL}"/>
    <rect x="268" y="410" width="264" height="26" fill="${WALL_SHADE}"/>
    <path d="M252 346 h296 l-26 -40 h-244 Z" fill="${ROOF}"/>
    <rect x="380" y="378" width="40" height="58" fill="#6f5a44"/>
    <rect x="300" y="368" width="42" height="32" fill="#5d6b63"/>
    <rect x="458" y="368" width="42" height="32" fill="#5d6b63"/>
    <g transform="translate(400 328)"><rect x="-6" y="-18" width="12" height="36" fill="#c8443c"/><rect x="-18" y="-6" width="36" height="12" fill="#c8443c"/></g>
    <rect x="556" y="392" width="52" height="44" rx="4" fill="#dfe4e2"/>
    <rect x="556" y="392" width="52" height="10" rx="4" fill="#c3ccc8"/>
    ${figure(232, 436, 1.3)}${figure(254, 440, 1.1, "#3a4640")}`,

  // Piste rurale réhabilitée + dalot
  pistes: (rng, ground) => `<path d="M320 ${horizon} L120 ${H} L560 ${H} L430 ${horizon} Z" fill="${ground.soil}"/>
    <path d="M320 ${horizon} L120 ${H} L172 ${H} L346 ${horizon} Z" fill="#fff" opacity="0.12"/>
    <path d="M430 ${horizon} L560 ${H} L506 ${H} L404 ${horizon} Z" fill="#000" opacity="0.07"/>
    ${[0, 1, 2, 3].map((i) => `<ellipse cx="${390 - i * 6}" cy="${330 + i * 44}" rx="${18 + i * 9}" ry="${3 + i}" fill="#000" opacity="0.06"/>`).join("")}
    <g>
      <rect x="286" y="392" width="228" height="16" fill="#b9b3a4"/>
      <rect x="286" y="408" width="228" height="10" fill="#8f8a7d"/>
      <rect x="300" y="418" width="18" height="34" fill="#a7a294"/>
      <rect x="482" y="418" width="18" height="34" fill="#a7a294"/>
      <path d="M318 418 h164 v22 h-164 Z" fill="#4a5a52" opacity="0.55"/>
    </g>
    ${[0, 1, 2, 3, 4].map((i) => `<rect x="${292 + i * 54}" y="374" width="6" height="20" fill="#e8e2d4"/><rect x="${292 + i * 54}" y="374" width="6" height="7" fill="#c8443c"/>`).join("")}
    ${figure(600, 452, 1.5)}
    ${tufts(rng, ground, 10)}`,

  // Magasin de stockage + sacs
  agriculture: () => `${shadow(400, 438, 172)}
    <rect x="272" y="340" width="256" height="98" fill="${WALL}"/>
    <rect x="272" y="412" width="256" height="26" fill="${WALL_SHADE}"/>
    <path d="M256 340 h288 l-24 -46 h-240 Z" fill="${ROOF_TIN}"/>
    <rect x="352" y="364" width="96" height="74" fill="#7c6a52"/>
    <path d="M352 364 h96 v74 h-96 Z" fill="none" stroke="#5f5140" stroke-width="4"/>
    <path d="M352 364 L448 438 M448 364 L352 438" stroke="#5f5140" stroke-width="3" opacity="0.6"/>
    <g fill="#e2d4b4">
      <ellipse cx="566" cy="424" rx="22" ry="15"/><ellipse cx="596" cy="430" rx="20" ry="14"/>
      <ellipse cx="578" cy="404" rx="20" ry="14"/>
    </g>
    <g fill="#cbb98f"><ellipse cx="566" cy="418" rx="14" ry="7"/><ellipse cx="578" cy="398" rx="12" ry="6"/></g>
    ${figure(232, 438, 1.3)}${figure(628, 442, 1.2, "#3a4640")}`,

  // Champ solaire + lampadaire
  energie: () => `${shadow(360, 430, 130)}
    ${[0, 1, 2].map((i) => {
      const x = 250 + i * 92;
      return `<g><rect x="${x + 24}" y="386" width="7" height="44" fill="#8c959b"/><rect x="${x + 48}" y="386" width="7" height="44" fill="#8c959b"/>
        <path d="M${x} 392 l16 -54 h74 l-16 54 Z" fill="#2c3f63"/>
        <path d="M${x} 392 l16 -54 h74 l-16 54 Z" fill="none" stroke="#8fa3c4" stroke-width="2"/>
        <path d="M${x + 24} 392 l16 -54 M${x + 48} 392 l16 -54 M${x + 8} 374 h72" stroke="#8fa3c4" stroke-width="1.6" opacity="0.7"/>
        <path d="M${x + 4} 348 l58 0" stroke="#dce6f5" stroke-width="4" opacity="0.35"/></g>`;
    }).join("")}
    <g><rect x="596" y="288" width="6" height="146" fill="#9aa2a8"/>
      <path d="M578 292 l40 -12 6 16 -40 12 Z" fill="#2c3f63" stroke="#8fa3c4" stroke-width="1.6"/>
      <rect x="586" y="300" width="28" height="9" rx="4" fill="#3f4a50"/>
      <path d="M600 312 l-22 34 h44 Z" fill="#ffe9a8" opacity="0.35"/></g>
    ${figure(206, 434, 1.3)}`,

  // Hangar de marché
  economie: (rng) => `${shadow(400, 440, 200)}
    <path d="M212 336 h376 l-30 -44 h-316 Z" fill="${ROOF_TIN}"/>
    <path d="M212 336 h376 l-8 10 h-360 Z" fill="#78848a"/>
    ${[0, 1, 2, 3, 4].map((i) => `<rect x="${232 + i * 84}" y="346" width="10" height="94" fill="#a89878"/>`).join("")}
    ${[0, 1, 2, 3].map((i) => {
      const x = 258 + i * 84;
      const c = ["#c8443c", "#2e7d4f", "#d9a441", "#4a63a8"][i];
      return `<g><rect x="${x}" y="398" width="58" height="10" rx="2" fill="#a2865f"/>
        <rect x="${x + 4}" y="408" width="50" height="30" fill="#8b7350" opacity="0.5"/>
        <ellipse cx="${x + 16}" cy="394" rx="12" ry="6" fill="${c}"/>
        <ellipse cx="${x + 40}" cy="394" rx="11" ry="6" fill="${c}" opacity="0.75"/></g>`;
    }).join("")}
    ${figure(226, 444, 1.35)}${figure(568, 446, 1.3, "#3a4640")}${figure(600, 442, 1.15)}
    ${tufts(rng, GROUNDS[0], 6)}`,

  // Centre communautaire + terrain de sport
  cohesion: () => `${shadow(330, 434, 150)}
    <rect x="222" y="352" width="216" height="82" fill="${WALL}"/>
    <rect x="222" y="410" width="216" height="24" fill="${WALL_SHADE}"/>
    <path d="M206 352 h248 l-124 -46 Z" fill="${ROOF}"/>
    <rect x="304" y="378" width="52" height="56" fill="#6f5a44"/>
    <rect x="248" y="374" width="38" height="28" fill="#5d6b63"/>
    <rect x="376" y="374" width="38" height="28" fill="#5d6b63"/>
    <g stroke="#e8e2d4" stroke-width="5" fill="none"><path d="M506 434 v-58 h96 v58"/><path d="M506 376 h96"/></g>
    <path d="M506 434 h96" stroke="#e8e2d4" stroke-width="3" opacity="0.5" fill="none"/>
    <circle cx="486" cy="428" r="10" fill="#f2f0e8" stroke="#3a4640" stroke-width="2"/>
    ${figure(462, 436, 1.3)}${figure(556, 430, 1.15, "#33403a")}${figure(590, 434, 1.2)}`,

  // Reboisement communautaire
  environnement: (rng, ground) => {
    let rows = "";
    for (let r = 0; r < 4; r++) {
      const y = 336 + r * 34;
      const s = 0.55 + r * 0.22;
      for (let i = 0; i < 7 - r; i++) {
        const x = 190 + i * (86 + r * 14) + r * 18;
        if (x > W - 40) continue;
        rows += `<g><rect x="${n(x - 1.8 * s)}" y="${n(y - 22 * s)}" width="${n(3.6 * s)}" height="${n(22 * s)}" fill="#6f5a44"/>
          <ellipse cx="${x}" cy="${n(y - 30 * s)}" rx="${n(16 * s)}" ry="${n(13 * s)}" fill="${ground.tree}"/>
          <ellipse cx="${n(x - 5 * s)}" cy="${n(y - 26 * s)}" rx="${n(9 * s)}" ry="${n(7 * s)}" fill="${ground.treeDark}" opacity="0.45"/>
          <path d="M${n(x - 12 * s)} ${y} q ${n(12 * s)} ${n(5 * s)} ${n(24 * s)} 0" stroke="${ground.soil}" stroke-width="${n(3 * s)}" fill="none" opacity="0.7"/></g>`;
      }
    }
    return `${rows}${figure(120, 452, 1.5)}${figure(96, 446, 1.3, "#3a4640")}${tufts(rng, ground, 8)}`;
  },

  // Concession villageoise — utilisé pour les photos de village
  village: (rng, ground) => {
    const hut = (x, y, s, roof) => `${shadow(x, n(y + 2), n(36 * s))}
      <path d="M${n(x - 34 * s)} ${y} a ${n(34 * s)} ${n(34 * s)} 0 0 1 ${n(68 * s)} 0 Z" fill="${WALL}"/>
      <path d="M${n(x - 34 * s)} ${y} a ${n(34 * s)} ${n(34 * s)} 0 0 1 ${n(68 * s)} 0 Z" fill="#000" opacity="0.06"/>
      <rect x="${n(x - 30 * s)}" y="${n(y - 34 * s)}" width="${n(60 * s)}" height="${n(34 * s)}" fill="${WALL}"/>
      <rect x="${n(x - 30 * s)}" y="${n(y - 10 * s)}" width="${n(60 * s)}" height="${n(10 * s)}" fill="${WALL_SHADE}"/>
      <path d="M${n(x - 44 * s)} ${n(y - 34 * s)} L${x} ${n(y - 76 * s)} L${n(x + 44 * s)} ${n(y - 34 * s)} Z" fill="${roof}"/>
      <path d="M${n(x - 44 * s)} ${n(y - 34 * s)} L${x} ${n(y - 76 * s)} L${n(x + 6 * s)} ${n(y - 34 * s)} Z" fill="#fff" opacity="0.10"/>
      <rect x="${n(x - 8 * s)}" y="${n(y - 24 * s)}" width="${n(16 * s)}" height="${n(24 * s)}" fill="#6f5a44"/>`;
    const granary = (x, y, s) => `${shadow(x, y, n(20 * s))}
      <rect x="${n(x - 16 * s)}" y="${n(y - 40 * s)}" width="${n(32 * s)}" height="${n(40 * s)}" rx="${n(6 * s)}" fill="#c2a878"/>
      <path d="M${n(x - 24 * s)} ${n(y - 40 * s)} L${x} ${n(y - 66 * s)} L${n(x + 24 * s)} ${n(y - 40 * s)} Z" fill="${ROOF}"/>`;
    return `${hut(250, 428, 1.05, ROOF)}${hut(392, 440, 1.25, "#7d5138")}${hut(548, 424, 0.95, ROOF)}
      ${granary(468, 420, 1)}
      ${figure(318, 448, 1.4)}${figure(342, 452, 1.2, "#3a4640")}${figure(614, 438, 1.25, "#33403a")}
      ${trees(rng, ground, 3, 330, 360)}
      ${tufts(rng, ground, 12)}`;
  },
};

function scene(structureKey, seed) {
  const rng = createRng(seed);
  const light = LIGHTS[seed % LIGHTS.length];
  const ground = GROUNDS[Math.floor(seed / LIGHTS.length) % GROUNDS.length];
  const id = `${structureKey}-${seed}`;
  const sunX = rng.int(120, 680);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img">
  ${defs(light, ground, id)}
  <rect width="${W}" height="${H}" fill="url(#sky-${id})"/>
  <circle cx="${sunX}" cy="${light.sunY}" r="140" fill="url(#sun-${id})"/>
  <circle cx="${sunX}" cy="${light.sunY}" r="26" fill="${light.sun}" opacity="0.9"/>
  <rect y="${horizon - 70}" width="${W}" height="70" fill="${light.haze}" opacity="0.35"/>
  ${hills(rng, ground)}
  <rect y="${horizon}" width="${W}" height="${H - horizon}" fill="url(#ground-${id})"/>
  ${trees(rng, ground, 6, 296, 322)}
  ${STRUCTURES[structureKey](rng, ground)}
  <rect width="${W}" height="${H}" fill="url(#vig-${id})"/>
</svg>
`;
}

const SECTOR_KEYS = ["eau", "education", "sante", "pistes", "agriculture", "energie", "economie", "cohesion", "environnement"];
const VARIANTS = 3;
const VILLAGE_SCENES = 8;

rmSync(OUT, { recursive: true, force: true });
mkdirSync(join(OUT, "secteurs"), { recursive: true });
mkdirSync(join(OUT, "villages"), { recursive: true });

let count = 0;
SECTOR_KEYS.forEach((key, s) => {
  for (let v = 0; v < VARIANTS; v++) {
    writeFileSync(join(OUT, "secteurs", `${key}-${v + 1}.svg`), scene(key, s * 7 + v * 13 + 3));
    count++;
  }
});
for (let v = 0; v < VILLAGE_SCENES; v++) {
  writeFileSync(join(OUT, "villages", `village-${v + 1}.svg`), scene("village", v * 5 + 11));
  count++;
}
console.log(`Wrote ${count} SVG scenes to public/img/`);
