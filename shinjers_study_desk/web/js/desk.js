/* Shinjer's Study Desk page core: boot, tab switching, data in, commands out, theme,
   helpers. See web/README.md for the contract. */
window.desk = window.desk || {};

(function () {
  // Fallback only: Python sends each tab's icon in boot.tabs.
  const TAB_ICONS = { study_day: "calendar", trouble: "target", keyboard: "keyboard", settings: "gear" };
  const renderers = {};
  let tabs = [];
  let active = null;
  let appearance = { mode: "auto", theme: "slate" };
  let night = false;

  desk.state = {};

  // ── commands out ──────────────────────────────────────────────────────────
  // Anki defines pycmd only once its Qt web channel connects, which can be
  // after DOMContentLoaded, so hold messages until then. Outside Anki (the
  // preview) there's no `qt` object and messages just go to the console.
  const queue = [];
  function post(msg) {
    if (typeof window.pycmd === "function") window.pycmd(msg);
    else if (window.qt) {
      queue.push(msg);
      if (queue.length === 1) flush();
    } else console.log("[pycmd]", msg);
  }
  function flush() {
    if (typeof window.pycmd !== "function") return setTimeout(flush, 20);
    while (queue.length) window.pycmd(queue.shift());
  }
  desk.send = function (tab, cmd, arg) {
    let a = arg;
    if (a === undefined || a === null) a = "";
    else if (typeof a === "object") a = JSON.stringify(a);
    post(`${tab}:${cmd}:${a}`);
  };

  // ── helpers ───────────────────────────────────────────────────────────────
  desk.esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  };
  desk.num = function (n, digits = 0) {
    if (n == null || n === "" || isNaN(n)) return "";
    return Number(n).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  };
  desk.flag = function (f) {
    if (f === "H" || f === "h") return '<span class="flag h" title="Above your usual range">H</span>';
    if (f === "L" || f === "l") return '<span class="flag l" title="Below your usual range">L</span>';
    return "";
  };
  desk.rangeBar = function (value, range, max) {
    const v = Number(value) || 0;
    let top = Number(max);
    if (!(top > 0)) top = Math.max(v, range ? Number(range[1]) : 0, 1);
    const pct = (x) => (Math.max(0, Math.min(1, x / top)) * 100).toFixed(1) + "%";
    let cls = "rb", band = "";
    if (range && range.length === 2) {
      const lo = Number(range[0]), hi = Number(range[1]);
      band = `<span class="band" style="--lo:${pct(lo)};--hi:${pct(hi)}"></span>`;
      if (v > hi) cls += " h";
      else if (v < lo) cls += " l";
    }
    return `<span class="${cls}" aria-hidden="true">${band}<span class="mk" style="--v:${pct(v)}"></span></span>`;
  };

  // ── tabs ──────────────────────────────────────────────────────────────────
  desk.register = function (id, spec) { renderers[id] = spec; };

  function panel(id) { return document.getElementById("tab-" + id); }

  function stateHtml(kind, title, msg) {
    if (kind === "loading") return `<div class="loading" role="status">${desk.esc(title || "Loading…")}</div>`;
    return `<div class="error" role="alert">${desk.icon("alert")}<h2>${desk.esc(title)}</h2>` +
      (msg ? `<pre>${desk.esc(msg)}</pre>` : "") + "</div>";
  }

  function focusKey(el) {
    const a = document.activeElement;
    if (!a || a === document.body || !el.contains(a)) return null;
    if (a.id) return "#" + CSS.escape(a.id);
    for (const attr of ["data-focus", "data-cmd", "data-key"]) {
      const v = a.getAttribute(attr);
      if (v != null) return `[${attr}="${CSS.escape(v)}"]`;
    }
    return null;
  }

  function draw(id) {
    const el = panel(id);
    if (!el) return;
    const spec = renderers[id];
    const content = document.querySelector(".content");
    const scroll = content ? content.scrollTop : 0;
    const fk = focusKey(el);
    try {
      if (!spec || typeof spec.render !== "function") throw new Error(`No page code is registered for "${id}".`);
      spec.render(el, desk.state[id]);
    } catch (err) {
      console.error(err);
      el.innerHTML = stateHtml("error", "This tab couldn't be drawn.", (err && err.message) || String(err));
    }
    if (id === active && content) content.scrollTop = scroll;
    if (fk) {
      const again = el.querySelector(fk);
      if (again) again.focus({ preventScroll: true });
    }
  }

  function select(id) {
    if (!panel(id)) return false;
    active = id;
    for (const t of tabs) {
      const p = panel(t.id);
      if (p) p.hidden = t.id !== id;
    }
    document.querySelectorAll(".rail .tab[data-tab]").forEach((b) => {
      if (b.dataset.tab === id) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    const content = document.querySelector(".content");
    if (content) content.scrollTop = 0;
    if (!(id in desk.state)) panel(id).innerHTML = stateHtml("loading");
    return true;
  }

  desk.show = function (id) { select(id); };

  desk.open = function (id) {
    if (id === active) return;
    if (select(id)) post(`desk:open:${id}`);
  };

  desk.receive = function (id, data) {
    desk.state[id] = data;
    draw(id);
  };

  desk.patch = function (id, part) {
    const cur = desk.state[id];
    desk.state[id] = cur && typeof cur === "object" ? Object.assign({}, cur, part) : part;
    // A tab can redraw just the part that changed; it returns true if it did.
    const spec = renderers[id], el = panel(id);
    if (spec && typeof spec.patch === "function" && el && spec.patch(el, desk.state[id], part)) return;
    draw(id);
  };

  desk.fail = function (id, msg) {
    const el = panel(id);
    if (el) el.innerHTML = stateHtml("error", "Something went wrong loading this tab.", msg);
  };

  // ── appearance ────────────────────────────────────────────────────────────
  function isDark() {
    return appearance.mode === "dark" || (appearance.mode === "auto" && night);
  }

  function applyLook() {
    const root = document.documentElement;
    const dark = isDark();
    if (dark) root.setAttribute("data-dark", "1");
    else root.removeAttribute("data-dark");
    root.setAttribute("data-theme", appearance.theme || "slate");
    const btn = document.querySelector(".mode-toggle");
    if (btn) {
      const label = dark ? "Switch to light" : "Switch to dark";
      btn.innerHTML = desk.icon(dark ? "sun" : "moon");
      btn.title = label;
      btn.setAttribute("aria-label", label);
    }
  }

  desk.appearance = function () { return Object.assign({ dark: isDark() }, appearance); };

  desk.setAppearance = function (a) {
    appearance = Object.assign({}, appearance, a || {});
    applyLook();
  };

  desk.setNight = function (on) {
    night = !!on;
    applyLook();
  };

  desk.toggleMode = function () {
    const mode = isDark() ? "light" : "dark";
    desk.setAppearance({ mode });
    post(`desk:pref:mode:${mode}`);
    if (desk.state.settings && desk.state.settings.appearance) {
      desk.state.settings.appearance.mode = mode;
      if (active === "settings") draw("settings");
    }
  };

  // ── boot ──────────────────────────────────────────────────────────────────
  function tabButton(t) {
    const icon = desk.icon(t.icon) || desk.icon(TAB_ICONS[t.id]) || desk.icon("list");
    return `<button type="button" class="tab" data-tab="${desk.esc(t.id)}">` +
      `<span class="ico">${icon}</span><span>${desk.esc(t.title)}</span></button>`;
  }

  desk.boot = function (b) {
    tabs = (b && b.tabs) || [];
    appearance = Object.assign({ mode: "auto", theme: "slate" }, (b && b.appearance) || {});
    night = !!(b && b.night);

    const main = tabs.filter((t) => t.id !== "settings");
    const settings = tabs.find((t) => t.id === "settings");
    const railTabs = document.querySelector(".rail-tabs");
    const railFoot = document.querySelector(".rail-foot");
    if (railTabs) railTabs.innerHTML = main.map(tabButton).join("");
    if (railFoot) {
      railFoot.innerHTML = '<button type="button" class="tab mode-toggle"></button>' +
        (settings ? tabButton(settings) : "");
    }

    const content = document.querySelector(".content");
    if (content) {
      content.innerHTML = tabs.map((t) =>
        `<section id="tab-${desk.esc(t.id)}" class="tab-panel" aria-label="${desk.esc(t.title)}" hidden></section>`
      ).join("");
    }
    desk.state = {};
    active = null;
    applyLook();
    const start = tabs.some((t) => t.id === b.active) ? b.active : (tabs[0] && tabs[0].id);
    if (start) select(start);
  };

  // ── events ────────────────────────────────────────────────────────────────
  document.addEventListener("click", (e) => {
    const tabBtn = e.target.closest(".rail .tab");
    if (tabBtn) {
      if (tabBtn.classList.contains("mode-toggle")) desk.toggleMode();
      else if (tabBtn.dataset.tab) desk.open(tabBtn.dataset.tab);
      return;
    }
    const c = e.target.closest("[data-cmd]");
    if (c && !c.disabled && c.getAttribute("aria-disabled") !== "true") {
      e.preventDefault();
      post(c.getAttribute("data-cmd"));
    }
  });

  // Up/Down moves between rail tabs.
  document.addEventListener("keydown", (e) => {
    if (!e.target.closest || !e.target.closest(".rail") || (e.key !== "ArrowDown" && e.key !== "ArrowUp")) return;
    const btns = Array.from(document.querySelectorAll(".rail .tab"));
    const i = btns.indexOf(e.target.closest(".tab"));
    if (i < 0) return;
    e.preventDefault();
    btns[(i + (e.key === "ArrowDown" ? 1 : btns.length - 1)) % btns.length].focus();
  });

  document.addEventListener("DOMContentLoaded", () => post("desk:ready"));
})();
