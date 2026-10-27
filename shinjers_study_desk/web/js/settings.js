/* Settings tab: appearance, then every tab's settings() sections. */
(function () {
  const MODES = [["auto", "Auto"], ["light", "Light"], ["dark", "Dark"]];

  function send(tab, key, value) {
    desk.send("settings", "set", { tab, key, value });
  }

  function seg(attrs, options, value, label) {
    return `<div class="seg" role="radiogroup" aria-label="${desk.esc(label)}">` +
      options.map(([v, l]) =>
        `<button type="button" role="radio" ${attrs} data-value="${desk.esc(v)}" ` +
        `aria-checked="${String(v) === String(value)}">${desk.esc(l)}</button>`).join("") +
      "</div>";
  }

  function row(id, label, hint, control) {
    return `<div class="set-row"><div class="set-text">` +
      `<div class="set-label" id="${id}">${desk.esc(label)}</div>` +
      (hint ? `<div class="hint">${desk.esc(hint)}</div>` : "") +
      `</div><div class="set-ctl">${control}</div></div>`;
  }

  function control(section, r, id) {
    const tk = `data-tab="${desk.esc(section.tab)}" data-key="${desk.esc(r.key)}"`;
    if (r.type === "switch") {
      return `<button type="button" class="sw-t" role="switch" ${tk} data-focus="${desk.esc(section.tab + "." + r.key)}" ` +
        `aria-checked="${!!r.value}" aria-labelledby="${id}"></button>`;
    }
    if (r.type === "choice") {
      const opts = r.options || [];
      if (opts.length <= 3) return seg(`data-choice ${tk}`, opts, r.value, r.label);
      return `<select class="sel" ${tk} aria-labelledby="${id}">` +
        opts.map(([v, l]) => `<option value="${desk.esc(v)}"${String(v) === String(r.value) ? " selected" : ""}>${desk.esc(l)}</option>`).join("") +
        "</select>";
    }
    if (r.type === "decks") {
      return `<span class="set-decks">${desk.esc(r.text || "")}</span>` +
        `<button type="button" class="btn sm" data-decks ${tk}>Choose…</button>`;
    }
    return "";
  }

  function appearanceSection(data) {
    const a = data.appearance || desk.appearance();
    const dark = desk.appearance().dark;
    const themes = data.themes || [["slate", "Slate"]];
    // Each tile is a tiny Study Desk window in that theme (and the current mode).
    const sw = themes.map(([k, l]) =>
      `<button type="button" class="theme-sw" data-set-theme="${desk.esc(k)}" aria-pressed="${k === a.theme}">` +
      `<span class="theme-mini" data-theme="${desk.esc(k)}"${dark ? ' data-dark="1"' : ""} aria-hidden="true"><i class="tm-rail"></i>` +
      `<span class="tm-page"><i class="tm-line"></i><i class="tm-btn"></i></span></span>` +
      `<span class="theme-name">${desk.esc(l)}</span></button>`).join("");
    return `<section class="set-section"><h2>Appearance</h2><div class="set-card">` +
      row("set-mode", "Mode", "Auto follows Anki's night mode.", seg("data-set-mode", MODES, a.mode, "Mode")) +
      `<div class="set-row set-themes"><div class="set-text"><div class="set-label" id="set-theme">Color</div>` +
      `<div class="hint">Changes the Study Desk window and the status bar on the Decks screen.</div></div>` +
      `<div class="theme-grid" role="group" aria-labelledby="set-theme">${sw}</div></div>` +
      "</div></section>";
  }

  function render(el, data) {
    data = data || {};
    let html = `<div class="set-wrap"><h1>Settings</h1>` + appearanceSection(data);
    (data.sections || []).forEach((s, si) => {
      if (!s.rows || !s.rows.length) return;
      html += `<section class="set-section"><h2>${desk.esc(s.title)}</h2><div class="set-card">` +
        s.rows.map((r, ri) => {
          const id = `set-${si}-${ri}`;
          return row(id, r.label, r.hint, control(s, r, id));
        }).join("") + "</div></section>";
    });
    el.innerHTML = html + "</div>";
    bind(el);
  }

  function setAppearance(key, value) {
    const st = desk.state.settings;
    if (st) st.appearance = Object.assign({}, st.appearance, { [key]: value });
    desk.setAppearance({ [key]: value });
    send("settings", key, value);
    if (st) desk.receive("settings", st);
  }

  function findRow(tab, key) {
    const st = desk.state.settings;
    for (const s of (st && st.sections) || []) {
      if ((s.tab || "settings") !== tab) continue;
      for (const r of s.rows || []) if (r.key === key) return r;
    }
    return null;
  }

  function bind(el) {
    if (el.dataset.bound) return;
    el.dataset.bound = "1";
    el.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b || !el.contains(b)) return;
      if (b.hasAttribute("data-set-mode")) return setAppearance("mode", b.dataset.value);
      if (b.hasAttribute("data-set-theme")) return setAppearance("theme", b.dataset.setTheme);
      const { tab, key } = b.dataset;
      if (!key) return;
      if (b.classList.contains("sw-t")) {
        const on = b.getAttribute("aria-checked") !== "true";
        b.setAttribute("aria-checked", String(on));
        const r = findRow(tab, key);
        if (r) r.value = on;
        send(tab, key, on);
      } else if (b.hasAttribute("data-choice")) {
        b.parentElement.querySelectorAll("button").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
        const r = findRow(tab, key);
        if (r) r.value = b.dataset.value;
        send(tab, key, b.dataset.value);
      } else if (b.hasAttribute("data-decks")) {
        send(tab, key, null);
      }
    });
    el.addEventListener("change", (e) => {
      const s = e.target.closest("select[data-key]");
      if (!s) return;
      const r = findRow(s.dataset.tab, s.dataset.key);
      if (r) r.value = s.value;
      send(s.dataset.tab, s.dataset.key, s.value);
    });
  }

  desk.register("settings", { render });
})();
