/* Study Day tab. Data shape: study_day/tab.py StudyDayTab.data(). */
(function () {
  "use strict";

  const TAB = "study_day";
  const ui = { histOpen: false, draft: null }; // page-only state, survives re-renders

  const esc = (s) => desk.esc(s == null ? "" : String(s));
  const num = (n, d) => desk.num(n, d || 0);
  const cmd = (c, arg) => `data-cmd="${TAB}:${c}:${arg == null ? "" : esc(arg)}"`;
  const icon = (name) => (desk.icon ? desk.icon(name) || "" : "");

  // ── main column ────────────────────────────────────────────────────────────

  // "Study tomorrow's 493 now" follows the days picked in the Study ahead form.
  function aheadLabel(d, days) {
    const n = (d.ahead_counts || [])[days - 1];
    if (n == null) return null;
    return days === 1 ? `Study tomorrow's ${num(n)} now` : `Study the next ${days} days' ${num(n)} now`;
  }

  function formDays(d) {
    return Number((ui.draft || d.form || {}).days) || 1;
  }

  function headline(d) {
    const h = d.head || {};
    const acts = (h.actions || [])
      .map((a, i) => {
        const cls = `btn${i ? "" : " primary"}`;
        const label = a.cmd === "ahead" && aheadLabel(d, formDays(d));
        if (label) return `<button class="${cls}" data-sd="ahead">${esc(label)}</button>`;
        return `<button class="${cls}" ${cmd(a.cmd)}>${esc(a.label)}</button>`;
      })
      .join("");
    return `<header class="sd-head sd-${esc(h.state)}">
      <div class="sd-titlerow"><h1>${esc(h.title)}</h1><span class="sd-when">${esc(d.now)}</span></div>
      <p class="lede">${esc(h.lede)}</p>
      ${acts ? `<div class="btnrow sd-acts">${acts}</div>` : ""}
    </header>`;
  }

  function rangeText(rng, digits) {
    return `${num(rng[0], digits)}–${num(rng[1], digits)}`;
  }

  function labTable(d) {
    const rows = (d.rows || []).map((r) => {
      const f = r.flag || "";
      const rng = r.range;
      const max = rng ? Math.max(r.value * 1.08, rng[1] * 1.5, 1) : null;
      const ref = rng
        ? `${desk.rangeBar(r.value, rng, max)}<span class="sd-rng num">${rangeText(rng, r.digits)}</span>`
        : `<span class="norange">${esc(r.note || "no range yet")}</span>`;
      const note = rng && r.note ? `<span class="sd-note">${esc(r.note)}</span>` : "";
      return `<tr class="${f ? "is-" + f.toLowerCase() : ""}">
        <th scope="row">${esc(r.label)}</th>
        <td class="res num">${num(r.value, r.digits)}</td>
        <td class="sd-flag">${desk.flag(f)}</td>
        <td class="unit">${esc(r.unit)}</td>
        <td class="sd-refcell"><span class="ref">${ref}${note}</span></td>
      </tr>`;
    }).join("");
    return `<table class="lab sd-lab">
      <thead><tr><th scope="col">Measure</th><th scope="col" class="r">Today</th><th scope="col"><span class="sr">Flag</span></th>
        <th scope="col"><span class="sr">Unit</span></th><th scope="col">Your range</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p class="sd-foot">Your range is the middle 80% of your study days over the last ${num(d.range_days || 30)} days. H or L marks a value outside it.</p>`;
  }

  function forecastSection(d) {
    const fc = d.forecast || {};
    const show = fc.show || 14;
    const seg = [7, 14, 30]
      .map((n) => `<button role="radio" aria-checked="${n === show}" data-fc="${n}">${n} d</button>`)
      .join("");
    const hasAhead = (fc.ahead || []).some((v) => v > 0);
    const legend = [
      `<span><i class="sw" style="--c:var(--cap-lav)"></i>Can be studied ahead</span>`,
      `<span><i class="sw sd-sw-soft" style="--c:var(--cap-lav)"></i>Other due</span>`,
      hasAhead ? `<span><i class="sw" style="--c:var(--cap-green)"></i>In ${esc(d.ahead_name || "Ahead deck")}</span>` : "",
      fc.range ? `<span><i class="sw" style="--c:var(--band-strong)"></i>Your range</span>` : "",
    ].join("");
    return `<section class="sd-sec" aria-label="Forecast">
      <div class="sechead"><h2>Forecast</h2>
        <div class="seg" role="radiogroup" aria-label="Days shown">${seg}</div></div>
      <div class="sd-chart" id="sd-fc"></div>
      <div class="legend sd-legend">${legend}</div>
    </section>`;
  }

  const PACE_SPANS = [[30, "30 d"], [90, "90 d"], [180, "6 mo"], [365, "1 yr"]];

  // The picked span of the Pace data. 6 months and up are grouped by week,
  // each bar the average per day studied that week, so it still lines up with
  // your range and the average line.
  function paceView(p) {
    const n = p.show || 30;
    const reviews = (p.reviews || []).slice(-n);
    const minutes = (p.minutes || []).slice(-n);
    const days = (p.days || []).slice(-n);
    const past = reviews.slice(0, -1); // today isn't over yet
    const studied = past.filter((v) => v > 0).length;
    const sum = (a) => a.reduce((t, v) => t + (v || 0), 0);
    const view = {
      n,
      avg: studied ? Math.round(sum(past) / studied) : 0,
      avgMinutes: studied ? Math.round(sum(minutes.slice(0, -1)) / studied) : 0,
      studied,
      weekly: n > 90,
      values: reviews,
      labels: days,
    };
    if (view.weekly) {
      // Weeks counted back from today, so the last bar is this week.
      const values = [], labels = [];
      for (let end = reviews.length; end > 0; end -= 7) {
        const start = Math.max(0, end - 7);
        const week = reviews.slice(start, end);
        const on = week.filter((v) => v > 0).length;
        values.unshift(on ? Math.round(sum(week) / on) : 0);
        labels.unshift({ wd: "Week of", date: (days[start] || {}).date || "" });
      }
      view.values = values;
      view.labels = labels;
    }
    return view;
  }

  function paceSection(d) {
    const p = d.pace || {};
    const show = p.show || 30;
    const v = paceView(p);
    const seg = PACE_SPANS
      .map(([n, label]) => `<button role="radio" aria-checked="${n === show}" data-pace="${n}">${label}</button>`)
      .join("");
    const how = v.weekly ? "Each bar is a week: average reviews per day studied. " : "";
    return `<section class="sd-sec" aria-label="Pace">
      <div class="sechead"><h2>Pace</h2>
        <div class="seg" role="radiogroup" aria-label="Days shown">${seg}</div></div>
      <div class="sd-chart" id="sd-pace"></div>
      <p class="hint sd-under">${how}Average <span class="num">${num(v.avg)}</span> reviews and <span class="num">${num(v.avgMinutes)}</span> min on the <span class="num">${num(v.studied)}</span> days you studied in the last ${num(v.n)} days (dashed line).</p>
    </section>`;
  }

  function drawForecast(el, d) {
    const fc = d.forecast || {};
    const n = fc.show || 14;
    const box = el.querySelector("#sd-fc");
    if (!box) return;
    charts.bars(box, {
      values: (fc.due || []).slice(0, n),
      highlight: (fc.pullable || []).slice(0, n),
      stack: (fc.ahead || []).slice(0, n),
      labels: (fc.days || []).slice(0, n),
      range: fc.range || null,
      todayIndex: 0,
      height: 168,
    });
  }

  function drawPace(el, d) {
    const p = d.pace || {};
    const box = el.querySelector("#sd-pace");
    if (!box) return;
    const v = paceView(p);
    charts.bars(box, {
      values: v.values,
      labels: v.labels,
      range: p.range || null,
      avg: v.avg || null,
      todayIndex: v.weekly ? null : v.values.length - 1,
      height: 132,
    });
  }

  // ── side column ────────────────────────────────────────────────────────────

  function aheadBlock(d) {
    const a = d.ahead;
    if (!a) return studyAheadForm(d);
    const pct = a.total ? Math.round((a.done / a.total) * 100) : 0;
    const flags = [];
    if (a.due_now) flags.push(`<p class="sd-warn"><span class="num">${num(a.due_now)}</span> of these ${a.due_now === 1 ? "is" : "are"} due today and won't count in your normal decks.</p>`);
    if (a.stale) flags.push(`<p class="sd-warn">Built on an earlier day. Cards you haven't studied still have their original due dates.</p>`);
    return `<section class="sd-block" aria-label="Ahead deck">
      <h2>${esc(a.name)}</h2>
      <p class="meta">Created ${esc(a.created)}</p>
      <div class="sd-prog"><span class="sd-track" role="progressbar" aria-valuemin="0" aria-valuemax="${a.total}" aria-valuenow="${a.done}" aria-label="Ahead deck progress"><i style="width:${pct}%"></i></span></div>
      <p class="sd-progtext"><b class="num">${num(a.done)}</b> of <span class="num">${num(a.total)}</span> done · <span class="num">${num(a.left)}</span> left, about ${esc(a.minutes)}</p>
      ${flags.join("")}
      <div class="btnrow"><button class="btn primary" ${cmd("study")}>${icon("play")}Study</button><button class="btn" ${cmd("remove")}>Remove</button></div>
    </section>`;
  }

  function studyAheadForm(d) {
    const f = ui.draft || d.form || { days: 1, extra: 0 };
    const opts = [1, 2, 3, 4, 5, 6, 7]
      .map((n) => `<option value="${n}"${n === Number(f.days) ? " selected" : ""}>${n} ${n === 1 ? "day" : "days"}</option>`)
      .join("");
    return `<section class="sd-block" aria-label="Study ahead">
      <h2>Study ahead</h2>
      <p class="hint">Pull upcoming reviews into ${esc(d.ahead_name || "an Ahead deck")} and study them today.</p>
      <div class="field"><label for="sd-days">Cards due in the next</label><select id="sd-days" class="sel">${opts}</select></div>
      <div class="field"><label for="sd-extra">Extra new cards</label><input id="sd-extra" class="numin num" type="number" min="0" max="500" step="1" value="${Number(f.extra) || 0}"></div>
      <div class="btnrow"><button class="btn primary" data-sd="create">${icon("plus")}Create Ahead deck</button></div>
    </section>`;
  }

  function freezeBlock(d) {
    const fz = d.frozen;
    if (fz) {
      const what = fz.day ? `Day <span class="num">${num(fz.day)}</span> of your break` : "Starts tomorrow";
      return `<section class="sd-block" aria-label="Freeze">
        <h2>Freeze</h2>
        <p class="sd-frozen">${what}</p>
        <p class="meta">Frozen since ${esc(fz.since)}</p>
        <div class="btnrow"><button class="btn primary" ${cmd("unfreeze")}>Unfreeze</button></div>
      </section>`;
    }
    return `<section class="sd-block" aria-label="Freeze">
      <h2>Freeze</h2>
      <p class="hint">Taking a break? While frozen, scheduled cards move back a day so nothing piles up.</p>
      <div class="btnrow wrap"><button class="btn" ${cmd("freeze", "now")}>${icon("snow")}Freeze today</button><button class="btn" ${cmd("freeze", "tomorrow")}>From tomorrow</button></div>
    </section>`;
  }

  function historyBlock(d) {
    const h = d.history || { entries: [], shown: 5 };
    const all = h.entries || [];
    if (!all.length) {
      return `<section class="sd-block" aria-label="History"><h2>History</h2><p class="hint">Nothing yet. Study ahead and Freeze show up here, and can be undone.</p></section>`;
    }
    const shown = h.shown || 5;
    const list = ui.histOpen ? all : all.slice(0, shown);
    const items = list.map((e) => {
      const tag = e.undone ? `<span class="sd-tag">Undone</span>` : "";
      const undo = e.next ? `<button class="btn xs" ${cmd("undo")}>${icon("undo")}Undo</button>` : "";
      const note = e.note ? `<p class="sd-hnote">${esc(e.note)}</p>` : "";
      return `<li class="${e.undone ? "undone" : ""}${e.next ? " next" : ""}">
        <div class="sd-htop"><time>${esc(e.when)}</time>${tag}${undo}</div>
        <p class="sd-hlabel">${esc(e.label)}</p>${note}
      </li>`;
    }).join("");
    const more = all.length > shown
      ? `<button class="linkbtn muted sd-more" data-sd="more" aria-expanded="${ui.histOpen}">${ui.histOpen ? "Show fewer" : `Show ${num(all.length - shown)} more`}</button>`
      : "";
    return `<section class="sd-block" aria-label="History"><h2>History</h2><ol class="sd-hist">${items}</ol>${more}</section>`;
  }

  function decksLine(d) {
    return `<p class="sd-decks">Decks: <span class="sd-deckname">${esc(d.decks)}</span> <button class="linkbtn" ${cmd("decks")}>Change</button></p>`;
  }

  // ── events (bound once per section element) ──────────────────────────────

  function readDraft(el) {
    const days = el.querySelector("#sd-days");
    const extra = el.querySelector("#sd-extra");
    if (!days || !extra) return null;
    const x = Math.round(Number(extra.value));
    return {
      days: Math.max(1, Math.min(7, Number(days.value) || 1)),
      extra: Math.max(0, Math.min(500, Number.isFinite(x) ? x : 0)),
    };
  }

  function bind(el) {
    if (el._sdBound) return;
    el._sdBound = true;

    el.addEventListener("click", (ev) => {
      const fcBtn = ev.target.closest("[data-fc]");
      if (fcBtn && el.contains(fcBtn)) {
        const n = Number(fcBtn.dataset.fc);
        const d = desk.state[TAB];
        if (!d || !d.forecast || d.forecast.show === n) return;
        d.forecast.show = n;
        fcBtn.parentElement.querySelectorAll("[data-fc]").forEach((b) =>
          b.setAttribute("aria-checked", String(b === fcBtn)));
        drawForecast(el, d);
        desk.send(TAB, "forecast", String(n));
        return;
      }
      const paceBtn = ev.target.closest("[data-pace]");
      if (paceBtn && el.contains(paceBtn)) {
        const n = Number(paceBtn.dataset.pace);
        const d = desk.state[TAB];
        if (!d || !d.pace || d.pace.show === n) return;
        d.pace.show = n;
        const sec = paceBtn.closest(".sd-sec");
        sec.outerHTML = paceSection(d);
        drawPace(el, d);
        const again = el.querySelector(`[data-pace="${n}"]`);
        if (again) again.focus();
        desk.send(TAB, "pace", String(n));
        return;
      }
      const act = ev.target.closest("[data-sd]");
      if (!act || !el.contains(act)) return;
      if (act.dataset.sd === "create" || act.dataset.sd === "ahead") {
        const f = readDraft(el);
        if (!f) return;
        ui.draft = null;
        desk.send(TAB, "create", f);
      } else if (act.dataset.sd === "more") {
        ui.histOpen = !ui.histOpen;
        const d = desk.state[TAB];
        const sec = act.closest(".sd-block");
        if (d && sec) {
          sec.outerHTML = historyBlock(d);
          const btn = el.querySelector(".sd-more");
          if (btn) btn.focus();
        }
      }
    });

    // Keep unsent form edits across live re-renders.
    const keep = (ev) => {
      if (ev.target.id !== "sd-days" && ev.target.id !== "sd-extra") return;
      ui.draft = readDraft(el);
      const btn = el.querySelector('[data-sd="ahead"]');
      const label = btn && ui.draft && aheadLabel(desk.state[TAB] || {}, ui.draft.days);
      if (label) btn.textContent = label;
    };
    el.addEventListener("input", keep);
    el.addEventListener("change", keep);
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && ev.target.id === "sd-extra") {
        ev.preventDefault();
        const b = el.querySelector('[data-sd="create"]');
        if (b) b.click();
      }
    });
  }

  // ── render ─────────────────────────────────────────────────────────────────

  function render(el, d) {
    if (!d) return;
    bind(el);

    el.innerHTML = `<div class="cols sd">
      <div class="main sd-main">
        ${headline(d)}
        ${labTable(d)}
        ${forecastSection(d)}
        ${paceSection(d)}
      </div>
      <aside class="side sd-side" aria-label="Study ahead, Freeze and history">
        ${aheadBlock(d)}
        ${freezeBlock(d)}
        ${historyBlock(d)}
        ${decksLine(d)}
      </aside>
    </div>`;

    drawForecast(el, d);
    drawPace(el, d);
  }

  desk.register(TAB, { render });
})();
