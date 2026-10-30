/* Trouble Spots: topics ranked by how often you miss them, and the cards
   behind the selected topic. Data shape: trouble/tab.py _payload(). */
(function () {
  "use strict";

  const esc = (s) => desk.esc(s == null ? "" : String(s));
  const pct = (f, d = 0) => desk.num((f || 0) * 100, d) + "%";

  // Topic names are paths ("Endocrine › Physiology"): mute the parents.
  function topicName(name) {
    const parts = String(name || "").split(" › ");
    const last = parts.pop();
    if (!parts.length) return esc(last);
    return `<span class="tr-sec">${esc(parts.join(" › "))} › </span>${esc(last)}`;
  }

  function controls(c) {
    const periods = (c.periods || []).map(([d, label]) =>
      `<button type="button" role="radio" aria-checked="${d === c.days}" data-days="${d}">${esc(label)}</button>`
    ).join("");
    const groups = (c.groups || []).map(([k, label]) =>
      `<option value="${esc(k)}"${k === c.group ? " selected" : ""}>${esc(label)}</option>`
    ).join("");
    const custom = c.group === "custom"
      ? `<label class="tr-ctl"><span>Tag</span><input type="text" class="tr-custom" value="${esc(c.custom)}" placeholder="e.g. #AK_Step1" spellcheck="false"></label>`
      : "";
    return `
      <div class="tr-controls">
        <span class="tr-ctl tr-decks"><span>Decks</span><b title="${esc(c.decks)}">${esc(c.decks)}</b>
          <button type="button" class="linkbtn" data-cmd="trouble:decks:">Change</button></span>
        <span class="tr-ctl"><span id="tr-per">Period</span>
          <span class="seg" role="radiogroup" aria-labelledby="tr-per">${periods}</span></span>
        <label class="tr-ctl"><span>Group by</span><select class="sel tr-group">${groups}</select></label>
        <label class="tr-ctl"><span>Depth</span><input type="number" class="numin num tr-depth" min="1" max="6" step="1" value="${esc(c.depth)}"></label>
        ${custom}
      </div>`;
  }

  function summary(d) {
    const s = d.summary;
    const rng = d.range
      ? `<span class="tr-ref">your range ${pct(d.range[0])}–${pct(d.range[1])}</span>` : "";
    return `<p class="tr-summary">
      <span class="num">${desk.num(s.reviews)}</span> reviews ·
      <span class="num">${desk.num(s.cards)}</span> cards ·
      <span class="num">${desk.num(s.again)}</span> again ·
      miss rate <b class="num">${pct(s.rate, 1)}</b>
      <span class="tr-label">${esc(s.label)}</span>${rng}</p>`;
  }

  function topicsTable(d) {
    const topics = d.topics;
    if (!topics.length) {
      return topicsCol(d, `<p class="tr-empty">No reviews in this period for these decks.</p>`);
    }
    const hi = d.range ? d.range[1] : 0;
    const max = Math.max(hi, ...topics.map((t) => t.trouble)) * 1.08 || 1;
    const rows = topics.map((t, i) => {
      const sel = i === d.selected;
      const high = t.flag === "H";
      return `<tr class="tr-row${sel ? " is-sel" : ""}${high ? " is-h" : ""}" data-i="${i}" tabindex="0" aria-selected="${sel}"${high ? ' title="Above your range"' : ""}>
        <th scope="row" class="tr-topic">${topicName(t.name)}</th>
        <td class="r num">${desk.num(t.cards)}</td>
        <td class="r num">${desk.num(t.missed)}</td>
        <td class="r num tr-ratio">${desk.num(t.again)}<span class="tr-of">/${desk.num(t.reviews)}</span></td>
        <td class="r num tr-res">${pct(t.trouble)}</td>
        <td class="tr-bar">${desk.rangeBar(t.trouble, d.range, max)}</td>
      </tr>`;
    }).join("");
    const more = d.topic_count > topics.length
      ? `<p class="tr-foot">Showing the top <span class="num">${desk.num(topics.length)}</span> of <span class="num">${desk.num(d.topic_count)}</span> topics.</p>` : "";
    const rangeNote = d.range
      ? `<p class="tr-foot">The bar shows each topic's miss rate against your range (shaded): the middle 80% of topics with enough reviews. Topics above it are in red.</p>` : "";
    return topicsCol(d, `
      <table class="tr-topics" aria-label="Topics ranked by miss rate">
        <colgroup><col><col style="width:56px"><col style="width:60px"><col style="width:104px"><col style="width:72px"><col style="width:150px"></colgroup>
        <thead><tr>
          <th scope="col">Topic</th><th scope="col" class="r">Cards</th><th scope="col" class="r">Missed</th>
          <th scope="col" class="r">Again / reviews</th><th scope="col" class="r">Miss rate</th>
          <th scope="col" class="tr-barhead">vs. your range</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>${more}${rangeNote}`);
  }

  function topicsCol(d, inner) {
    const n = (d.topics || []).length;
    return `<div class="tr-col">
      <div class="tr-colhead"><div class="tr-coltitle"><h2>Topics</h2>
        <span class="tr-meta">${n ? "Click a topic to see its missed cards" : ""}</span></div></div>
      <div class="tr-pane">${inner}</div></div>`;
  }

  function drill(d) {
    const topic = d.selected != null ? d.topics[d.selected] : null;
    const title = topic ? topicName(topic.name) : "All topics";
    const cards = d.cards || [];
    const head = `
      <div class="tr-colhead">
        <div class="tr-coltitle"><h2>${title}</h2>
          <span class="tr-meta"><span class="num">${desk.num(d.card_total)}</span> missed card${d.card_total === 1 ? "" : "s"}${cards.length ? " · double-click a card to open it" : ""}</span></div>
        ${cards.length ? `<button type="button" class="btn" data-cmd="trouble:browse:">${desk.icon("list")}Open in Browser</button>` : ""}
      </div>`;
    if (!cards.length) {
      return `<div class="tr-col tr-drill">${head}<div class="tr-pane"><p class="tr-empty">No missed cards${topic ? " in this topic" : ""}.</p></div></div>`;
    }
    const rows = cards.map((c) => `<tr class="tr-card" data-cid="${esc(c.cid)}" tabindex="0">
        <td class="tr-text" title="${esc(c.text)}">${esc(c.text)}</td>
        <td class="r num tr-strong">${desk.num(c.again)}</td>
        <td class="r num">${desk.num(c.reviews)}</td>
        <td class="r num">${desk.num(c.lapses)}</td>
        <td class="r num">${esc(c.strength)}</td>
        <td class="tr-deck" title="${esc(c.deck)}">${esc(c.deck)}</td>
      </tr>`).join("");
    const foot = d.card_total > cards.length
      ? `<p class="tr-foot">Showing <span class="num">${desk.num(cards.length)}</span> of <span class="num">${desk.num(d.card_total)}</span> missed cards. Open in Browser shows them all.</p>` : "";
    return `<div class="tr-col tr-drill">${head}<div class="tr-pane">
      <table class="tr-cards">
        <colgroup><col><col style="width:52px"><col style="width:62px"><col style="width:56px"><col style="width:74px"><col style="width:130px"></colgroup>
        <thead><tr><th scope="col">Card</th><th scope="col" class="r">Again</th><th scope="col" class="r">Reviews</th>
          <th scope="col" class="r">Lapses</th><th scope="col" class="r">${d.fsrs ? "Difficulty" : "Ease"}</th><th scope="col">Deck</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>${foot}</div></div>`;
  }

  function body(d) {
    const hasData = Array.isArray(d.topics);
    if (d.error) {
      return `<div class="error tr-error" role="alert">${desk.icon("alert")}<h2>Nothing to show</h2><p>${esc(d.error)}</p></div>`;
    }
    if (!hasData) {
      return d.loading ? `<div class="loading" role="status">Reading your reviews…</div>` : "";
    }
    const updating = d.loading ? `<p class="tr-updating" role="status">Updating…</p>` : "";
    return `<div class="tr-sheet${d.loading ? " is-stale" : ""}">
      ${updating}<div class="tr-split">${topicsTable(d)}${drill(d)}</div></div>`;
  }

  // The top (controls and summary) can be folded away to make room for the
  // tables. Remembered in this browser only.
  const FOLD_KEY = "trouble.folded";
  let folded = false;
  try { folded = localStorage.getItem(FOLD_KEY) === "1"; } catch (e) { /* no storage */ }

  function brief(d, c) {
    const period = ((c.periods || []).find(([n]) => n === c.days) || [])[1] || "";
    const group = ((c.groups || []).find(([k]) => k === c.group) || [])[1] || "";
    const bits = [c.decks, period === "All" ? "all time" : period, group];
    if (d.summary) bits.push(`miss rate ${pct(d.summary.rate, 1)}`);
    return bits.filter(Boolean).map(esc).join(" · ");
  }

  function render(el, d) {
    d = d || {};
    const c = d.controls || {};
    const scroll = Array.from(el.querySelectorAll(".tr-pane"), (p) => p.scrollTop);
    const hasSummary = !d.error && Array.isArray(d.topics);
    el.innerHTML = `
      <div class="headrow tr-head">
        <h1><button type="button" class="tr-fold" aria-expanded="${!folded}" aria-controls="tr-top">
          <span class="tr-chev">${desk.icon("chevron")}</span>Trouble Spots</button></h1>
        <span class="tr-brief"${folded ? "" : " hidden"}>${brief(d, c)}</span>
        <div class="btnrow tr-actions">
          <button type="button" class="btn" data-cmd="trouble:refresh:">${desk.icon("refresh")}Refresh</button>
          <span class="tr-export"><span>Export</span>
            <button type="button" class="linkbtn" data-cmd="trouble:export:html">Web page</button>
            <button type="button" class="linkbtn" data-cmd="trouble:export:csv">CSV</button></span>
        </div>
      </div>
      <div id="tr-top" class="tr-top"${folded ? " hidden" : ""}>
        ${controls(c)}
        ${hasSummary ? summary(d) : ""}
      </div>
      ${body(d)}`;
    el.querySelectorAll(".tr-pane").forEach((p, i) => { if (scroll[i]) p.scrollTop = scroll[i]; });
    bind(el);
  }

  function setFolded(el, on) {
    folded = on;
    try { localStorage.setItem(FOLD_KEY, on ? "1" : "0"); } catch (e) { /* no storage */ }
    const top = el.querySelector(".tr-top"), b = el.querySelector(".tr-brief");
    const btn = el.querySelector(".tr-fold");
    if (top) top.hidden = on;
    if (b) b.hidden = !on;
    if (btn) btn.setAttribute("aria-expanded", String(!on));
  }

  function setDepth(input) {
    const v = Math.max(1, Math.min(6, parseInt(input.value, 10) || 1));
    const cur = (desk.state.trouble && desk.state.trouble.controls || {}).depth;
    if (v !== cur) desk.send("trouble", "set", { depth: v });
    else input.value = v;
  }

  let lastCustom = null;
  function sendCustom(input) {
    const cur = ((desk.state.trouble && desk.state.trouble.controls || {}).custom || "").trim();
    const v = input.value.trim();
    if (v === cur || v === lastCustom) return;
    lastCustom = v;
    desk.send("trouble", "set", { custom: v });
  }

  function bind(el) {
    if (el._trBound) return;
    el._trBound = true;
    el.addEventListener("click", (e) => {
      if (e.target.closest(".tr-fold")) {
        setFolded(el, !folded);
        return;
      }
      const day = e.target.closest("[data-days]");
      if (day && el.contains(day)) {
        if (day.getAttribute("aria-checked") !== "true") {
          desk.send("trouble", "set", { days: Number(day.dataset.days) });
        }
        return;
      }
      const row = e.target.closest(".tr-row");
      // The second click of a double-click would undo the selection.
      if (row && el.contains(row) && e.detail < 2) {
        markSelected(el, row.classList.contains("is-sel") ? null : row.dataset.i);
        desk.send("trouble", "select", row.dataset.i);
      }
    });
    el.addEventListener("dblclick", (e) => {
      const card = e.target.closest(".tr-card");
      if (card && el.contains(card)) {
        window.getSelection().removeAllRanges();
        desk.send("trouble", "card", card.dataset.cid);
      }
    });
    el.addEventListener("keydown", (e) => {
      const t = e.target;
      if (t.classList.contains("tr-row") && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        desk.send("trouble", "select", t.dataset.i);
      } else if (t.classList.contains("tr-card") && e.key === "Enter") {
        e.preventDefault();
        desk.send("trouble", "card", t.dataset.cid);
      } else if (t.classList.contains("tr-custom") && e.key === "Enter") {
        e.preventDefault();
        sendCustom(t);
      }
    });
    el.addEventListener("change", (e) => {
      const t = e.target;
      if (t.classList.contains("tr-group")) desk.send("trouble", "set", { group: t.value });
      else if (t.classList.contains("tr-depth")) setDepth(t);
    });
    el.addEventListener("focusout", (e) => {
      if (e.target.classList.contains("tr-custom")) sendCustom(e.target);
    });
  }

  // Picking a topic only changes the card list and the highlight, so redraw
  // just those instead of the whole table.
  function patch(el, d, part) {
    if (!("cards" in part) || d.loading || d.error || !Array.isArray(d.topics)) return false;
    const old = el.querySelector(".tr-drill");
    if (!old) return false;
    markSelected(el, d.selected);
    old.outerHTML = drill(d);
    return true;
  }

  function markSelected(el, i) {
    el.querySelectorAll(".tr-row").forEach((r) => {
      const sel = String(i) === r.dataset.i;
      r.classList.toggle("is-sel", sel);
      r.setAttribute("aria-selected", sel);
    });
  }

  desk.register("trouble", { render, patch });
})();
