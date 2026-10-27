/* About tab: what the add-on does, a quick start, and links for help. */
(function () {
  const TABS = [
    ["study_day", "calendar", "Study Day",
      "Today's reviews and new cards next to your usual range, flagged H or L when they're outside it. " +
      "Study ahead pulls upcoming reviews into a temporary deck; Freeze pauses reviews for a break " +
      "so they don't pile up. Also a forecast, your pace, and a history you can undo."],
    ["trouble", "target", "Trouble Spots",
      "Topics ranked by how often you miss them, grouped by First Aid section, Pathoma chapter, " +
      "Boards & Beyond or Sketchy video, organ system, subdeck or any tag. Click a topic to see its cards, " +
      "open them in the Browser, or export a study sheet. It never changes your cards."],
    ["keyboard", "keyboard", "Keyboard",
      "Every shortcut on the review screen, the deck overview and everywhere else. Click an action " +
      "and press a key. If the key is taken, swap it, give the old action a spare key, or unbind it. " +
      "Smart undo flips back to the question instead of undoing a review."],
    ["settings", "gear", "Settings",
      "Light, dark or Auto (follows Anki's night mode), eleven color themes, the window, the top-bar link, " +
      "and each tab's own options."],
  ];

  const STEPS = [
    ["Choose your decks.",
      "Study Day only counts the decks you pick. Leave it on all decks, or choose your main deck.",
      ["settings", "Open Settings"]],
    ["Check Study Day before you review.",
      "See what's left today and how long it should take. If you have time to spare, Study ahead " +
      "pulls tomorrow's reviews in now. Going away? Freeze pauses reviews until you're back.",
      ["study_day", "Open Study Day"]],
    ["Look at Trouble Spots once a week.",
      "Pick a grouping (First Aid sections is a good start) and a period. The topics at the top " +
      "are the ones to reread or rewatch.",
      ["trouble", "Open Trouble Spots"]],
  ];

  const WHERE = [
    ["The <b>Shinjer's Study Desk</b> link in Anki's top bar, next to Decks, Add and Browse."],
    ["The status bar on the <b>Decks</b> screen. Click the logo or <b>Open</b>."],
    ["<b>Tools › Shinjer's Study Desk…</b>"],
    ["<b>Tools › Add-ons › Shinjer's Study Desk › Config</b> opens Settings."],
  ];

  const FAQ = [
    ["Can I undo things?",
      "Yes. Study ahead, Freeze and catch-up all show in the Study Day history with an Undo button, " +
      "and Anki's own Edit › Undo works too. The two stay in step."],
    ["Does it need AnKing tags?",
      "Study Day and Keyboard work with any deck. Trouble Spots is built around AnKing-style tags, " +
      "but it can also group by subdeck or by any tag you type."],
    ["Does it send my data anywhere?",
      "No. Everything happens on your computer. The add-on never connects to the internet; the links " +
      "on this page just open your browser."],
    ["Do settings follow my profile?",
      "Study Day and Trouble Spots settings are saved in your collection, so they sync with it. " +
      "Look, window and keyboard settings are saved with the add-on and apply to every profile."],
  ];

  const LINKS = {
    github: ["external", "Source & guide on GitHub"],
    issues: ["bug", "Report a problem"],
    ankiweb: ["star", "Rate it on AnkiWeb"],
    changes: ["list", "What's new"],
  };

  function logo() {
    const img = document.querySelector(".brand-logo");
    return img ? `<img class="ab-logo" src="${desk.esc(img.getAttribute("src"))}" alt="">` : "";
  }

  function render(el, d) {
    d = d || {};
    const links = (d.links || []).filter((k) => LINKS[k]);
    const linkBtns = links.map((k, i) =>
      `<button type="button" class="btn${i === 0 ? " primary" : ""}" data-cmd="about:link:${k}">` +
      `${desk.icon(LINKS[k][0])}${desk.esc(LINKS[k][1])}</button>`).join("");

    const steps = STEPS.map(([title, body, [tab, label]], i) =>
      `<li class="ab-step"><span class="ab-n" aria-hidden="true">${i + 1}</span><div>` +
      `<h3>${desk.esc(title)}</h3><p>${desk.esc(body)}</p>` +
      `<button type="button" class="linkbtn" data-open="${tab}">${desk.esc(label)}</button></div></li>`).join("");

    const tabs = TABS.map(([id, icon, title, body]) =>
      `<button type="button" class="ab-tab" data-open="${id}">` +
      `<span class="ab-tab-head"><span class="ab-ico">${desk.icon(icon)}</span><h3>${desk.esc(title)}</h3>` +
      `<span class="ab-go">${desk.icon("chevron")}</span></span>` +
      `<p>${desk.esc(body)}</p></button>`).join("");

    const install = d.ankiweb_id
      ? `<p class="hint ab-code">Share it: in Anki, <b>Tools › Add-ons › Get Add-ons…</b> and enter ` +
        `<span class="num">${desk.esc(d.ankiweb_id)}</span>.</p>`
      : "";

    el.innerHTML =
      `<div class="ab-wrap">` +
      `<header class="ab-hero">${logo()}<div class="ab-title">` +
      `<h1>Shinjer's Study Desk</h1>` +
      `<p class="meta">Version ${desk.esc(d.version || "")} · by Shinjer Li · free and open source (MIT)</p>` +
      `<p class="lede">One window for your study day, the topics you miss most, and your keyboard shortcuts. ` +
      `Built for Step 1 students using AnKing-style decks, and it works with any deck.</p>` +
      `</div></header>` +
      (linkBtns ? `<div class="btnrow ab-links">${linkBtns}</div>` : "") + install +

      `<section class="ab-section"><h2>Quick start</h2><ol class="ab-steps sheet">${steps}</ol></section>` +

      `<section class="ab-section"><h2>The tabs</h2><div class="ab-tabs">${tabs}</div></section>` +

      `<div class="ab-cols">` +
      `<section class="ab-section"><h2>Opening this window</h2><ul class="ab-list sheet">` +
      WHERE.map(([html]) => `<li>${html}</li>`).join("") + `</ul></section>` +
      `<section class="ab-section"><h2>Good to know</h2><dl class="ab-faq sheet">` +
      FAQ.map(([q, a]) => `<dt>${desk.esc(q)}</dt><dd>${desk.esc(a)}</dd>`).join("") + `</dl></section>` +
      `</div>` +

      `<p class="hint ab-foot">Found a bug or have an idea? ` +
      (links.includes("issues")
        ? `<button type="button" class="linkbtn" data-cmd="about:link:issues">Open an issue on GitHub</button>. `
        : "") +
      `Please include your Anki version (Help › About).</p>` +
      `</div>`;
    bind(el);
  }

  function bind(el) {
    if (el.dataset.bound) return;
    el.dataset.bound = "1";
    el.addEventListener("click", (e) => {
      const b = e.target.closest("[data-open]");
      if (b && el.contains(b)) desk.open(b.dataset.open);
    });
  }

  desk.register("about", { render });
})();
