const ZONE_RE = /^([TMDC])(\d{3})(s)?$/;

const LANGS = [
  { code: "la", flag: "../flags/Drapeau-Vatican.jpg", label: "Latine", alt: "Vatican flag \u2014 Latin" },
  { code: "it", flag: "../flags/Drapeau-Italie.jpg", label: "Italiano", alt: "Italian flag \u2014 Italian" },
  { code: "fr", flag: "../flags/Drapeau-France.jpg", label: "Fran\u00e7ais", alt: "French flag \u2014 French" },
  { code: "en", flag: "../flags/Drapeau-Grande-Bretagne.jpg", label: "English", alt: "British flag \u2014 English" },
];

const UI = {
  la: {
    htmlLang: "la",
    skip: "Ad tabulam ire",
    subtitle: "Scaenarium 1",
    themeToLight: "Ad lucidum modum ire",
    themeToDark: "Ad obscurum modum ire",
    loadError: "Tabulam vel JSON onerare non potuimus.",
    ariaMap: "Tabula Europae et Orientis Propinqui",
    noEntry: (id) => `Nulla inscriptio JSON pro <code>${id}</code>.`,
    prompt: "Provinciam, litus vel mare tange.",
    terrain: "Terrenum",
    mp: "Impensa motus",
    city: "Civitas",
    production: "Productio",
    sovereign: "Dominus",
    neighborsLand: "Vicini (Terra)",
    neighborsSea: "Vicini (Mare)",
    mpUnit: "MP",
    none: "\u2014",
  },
  it: {
    htmlLang: "it",
    skip: "Vai alla mappa",
    subtitle: "Scenario 1",
    themeToLight: "Passa al tema chiaro",
    themeToDark: "Passa al tema scuro",
    loadError: "Impossibile caricare la mappa o il JSON.",
    ariaMap: "Mappa d'Europa e del Vicino Oriente",
    noEntry: (id) => `Nessuna voce JSON per <code>${id}</code>.`,
    prompt: "Clicca una provincia, una costa o un mare.",
    terrain: "Terreno",
    mp: "Costo di movimento",
    city: "Citt\u00e0",
    production: "Produzione",
    sovereign: "Sovrano",
    neighborsLand: "Confinanti (Terra)",
    neighborsSea: "Confinanti (Mare)",
    mpUnit: "MP",
    none: "\u2014",
  },
  fr: {
    htmlLang: "fr",
    skip: "Aller \u00e0 la carte",
    subtitle: "Sc\u00e9nario 1",
    themeToLight: "Passer en mode clair",
    themeToDark: "Passer en mode sombre",
    loadError: "Impossible de charger la carte ou le JSON.",
    ariaMap: "Carte d\u2019Europe et du Proche-Orient",
    noEntry: (id) => `Pas d\u2019entr\u00e9e JSON pour <code>${id}</code>.`,
    prompt: "Cliquez une province, une c\u00f4te ou une mer.",
    terrain: "Terrain",
    mp: "Co\u00fbt",
    city: "Ville",
    production: "Production",
    sovereign: "Souverain",
    neighborsLand: "Voisins (Terre)",
    neighborsSea: "Voisins (Mer)",
    mpUnit: "MP",
    none: "\u2014",
  },
  en: {
    htmlLang: "en",
    skip: "Skip to the map",
    subtitle: "Scenario 1",
    themeToLight: "Switch to light mode",
    themeToDark: "Switch to dark mode",
    loadError: "Could not load the map or the JSON.",
    ariaMap: "Map of Europe and the Near East",
    noEntry: (id) => `No JSON entry for <code>${id}</code>.`,
    prompt: "Click a province, a coast, or a sea.",
    terrain: "Terrain",
    mp: "MP cost",
    city: "Town",
    production: "Production",
    sovereign: "Sovereign",
    neighborsLand: "Neighbors (Land)",
    neighborsSea: "Neighbors (Sea)",
    mpUnit: "MP",
    none: "\u2014",
  },
};

const $ = (sel) => document.querySelector(sel);

let lang = "en";

function landId(id) {
  const m = ZONE_RE.exec(id || "");
  if (!m) return null;
  return m[1] === "C" ? `T${m[2]}` : id;
}

function relatedIds(id) {
  const m = ZONE_RE.exec(id || "");
  if (!m) return [];
  const num = m[2];
  if (m[1] === "C" || m[1] === "T") {
    return [`T${num}`, `C${num}`, `C${num}s`];
  }
  return [id];
}

function themeIcons(mode) {
  return mode === "dark"
    ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
    : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
}

(function initTheme() {
  const root = document.documentElement;
  const btn = $("[data-theme-toggle]");
  let mode = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  const apply = () => {
    root.setAttribute("data-theme", mode);
    if (btn) {
      btn.setAttribute("aria-label", mode === "dark" ? UI[lang].themeToLight : UI[lang].themeToDark);
      btn.innerHTML = themeIcons(mode);
    }
  };
  apply();
  btn?.addEventListener("click", () => {
    mode = mode === "dark" ? "light" : "dark";
    apply();
  });
  window.__refreshThemeLabel = apply;
})();

