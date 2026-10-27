/* Keyboard: every shortcut per screen, with a "press a key" editor and an
   inline conflict choice. Data shape: keyboard/tab.py data(). */
(function () {
  "use strict";

  const esc = (s) => desk.esc(s == null ? "" : String(s));

  // Survive re-renders.
  let scope = null;          // selected scope id
  let filter = "";
  let filterFocus = null;    // [selStart, selEnd] when the filter had focus
  let capture = null;        // {scope, name} while waiting for a key
  let conflict = null;       // {scope, name, key, holder, holderLabel, resolve}
  let confirmReset = false;
  let lastEl = null;

  const POLICY_HINTS = {
    swap: (who, old) => old ? `${who} gets ${kbd(old)}` : `${who} gets this row's old key`,
    spare: (who) => `${who} gets an unused key`,
    delete: (who) => `${who} has no key`,
  };

  const kbd = (k) => `<kbd>${esc(k)}</kbd>`;
  const same = (a, b) => String(a).toLowerCase() === String(b).toLowerCase();

  function rerender() {
    if (lastEl) render(lastEl, desk.state.keyboard);
  }

  function currentScope(data) {
    const scopes = data.scopes || [];
    return scopes.find((s) => s.id === scope) || scopes[0] || null;
  }

  function allRows(sc) {
    return sc.groups.flatMap((g) => g.rows);
  }

  function matches(row, q) {
    if (!q) return true;
    if (row.label.toLowerCase().includes(q)) return true;
    return row.keys.some((k) => k.toLowerCase().includes(q));
  }

  function conflictPanel(data) {
    const c = conflict;
    const oldKey = (() => {
      const row = allRows(currentScope(data)).find((r) => r.name === c.name);
      return row ? row.keys.find((k) => !same(k, c.key)) : null;
    })();
    const who = esc(c.holderLabel);
    const choices = (data.policies || []).map(([p, label]) => {
      const on = p === c.resolve;
      const hint = POLICY_HINTS[p] ? POLICY_HINTS[p](who, oldKey) : "";
      return `<label class="kb-choice${on ? " on" : ""}">
        <input type="radio" name="kb-resolve" value="${esc(p)}"${on ? " checked" : ""}>
        <span><b>${esc(label)}</b>${hint ? `<small>${hint}</small>` : ""}</span>
        ${p === data.policy ? `<em>Default</em>` : ""}</label>`;
    }).join("");
    return `<tr class="kb-conflict"><td colspan="4"><div class="kb-cpanel" role="group" aria-label="Resolve key conflict">
      <p class="kb-cmsg"><span class="kb-crit">${desk.icon("alert")}</span>${kbd(c.key)} is used by <b>${who}</b>. What should happen to it?</p>
      <div class="kb-choices" role="radiogroup">${choices}</div>
      <div class="kb-capply">
        <button type="button" class="btn primary" data-act="apply">Apply</button>
        <button type="button" class="btn" data-act="cancel">Cancel</button>
      </div></div></td></tr>`;
  }

  function rowHtml(sc, row, data) {
    const editing = capture && capture.scope === sc.id && capture.name === row.name;
    const clashing = conflict && conflict.scope === sc.id && conflict.name === row.name;
    const holder = conflict && conflict.scope === sc.id && conflict.holder === row.name;
    let keys;
    if (clashing) {
      keys = `<kbd class="pending">${esc(conflict.key)}</kbd>`;
    } else if (editing) {
      keys = `<span class="kb-listen">Press a key… <span>Esc to cancel</span></span>`;
    } else if (row.keys.length) {
      keys = row.keys.map((k) => `<kbd${holder && same(k, conflict.key) ? ` class="hit"` : ""}>${esc(k)}</kbd>`).join("");
    } else {
      keys = `<span class="kb-none">None</span>`;
    }
    const def = row.changed && !editing && !clashing
      ? `<span class="kb-def">default: ${row.defaults.length ? row.defaults.map(esc).join(", ") : "none"}</span>` : "";
    const busy = editing || clashing;
    const actions = busy ? "" : `
      ${row.changed ? `<button type="button" class="linkbtn muted" data-act="reset">Reset</button>` : ""}
      ${row.keys.length ? `<button type="button" class="linkbtn muted" data-act="clear">Clear</button>` : ""}
      <button type="button" class="linkbtn" data-act="change">Change</button>`;
    const tr = `<tr class="kb-row${busy ? " editing" : ""}${row.changed ? " changed" : ""}" data-name="${esc(row.name)}">
      <th scope="row"><span class="kb-label">${esc(row.label)}</span>${row.smart ? `<span class="kb-badge" title="With the answer showing, undo flips back to the question">smart</span>` : ""}
        ${row.note ? `<span class="kb-note">${esc(row.note)}</span>` : ""}</th>
      <td class="kb-keys">${keys}</td>
      <td class="kb-defc">${def}</td>
      <td class="kb-acts">${actions}</td></tr>`;
    return clashing ? tr + conflictPanel(data) : tr;
  }

  function render(el, data) {
    lastEl = el;
    data = data || {};
    const sc = currentScope(data);
    if (!sc) { el.innerHTML = `<h1>Keyboard</h1>`; return; }
    scope = sc.id;
    if (capture && capture.scope !== sc.id) capture = null;
    if (conflict && conflict.scope !== sc.id) conflict = null;

    const seg = data.scopes.map((s) =>
      `<button type="button" role="radio" aria-checked="${s.id === sc.id}" data-scope="${esc(s.id)}">${esc(s.title)}</button>`
    ).join("");
    const errors = (sc.errors || []).length
      ? `<div class="kb-errors" role="alert"><b>Some shortcuts couldn't be applied</b><ul>${sc.errors.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div>` : "";
    const reset = confirmReset
      ? `<span class="kb-confirm">Reset every shortcut on every screen to Anki's defaults?
          <button type="button" class="btn xs primary" data-act="reset-all-yes">Reset all</button>
          <button type="button" class="btn xs" data-act="reset-all-no">Cancel</button></span>`
      : `<button type="button" class="linkbtn muted" data-act="reset-all">Reset all</button>`;

    const q = filter.trim().toLowerCase();
    const groups = sc.groups.map((g) => {
      const rows = g.rows.filter((r) => matches(r, q)
        || (conflict && conflict.name === r.name) || (capture && capture.name === r.name));
      if (!rows.length) return "";
      return `<section class="kb-group"><h2>${esc(g.title)}</h2>
        <table class="kb-keys-t"><colgroup><col style="width:34%"><col><col style="width:22%"><col class="kb-actcol"></colgroup>
        <tbody>${rows.map((r) => rowHtml(sc, r, data)).join("")}</tbody></table></section>`;
    }).join("");

    el.innerHTML = `
      <div class="headrow kb-head">
        <h1>Keyboard</h1>
        <span class="seg" role="radiogroup" aria-label="Screen">${seg}</span>
      </div>
      <p class="kb-hint">${esc(sc.hint)}</p>
      <div class="kb-tools">
        <label class="kb-filter">${desk.icon("search")}<input type="search" placeholder="Filter by action or key" value="${esc(filter)}" spellcheck="false" aria-label="Filter shortcuts"></label>
        <span class="kb-reset">${reset}</span>
      </div>
      ${errors}
      ${groups || `<p class="kb-empty">No shortcuts match “${esc(filter)}”.</p>`}`;

    if (filterFocus) {
      const inp = el.querySelector(".kb-filter input");
      inp.focus();
      try { inp.setSelectionRange(filterFocus[0], filterFocus[1]); } catch (e) { /* ignore */ }
    }
    bind(el);
  }

  // ── key capture ──────────────────────────────────────────────────────────

  const NAMES = {
    ArrowLeft: "Left", ArrowRight: "Right", ArrowUp: "Up", ArrowDown: "Down",
    Enter: "Return", " ": "Space", PageUp: "PgUp", PageDown: "PgDown",
    Insert: "Ins", Delete: "Del", Backspace: "Backspace", Tab: "Tab",
    Home: "Home", End: "End",
  };
  const MODIFIERS = new Set(["Control", "Alt", "Shift", "Meta", "AltGraph", "OS", "CapsLock", "NumLock", "Fn"]);

  // KeyboardEvent → Qt key text ("Ctrl+Shift+A", "Space", "?"), or null.
  function qtKey(e) {
    if (MODIFIERS.has(e.key)) return null;
    const strong = e.ctrlKey || e.altKey || e.metaKey;
    let base = null;
    let printable = false;
    if (NAMES[e.key]) base = NAMES[e.key];
    else if (/^F([1-9]|1[0-2])$/.test(e.key)) base = e.key;
    else if (strong && /^Key[A-Z]$/.test(e.code)) base = e.code.slice(3);
    else if (strong && /^(Digit|Numpad)\d$/.test(e.code)) base = e.code.slice(-1);
    else if (/^[a-z]$/i.test(e.key)) base = e.key.toUpperCase();
    else if (e.key.length === 1) { base = e.key; printable = true; }
    if (!base) return null;
    const mods = [];
    if (e.ctrlKey) mods.push("Ctrl");
    if (e.altKey) mods.push("Alt");
    // Shift is already folded into a symbol like "!" unless Ctrl/Alt/Meta are down.
    if (e.shiftKey && !(printable && !strong)) mods.push("Shift");
    if (e.metaKey) mods.push("Meta");
    return [...mods, base].join("+");
  }

  function onKey(e) {
    if (!capture && !conflict) return;
    if (!lastEl || !lastEl.isConnected || lastEl.offsetParent === null) return;
    if (conflict) {
      if (e.key === "Escape") { e.preventDefault(); conflict = null; rerender(); }
      return;
    }
    e.preventDefault();
    e.stopPropagation();
    if (e.key === "Escape") { capture = null; rerender(); return; }
    const key = qtKey(e);
    if (!key) return;
    const data = desk.state.keyboard;
    const sc = currentScope(data);
    const target = capture;
    capture = null;
    const rows = allRows(sc);
    const me = rows.find((r) => r.name === target.name);
    if (me && me.keys.some((k) => same(k, key))) { rerender(); return; }
    const holder = rows.find((r) => r.name !== target.name && r.keys.some((k) => same(k, key)));
    if (holder) {
      conflict = { scope: target.scope, name: target.name, key, holder: holder.name,
                   holderLabel: holder.label, resolve: data.policy };
      rerender();
      const apply = lastEl.querySelector('[data-act="apply"]');
      if (apply) apply.focus();
    } else {
      rerender();
      desk.send("keyboard", "bind", { scope: target.scope, name: target.name, key });
    }
  }

  function bind(el) {
    if (el._kbBound) return;
    el._kbBound = true;
    document.addEventListener("keydown", onKey, true);

    el.addEventListener("click", (e) => {
      const segBtn = e.target.closest("[data-scope]");
      if (segBtn) {
        if (segBtn.dataset.scope !== scope) {
          scope = segBtn.dataset.scope;
          capture = conflict = null;
          rerender();
        }
        return;
      }
      const btn = e.target.closest("[data-act]");
      if (!btn) return;
      const act = btn.dataset.act;
      const tr = btn.closest("[data-name]");
      const name = tr && tr.dataset.name;
      if (act === "change") {
        capture = { scope, name };
        conflict = null;
        filterFocus = null;
        rerender();
      } else if (act === "clear") {
        desk.send("keyboard", "clear", { scope, name });
      } else if (act === "reset") {
        desk.send("keyboard", "reset", { scope, name });
      } else if (act === "apply" && conflict) {
        const c = conflict;
        conflict = null;
        rerender();
        desk.send("keyboard", "bind", { scope: c.scope, name: c.name, key: c.key, resolve: c.resolve });
      } else if (act === "cancel") {
        conflict = null;
        rerender();
      } else if (act === "reset-all") {
        confirmReset = true;
        rerender();
        const yes = el.querySelector('[data-act="reset-all-no"]');
        if (yes) yes.focus();
      } else if (act === "reset-all-yes") {
        confirmReset = false;
        desk.send("keyboard", "reset_all", "");
      } else if (act === "reset-all-no") {
        confirmReset = false;
        rerender();
      }
    });

    el.addEventListener("change", (e) => {
      if (e.target.name === "kb-resolve" && conflict) {
        conflict.resolve = e.target.value;
        el.querySelectorAll(".kb-choice").forEach((c) =>
          c.classList.toggle("on", c.querySelector("input").checked));
      }
    });

    el.addEventListener("input", (e) => {
      if (!e.target.closest(".kb-filter")) return;
      filter = e.target.value;
      filterFocus = [e.target.selectionStart, e.target.selectionEnd];
      rerender();
    });
    el.addEventListener("focusin", (e) => {
      if (e.target.closest(".kb-filter")) filterFocus = [e.target.selectionStart, e.target.selectionEnd];
    });
    el.addEventListener("focusout", (e) => {
      if (!e.target.closest(".kb-filter")) return;
      // A re-render detaches the input; only a real blur clears the memory.
      setTimeout(() => {
        const inp = el.querySelector(".kb-filter input");
        if (!inp || document.activeElement !== inp) filterFocus = null;
      }, 0);
    });
    el.addEventListener("keyup", (e) => {
      const t = e.target;
      if (t.closest && t.closest(".kb-filter")) filterFocus = [t.selectionStart, t.selectionEnd];
    });
  }

  desk.register("keyboard", { render });
})();
