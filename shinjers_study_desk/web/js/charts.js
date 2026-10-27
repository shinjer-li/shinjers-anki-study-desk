/* Shinjer's Study Desk: small SVG bar charts (Study Day forecast and pace).

   charts.bars(el, {
     values:    [n, ...]          main series, one bar per day
     stack:     [n, ...]          optional, drawn on top of values (e.g. Ahead deck)
     highlight: [n, ...]          optional subset of values drawn stronger (e.g. pullable)
     labels:    [{wd, date}, ...] one per bar
     range:     [lo, hi]          optional horizontal band ("your range")
     avg:       n                 optional dashed average line
     todayIndex: i                optional, that day's label is emphasised
                                  (labels are counted from it, else from the last bar)
     height:    px                default 150
   })

   Fills the width of `el` and redraws when `el` changes size. Colors come
   from classes in css/study_day.css, so a theme switch needs no redraw. */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const PAD = { top: 8, right: 4, bottom: 34, left: 34 };
  const live = new Map(); // el -> opts

  function niceStep(max, ticks) {
    const raw = max / ticks;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const n = raw / mag;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * mag;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  }

  function fmt(n) {
    return Math.round(n).toLocaleString("en-US");
  }

  function draw(el, o) {
    const width = el.clientWidth;
    if (!width) return; // hidden; the observer redraws once it has a size
    const height = o.height || 150;
    const vals = o.values || [];
    const stack = o.stack || [];
    const hi = o.highlight || [];
    const labels = o.labels || [];
    const n = vals.length;
    const total = (i) => (vals[i] || 0) + (stack[i] || 0);

    let top = 0;
    for (let i = 0; i < n; i++) top = Math.max(top, total(i));
    if (o.range) top = Math.max(top, o.range[1]);
    if (o.avg) top = Math.max(top, o.avg);
    top = Math.max(top, 4);
    const step = niceStep(top, 3);
    const yMax = Math.ceil(top / step) * step;

    const pw = width - PAD.left - PAD.right;
    const ph = height - PAD.top - PAD.bottom;
    const y = (v) => PAD.top + ph - (v / yMax) * ph;
    const slot = n ? pw / n : pw;
    const gap = Math.max(1, Math.min(slot * 0.28, 8));
    const bw = Math.max(1, slot - gap);

    const parts = [];
    const r = (v) => Math.round(v * 10) / 10;

    // Grid + ticks, one scale.
    for (let v = 0; v <= yMax + 1e-9; v += step) {
      const yy = r(y(v)) + 0.5;
      parts.push(`<line class="${v ? "c-grid" : "c-axis"}" x1="${PAD.left}" x2="${width - PAD.right}" y1="${yy}" y2="${yy}"/>`);
      parts.push(`<text class="c-tick" x="${PAD.left - 6}" y="${yy + 3.5}" text-anchor="end">${fmt(v)}</text>`);
    }

    // Range band, behind the bars.
    if (o.range) {
      const y1 = y(Math.min(o.range[1], yMax));
      const y0 = y(Math.max(o.range[0], 0));
      parts.push(`<rect class="c-band" x="${PAD.left}" width="${pw}" y="${r(y1)}" height="${r(Math.max(1, y0 - y1))}"/>`);
    }

    // Bars: values (with the highlighted subset at the bottom), stack on top.
    for (let i = 0; i < n; i++) {
      const x = r(PAD.left + i * slot + gap / 2);
      const v = vals[i] || 0;
      const h = Math.min(hi[i] || 0, v);
      const s = stack[i] || 0;
      const title = `<title>${labels[i] ? esc(labels[i].wd + " " + labels[i].date) + ": " : ""}${fmt(v)}${s ? " + " + fmt(s) : ""}</title>`;
      parts.push(`<g>${title}`);
      if (v > h) parts.push(`<rect class="c-val" x="${x}" width="${r(bw)}" y="${r(y(v))}" height="${r(y(h) - y(v))}"/>`);
      if (h) parts.push(`<rect class="c-hi" x="${x}" width="${r(bw)}" y="${r(y(h))}" height="${r(y(0) - y(h))}"/>`);
      if (s) parts.push(`<rect class="c-stack" x="${x}" width="${r(bw)}" y="${r(y(v + s))}" height="${r(y(v) - y(v + s))}"/>`);
      if (!v && !s) parts.push(`<rect class="c-zero" x="${x}" width="${r(bw)}" y="${r(y(0) - 2)}" height="2"/>`);
      parts.push(`</g>`);
    }

    // Average line.
    if (o.avg) {
      const ya = r(y(o.avg)) + 0.5;
      parts.push(`<line class="c-avg" x1="${PAD.left}" x2="${width - PAD.right}" y1="${ya}" y2="${ya}"/>`);
    }

    // Day labels: every Nth day, counted from today so today is always labelled.
    const twoLine = slot >= 38;
    const labelW = twoLine ? 36 : 46;
    const every = Math.max(1, Math.ceil(labelW / slot));
    const anchor = o.todayIndex != null ? o.todayIndex : n - 1;
    for (let i = 0; i < n; i++) {
      if (((i - anchor) % every + every) % every) continue;
      const lab = labels[i] && { wd: esc(labels[i].wd), date: esc(labels[i].date) };
      if (!lab) continue;
      const cx = r(PAD.left + i * slot + slot / 2);
      const cls = "c-day" + (i === o.todayIndex ? " today" : "");
      const base = height - PAD.bottom + 14;
      if (twoLine) {
        parts.push(`<text class="${cls}" x="${cx}" y="${base}" text-anchor="middle">${lab.wd}</text>`);
        parts.push(`<text class="${cls} sub" x="${cx}" y="${base + 13}" text-anchor="middle">${lab.date}</text>`);
      } else {
        // Keep the first and last label inside the plot.
        let anchorTxt = "middle", lx = cx;
        if (cx - labelW / 2 < PAD.left - 6) { anchorTxt = "start"; lx = r(PAD.left + i * slot); }
        if (cx + labelW / 2 > width) { anchorTxt = "end"; lx = r(PAD.left + (i + 1) * slot); }
        parts.push(`<text class="${cls}" x="${lx}" y="${base}" text-anchor="${anchorTxt}">${i === o.todayIndex ? "Today" : lab.date}</text>`);
      }
    }

    const svg = `<svg class="chart" xmlns="${NS}" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img">${parts.join("")}</svg>`;
    el.innerHTML = svg;
  }

  let ro = null;
  const lastW = new WeakMap();
  if (typeof ResizeObserver !== "undefined") {
    ro = new ResizeObserver((entries) => {
      for (const e of entries) {
        const el = e.target;
        if (!el.isConnected) { ro.unobserve(el); live.delete(el); continue; }
        const w = el.clientWidth;
        if (w && w !== lastW.get(el)) { lastW.set(el, w); draw(el, live.get(el)); }
      }
    });
  }
  window.addEventListener("resize", () => {
    for (const [el, o] of live) {
      if (!el.isConnected) { live.delete(el); if (ro) ro.unobserve(el); continue; }
      if (!ro) draw(el, o);
    }
  });

  function bars(el, opts) {
    if (!el) return;
    live.set(el, opts || {});
    draw(el, opts || {});
    lastW.set(el, el.clientWidth);
    if (ro) ro.observe(el);
  }

  window.charts = { bars };
})();