async function main() {
  const stage = $("#stage");
  const panel = $("#panel");
  const langsNav = $("[data-langs]");

  const [mapRes, dataRes] = await Promise.all([
    fetch("./map.svg"),
    fetch("./province-map.json"),
  ]);
  if (!mapRes.ok || !dataRes.ok) {
    panel.innerHTML = `<p class="status">${UI[lang].loadError}</p>`;
    return;
  }
  const svgText = await mapRes.text();
  const doc = await dataRes.json();
  const byId = Object.fromEntries(doc.zones.map((z) => [z.id, z]));

  stage.innerHTML = svgText;
  const svg = stage.querySelector("svg");
  svg.removeAttribute("width");
  svg.removeAttribute("height");
  svg.setAttribute("role", "img");
  const rivers = svg.getElementById("layer3");
  if (rivers) rivers.setAttribute("pointer-events", "none");

  let selected = null;

  function applyStaticStrings() {
    const t = UI[lang];
    document.documentElement.setAttribute("lang", t.htmlLang);
    $(".skip").textContent = t.skip;
    $("[data-i18n='subtitle']").textContent = t.subtitle;
    svg.setAttribute("aria-label", t.ariaMap);
    window.__refreshThemeLabel?.();
  }

  function paint(id) {
    svg.querySelectorAll(".is-selected").forEach((n) => n.classList.remove("is-selected"));
    relatedIds(id).forEach((zid) => svg.getElementById(zid)?.classList.add("is-selected"));
    selected = id;
  }

  function show(id) {
    const t = UI[lang];
    const zone = byId[id];
    if (!zone) {
      panel.innerHTML = `<p class="empty">${t.noEntry(id)}</p>`;
      return;
    }
    const land = zone.kind === "coastal" && zone.parent_id ? byId[zone.parent_id] : null;
    const focus = land || zone;
    const focusText = focus.i18n[lang];

    const edges = [...(focus.adjacencies || [])];
    if (focus.kind === "land") {
      const coastal = byId["C" + focus.id.slice(1)];
      if (coastal) edges.push(...(coastal.adjacencies || []));
    }

    function edgeCost(edge, target) {
      const extra = edge.extra_cost || 0;
      if (edge.feature === "strait") return extra;
      const targetMove = target ? target.move_cost ?? 0 : 0;
      return targetMove + extra;
    }

    const neighborsLand = [];
    const neighborsSea = [];
    edges.forEach((edge) => {
      const target = byId[edge.id];
      const targetName = target ? target.i18n[lang].name || target.id : edge.id;
      const cost = edgeCost(edge, target);
      const entry = { id: edge.id, label: `${targetName} (${cost} ${t.mpUnit})` };
      if (edge.edge === "cabotage" || edge.edge === "high_seas") neighborsSea.push(entry);
      else neighborsLand.push(entry);
    });

    panel.innerHTML = `
      <h2>${focusText.name || focus.id}</h2>
      <dl>
        <div class="row row-split">
          <div class="field"><dt>${t.terrain}</dt><dd>${focusText.terrain || t.none}</dd></div>
          <div class="field"><dt>${t.mp}</dt><dd>${focus.move_cost ?? t.none}</dd></div>
        </div>
        <div class="row row-split">
          <div class="field"><dt>${t.city}</dt><dd>${focusText.city || t.none}</dd></div>
          <div class="field"><dt>${t.production}</dt><dd>${focusText.production || t.none}</dd></div>
        </div>
        <div class="row"><dt>${t.sovereign}</dt><dd>${focusText.sovereign || t.none}</dd></div>
        <div class="row">
          <dt>${t.neighborsLand}</dt>
          <dd>
            ${
              neighborsLand.length
                ? `<ul class="neighbors">${neighborsLand
                    .map((n) => `<li><button type="button" data-go="${n.id}">${n.label}</button></li>`)
                    .join("")}</ul>`
                : t.none
            }
          </dd>
        </div>
        <div class="row">
          <dt>${t.neighborsSea}</dt>
          <dd>
            ${
              neighborsSea.length
                ? `<ul class="neighbors">${neighborsSea
                    .map((n) => `<li><button type="button" data-go="${n.id}">${n.label}</button></li>`)
                    .join("")}</ul>`
                : t.none
            }
          </dd>
        </div>
      </dl>
    `;
  }

  function showPrompt() {
    panel.innerHTML = `<p class="empty">${UI[lang].prompt}</p>`;
  }

  function select(id) {
    if (!ZONE_RE.test(id)) return;
    paint(id);
    show(id);
  }

  function setLang(code) {
    if (!UI[code] || code === lang) return;
    lang = code;
    langsNav.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
    applyStaticStrings();
    if (selected) show(selected);
    else showPrompt();
  }

  langsNav.innerHTML = LANGS.map(
    (l) => `<button type="button" data-lang="${l.code}" aria-pressed="${l.code === lang}" title="${l.label}">
      <img src="${l.flag}" alt="${l.alt}" />
    </button>`
  ).join("");
  langsNav.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-lang]");
    if (btn) setLang(btn.dataset.lang);
  });

  svg.addEventListener("click", (event) => {
    const node = event.target.closest("[id]");
    if (!node || node === svg) return;
    select(node.id);
  });

  panel.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-go]");
    if (btn) select(btn.getAttribute("data-go"));
  });

  applyStaticStrings();
  showPrompt();
}

main().catch((err) => {
  $("#panel").innerHTML = `<p class="status">${err.message}</p>`;
});
