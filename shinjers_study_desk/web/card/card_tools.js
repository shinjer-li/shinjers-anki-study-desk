/* Shinjer's Study Desk helpers for the review screen, called from keyboard/card_tools.py.
   Works with the AnKing note types (cloze one-by-one, hint buttons) and falls back to
   Anki's own {{hint:}} links and plain cards. Every call returns something Python can
   turn into a tooltip. */
window.studyDeskCard = window.studyDeskCard || (function () {
  let hovered = null;
  // Copy image steps through the card's images; reset when the card changes.
  let imageList = [], imageIndex = -1;

  document.addEventListener("mouseover", (e) => {
    hovered = e.target && e.target.tagName === "IMG" ? e.target : null;
  });
  document.addEventListener("mouseleave", () => { hovered = null; });

  function shown(el) {
    if (!el.isConnected) return false;
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      if (getComputedStyle(n).display === "none") return false;
    }
    return true;
  }

  function click(el) {
    el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  }

  // ── cloze one-by-one ────────────────────────────────────────────────────────
  function revealNext() {
    if (!document.querySelector(".cloze-hidden")) return false;
    if (typeof window.revealNextCloze === "function") window.revealNextCloze();
    else click(document.getElementById("button-reveal-next"));
    return true;
  }

  function revealAll() {
    const btn = document.getElementById("button-toggle-all");
    if (typeof window.toggleAllCloze === "function" && btn) window.toggleAllCloze();
    else if (btn) click(btn);
    else return false;
    return true;
  }

  // ── hint buttons ────────────────────────────────────────────────────────────
  // A closed hint (AnKing's buttons and Anki's {{hint:}}) shows an <a class="hint">.
  function closedHints() {
    return Array.from(document.querySelectorAll("a.hint")).filter(shown);
  }

  function hintNext() {
    const a = closedHints()[0];
    if (!a) return false;
    click(a);
    return true;
  }

  function hintAll() {
    const closed = closedHints();
    if (closed.length) {
      closed.forEach(click);
      return "opened";
    }
    // Everything is open: close AnKing's buttons again, like the card's ' key.
    const open = Array.from(document.querySelectorAll(".hintBtn")).filter((b) => {
      const div = b.querySelector("div");
      return shown(b) && div && div.style.display !== "none";
    });
    if (!open.length || typeof window.toggleHintBtn !== "function") return "";
    open.forEach((b) => window.toggleHintBtn(b.id, true));
    return "closed";
  }

  // ── copy image ──────────────────────────────────────────────────────────────
  function sectionOf(img) {
    const btn = img.closest(".hintBtn");
    if (btn && btn.dataset.name) return btn.dataset.name;
    if (img.closest("#extra")) return "Extra";
    return "";
  }

  // The image under the mouse; otherwise step through the visible images (or
  // every image, if FA/Bootcamp etc. are still closed).
  function pickImage() {
    const all = Array.from(document.querySelectorAll("#qa img")).filter((i) => {
      const src = i.getAttribute("src") || "";
      return src && !/^_/.test(src.split("/").pop()); // skip note-type icons (_first-aid.icon.png)
    });
    let img = hovered && hovered.isConnected && all.includes(hovered) ? hovered : null;
    let list = all.filter(shown);
    if (!list.length) list = all;
    if (!img) {
      if (!list.length) return null;
      if (list.length !== imageList.length || list.some((x, i) => x !== imageList[i])) imageIndex = -1;
      imageList = list;
      imageIndex = (imageIndex + 1) % list.length;
      img = list[imageIndex];
    }
    img.classList.add("sd-copied");
    setTimeout(() => img.classList.remove("sd-copied"), 700);
    return {
      src: img.src,
      section: sectionOf(img),
      index: list.indexOf(img) + 1,
      total: list.length,
    };
  }

  // ── copy card text ──────────────────────────────────────────────────────────
  // The card's main text with every cloze filled in. AnKing cards: the Text field
  // only (no Extra, hints or tags). Other cards: the front side.
  const BLOCK = /^(DIV|P|BR|LI|UL|OL|TR|TABLE|H[1-6]|BLOCKQUOTE|PRE|HR)$/;

  function textOf(root) {
    let out = "";
    (function walk(node) {
      if (node.nodeType === 3) { out += node.nodeValue; return; }
      if (node.nodeType !== 1) return;
      const el = node;
      if (/^(SCRIPT|STYLE|BUTTON)$/.test(el.tagName)) return;
      if (el.classList.contains("cloze-replacer")) return;
      // Hidden one-by-one clozes still count; anything else hidden doesn't.
      if (!el.classList.contains("cloze-hidden") && !el.closest(".cloze-hidden") &&
          getComputedStyle(el).display === "none") return;
      if (el.tagName === "IMG") return;
      const block = BLOCK.test(el.tagName);
      if (block) out += "\n";
      if (el.tagName === "LI") out += "- ";
      el.childNodes.forEach(walk);
      if (block) out += "\n";
    })(root);
    return out
      .replace(/[ \t ]+/g, " ")
      .split("\n").map((l) => l.trim()).filter(Boolean).join("\n");
  }

  function cardText() {
    const qa = document.getElementById("qa") || document.body;
    const field = Array.from(qa.querySelectorAll("#text, .clozefield, .editcloze")).find(shown);
    if (field) return textOf(field);
    const hr = qa.querySelector("hr#answer");
    if (hr) {
      const front = document.createElement("div");
      for (let n = qa.firstChild; n && n !== hr; n = n.nextSibling) front.appendChild(n.cloneNode(true));
      // Measure styles on the real page, then throw the copy away.
      front.style.cssText = "position:absolute;left:-99999px;top:0";
      qa.appendChild(front);
      try { return textOf(front); } finally { front.remove(); }
    }
    return textOf(qa);
  }

  const style = document.createElement("style");
  style.textContent = "img.sd-copied{outline:3px solid #2e9d6a;outline-offset:2px;transition:outline-color .6s}";
  document.head.appendChild(style);

  return { revealNext, revealAll, hintNext, hintAll, pickImage, cardText };
})();
