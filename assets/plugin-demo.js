/* Static, browser-only samples. No provider calls, persistence, or email configuration. */
(() => {
  "use strict";
  const catalog = [
    { id: "weather", name: "Weather", category: "Local & daily", source: "Open-Meteo", url: "https://open-meteo.com/", description: "Conditions for your chosen coordinates.", sample: [{ type: "kv", rows: [["Location", "Borongan City"], ["Conditions", "Partly cloudy · 27°C"], ["Humidity", "80%"]] }] },
    { id: "air_quality", name: "Air quality", category: "Local & daily", source: "Open-Meteo", url: "https://open-meteo.com/", description: "Air quality index and fine particles.", sample: [{ type: "kv", rows: [["US AQI", "32 · Good"], ["PM2.5", "6 μg/m³"]] }] },
    { id: "uv_index", name: "UV index", category: "Local & daily", source: "Open-Meteo", url: "https://open-meteo.com/", description: "A quick view of UV exposure.", sample: [{ type: "kv", rows: [["UV index", "6.2 · High"]] }] },
    { id: "sunrise", name: "Sunrise & sunset", category: "Local & daily", source: "Open-Meteo", url: "https://open-meteo.com/", description: "Daylight times for your location.", sample: [{ type: "kv", rows: [["Sunrise", "05:30 · Asia/Manila"], ["Sunset", "17:45 · Asia/Manila"]] }] },
    { id: "public_holiday", name: "Public holiday", category: "Local & daily", source: "Nager.Date", url: "https://date.nager.at/", description: "Public holidays for your selected country.", sample: [{ type: "kv", rows: [["Country", "Philippines"], ["Today", "No public holiday in this sample"]] }] },
    { id: "quote", name: "Daily quote", category: "Quotes & learning", source: "ZenQuotes", url: "https://zenquotes.io/", description: "A short thought and its author.", sample: [{ type: "quote", text: "An illustrative thought appears here, with its author below.", author: "Sample attribution — not a real quotation" }] },
    { id: "quotable", name: "Quotable", category: "Quotes & learning", source: "Quotable", url: "https://github.com/lukePeavey/quotable", description: "An alternative quote provider.", note: "Known endpoint availability/TLS issues; this sample is not a health check.", sample: [{ type: "quote", text: "Another perspective, from your selected quote source.", author: "Sample attribution — not a real quotation" }] },
    { id: "stoic", name: "Stoic quote", category: "Quotes & learning", source: "Stoic Quotes", url: "https://stoic-quotes.com/", description: "A moment for philosophical reflection.", sample: [{ type: "quote", text: "A short passage from a Stoic author would appear here.", author: "Sample attribution — not a real quotation" }] },
    { id: "word_of_day", name: "Word of the day", category: "Quotes & learning", source: "Merriam-Webster", url: "https://www.merriam-webster.com/word-of-the-day", description: "A word, a definition, and a source link.", sample: [{ type: "kv", rows: [["Word", "Concise"], ["Definition", "Brief and clear; expressed in few words. (Illustrative definition.)"]] }] },
    { id: "bible_verse", name: "Bible verse", category: "Quotes & learning", source: "Bible API", url: "https://bible-api.com/", description: "A random verse from the World English Bible.", sample: [{ type: "kv", rows: [["Reference", "John 11:35"], ["Text", "Jesus wept."], ["Translation", "World English Bible · public domain"]] }] },
    { id: "headlines", name: "Headlines", category: "News & research", source: "BBC RSS", url: "https://www.bbc.com/news", description: "Three headlines with original article links.", sample: [{ type: "ranked", items: ["A world news headline appears here", "A science story worth opening", "One more story for your afternoon"] }] },
    { id: "hackernews", name: "Hacker News", category: "News & research", source: "Hacker News", url: "https://news.ycombinator.com/", description: "Technology stories and community discussion.", sample: [{ type: "ranked", items: ["A developer shares a useful open-source tool", "A discussion about building reliable software"] }] },
    { id: "reddit", name: "Reddit tech", category: "News & research", source: "Reddit", url: "https://www.reddit.com/r/technology/", description: "RSS stories from configurable subreddits.", sample: [{ type: "ranked", items: ["A technology discussion from your chosen community", "A programming project shared by its author"] }] },
    { id: "lobsters", name: "Lobsters", category: "News & research", source: "Lobsters", url: "https://lobste.rs/", description: "Computing links and technical discussions.", sample: [{ type: "ranked", items: ["Notes on a small programming language", "A closer look at database internals"] }] },
    { id: "devto", name: "Dev.to", category: "News & research", source: "DEV Community", url: "https://dev.to/", description: "Developer articles with topic tags.", sample: [{ type: "ranked", items: ["Testing a Python project with fixtures", "Making a small website keyboard accessible"] }] },
    { id: "arxiv", name: "arXiv AI papers", category: "News & research", source: "arXiv", url: "https://arxiv.org/list/cs.AI/recent", description: "AI papers, authors, and abstract excerpts.", sample: [{ type: "ranked", items: ["An illustrative paper about reasoning systems", "An illustrative study of model evaluation"] }] },
    { id: "openalex", name: "OpenAlex papers", category: "News & research", source: "OpenAlex", url: "https://openalex.org/", description: "Research discovery with authors and citations.", note: "API access and rate limits apply.", sample: [{ type: "ranked", items: ["A research result with author and citation metadata"] }] },
    { id: "papers_with_code", name: "Papers With Code", category: "News & research", source: "Papers With Code / Hugging Face", url: "https://huggingface.co/papers", description: "Paper summaries and related code repositories.", note: "Legacy source redirects to Hugging Face; integration review is pending.", sample: [{ type: "ranked", items: ["An illustrative paper paired with its code repository"] }] },
    { id: "semantic_scholar", name: "Semantic Scholar", category: "News & research", source: "Semantic Scholar", url: "https://www.semanticscholar.org/", description: "Research papers matched to a configured query.", note: "Public requests may be rate-limited; an optional API key is supported.", sample: [{ type: "ranked", items: ["An illustrative search result for artificial intelligence"] }] },
    { id: "github_trending", name: "GitHub Trending", category: "News & research", source: "GitHub", url: "https://github.com/trending", description: "Trending repositories by language and period.", sample: [{ type: "ranked", items: ["example/small-tool — a sample repository", "example/research-kit — another sample repository"] }] },
    { id: "product_hunt", name: "Product Hunt", category: "News & research", source: "Product Hunt", url: "https://www.producthunt.com/", description: "New products and short descriptions.", sample: [{ type: "ranked", items: ["Sample Workspace — a fictional planning app", "Sample Notebook — a fictional research tool"] }] },
    { id: "ai_pricing", name: "AI updates & pricing", category: "News & research", source: "Google News + OpenRouter", url: "https://openrouter.ai/models", description: "Two AI news feeds and a model-price watchlist.", note: "One plugin with three internal sections. Pricing normally runs Mondays; shown here as a sample.", sample: [{ type: "heading", text: "AI model advances" }, { type: "ranked", items: ["An illustrative model release with an original story link"] }, { type: "heading", text: "AI top stories" }, { type: "ranked", items: ["An illustrative story about AI research and adoption"] }, { type: "heading", text: "Model pricing · Monday sample" }, { type: "kv", rows: [["Example model (fictional)", "$2 input / $8 output per million tokens"], ["Example mix", "$4 for 1M input + 250K output"]] }] },
    { id: "crypto", name: "Crypto", category: "Markets", source: "Yahoo Finance via yfinance", url: "https://pypi.org/project/yfinance/", description: "BTC, ETH, and SOL with daily-bar timestamps.", note: "Changes compare daily closes, not rolling 24-hour returns. Illustrative prices only.", sample: [{ type: "kv", rows: [["BTC", "$67,890 · +2.3%"], ["ETH", "$3,450 · −0.8%"], ["SOL", "$145 · +1.2%"], ["Daily bar", "Illustrative timestamp · 00:00 UTC"]] }] },
    { id: "ph_stocks", name: "PH stocks", category: "Markets", source: "Twelve Data", url: "https://twelvedata.com/", description: "Optional PSE quotes with source timestamps.", note: "Requires TWELVEDATA_API_KEY and PSE entitlement. Demo toggle does not enable real stock access.", sample: [{ type: "kv", rows: [["BDO", "₱145.50 · +0.5%"], ["SM", "₱920.00 · −0.3%"], ["As of", "Illustrative prior trading day · Asia/Manila"]] }] },
    { id: "fx", name: "Exchange rate", category: "Markets", source: "Frankfurter", url: "https://frankfurter.dev/", description: "A configured currency pair, such as USD/PHP.", sample: [{ type: "kv", rows: [["USD / PHP", "58.25 · illustrative rate"]] }] },
    { id: "dad_joke", name: "Dad joke", category: "Puzzles & downtime", source: "icanhazdadjoke", url: "https://icanhazdadjoke.com/", description: "A short break from the serious sections.", sample: [{ type: "text", text: "A short setup and a groan-worthy punchline go here." }] },
    { id: "chess_puzzle", name: "Chess puzzle", category: "Puzzles & downtime", source: "Lichess", url: "https://lichess.org/training/daily", description: "A daily puzzle with a link to solve it.", sample: [{ type: "kv", rows: [["Rating", "1,500 · sample"], ["Theme", "Mate in two"]] }, { type: "text", text: "The real section includes the position (FEN) and a puzzle link. No solution is revealed here." }] },
    { id: "trivia", name: "Trivia", category: "Puzzles & downtime", source: "Open Trivia DB", url: "https://opentdb.com/", description: "A multiple-choice question and its answer.", sample: [{ type: "text", text: "Which planet is known as the Red Planet?" }, { type: "list", items: ["Venus", "Mars", "Jupiter", "Mercury"] }, { type: "text", text: "Answer: Mars · illustrative question" }] },
    { id: "recipe", name: "Recipe", category: "Puzzles & downtime", source: "TheMealDB", url: "https://www.themealdb.com/", description: "A recipe with ingredients and instructions.", sample: [{ type: "text", text: "Sample tomato toast" }, { type: "heading", text: "Ingredients" }, { type: "list", items: ["Bread", "Tomato", "Olive oil"] }, { type: "heading", text: "Instructions" }, { type: "text", text: "Toast the bread, add sliced tomato, and finish with olive oil. A short demonstration recipe." }] },
    { id: "cocktail", name: "Cocktail", category: "Puzzles & downtime", source: "TheCocktailDB", url: "https://www.thecocktaildb.com/", description: "A drink, ingredients, glassware, and instructions.", sample: [{ type: "text", text: "Sample citrus cooler · non-alcoholic" }, { type: "list", items: ["Soda water", "Lime", "Ice"] }, { type: "text", text: "Pour over ice and stir. Illustrative recipe; the live provider also returns alcoholic drinks." }] },
  ];
  const defaults = ["weather", "quote", "headlines", "ai_pricing", "crypto"];
  const initialState = () => ({ order: catalog.map(p => p.id), enabled: new Set(defaults) });
  // Target positions refer to the complete catalog, never just the filtered view.
  function move(order, id, target, after = false) {
    if (id === target || !order.includes(id) || !order.includes(target)) return [...order];
    const next = order.filter(key => key !== id);
    next.splice(next.indexOf(target) + Number(after), 0, id);
    return next;
  }
  if (typeof module !== "undefined") module.exports = { catalog, defaults, initialState, move };
  if (typeof document === "undefined") return;

  const root = document.querySelector("#plugin-builder");
  if (!root) return;
  const byId = new Map(catalog.map(p => [p.id, p]));
  let state = initialState();
  const list = root.querySelector("#plugin-list");
  const preview = root.querySelector("#demo-sections");
  const search = root.querySelector("#plugin-search");
  const category = root.querySelector("#plugin-category");
  const live = root.querySelector("#demo-announcement");
  const count = root.querySelector("#enabled-count");
  let drag = null;
  let announcementTimer;

  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function announce(message) {
    clearTimeout(announcementTimer);
    live.textContent = "";
    announcementTimer = setTimeout(() => { live.textContent = message; }, 30);
  }
  function focusControl(id, action) {
    list.querySelector(`[data-id="${id}"] [data-action="${action}"]`)?.focus({ preventScroll: true });
  }
  function renderSample(plugin) {
    const section = el("section", undefined, "demo-email-section");
    section.dataset.plugin = plugin.id;
    section.append(el("h4", plugin.name));
    for (const block of plugin.sample) {
      if (block.type === "kv") {
        const dl = el("dl", undefined, "demo-values");
        for (const [key, value] of block.rows) {
          const row = el("div");
          row.append(el("dt", key), el("dd", value));
          dl.append(row);
        }
        section.append(dl);
      } else if (block.type === "list" || block.type === "ranked") {
        const ul = el("ul");
        for (const item of block.items) ul.append(el("li", item));
        section.append(ul);
      } else if (block.type === "quote") {
        const quote = el("blockquote");
        quote.append(el("p", block.text), el("cite", block.author));
        section.append(quote);
      } else {
        section.append(el(block.type === "heading" ? "h5" : "p", block.text));
      }
    }
    const source = el("p", undefined, "demo-source");
    const link = el("a", plugin.source);
    link.href = plugin.url;
    source.append("Source website: ", link, " · sample content, not a live result");
    section.append(source);
    if (plugin.note) section.append(el("p", plugin.note, "demo-provider-note"));
    return section;
  }
  function renderPreview() {
    const selected = state.order.filter(id => state.enabled.has(id));
    count.textContent = `${selected.length} of ${catalog.length} enabled in demo`;
    preview.replaceChildren(...selected.map(id => renderSample(byId.get(id))));
    if (!selected.length) preview.append(el("p", "Your sample brief is empty. Enable a plugin to add its section here.", "demo-empty"));
  }
  function renderList() {
    const query = search.value.trim().toLowerCase();
    const visible = state.order.filter(id => {
      const p = byId.get(id);
      return (!category.value || category.value === p.category) &&
        `${p.name} ${p.id} ${p.description} ${p.source}`.toLowerCase().includes(query);
    });
    const rows = visible.map(id => {
      const p = byId.get(id);
      const position = state.order.indexOf(id);
      const li = el("li", undefined, "plugin-row");
      li.dataset.id = id;
      li.classList.toggle("is-enabled", state.enabled.has(id));
      const handle = el("button", "⠿", "drag-handle");
      handle.type = "button";
      handle.dataset.action = "drag";
      handle.setAttribute("aria-label", `Reorder ${p.name}`);
      handle.setAttribute("aria-describedby", "reorder-help");
      handle.title = "Drag to reorder, or use Arrow Up / Arrow Down";
      const info = el("div", undefined, "plugin-info");
      const label = el("label", undefined, "plugin-label");
      const toggle = el("input");
      toggle.type = "checkbox";
      toggle.checked = state.enabled.has(id);
      toggle.dataset.action = "toggle";
      toggle.setAttribute("aria-label", `Enable ${p.name} in demo`);
      label.append(toggle, el("span", p.name));
      info.append(label, el("p", p.description), el("small", `${position + 1}. ${p.category} · ${p.source}`));
      if (p.note) info.append(el("small", p.note, "plugin-caveat"));
      const buttons = el("div", undefined, "reorder-buttons");
      for (const [action, symbol, limit] of [["up", "↑", position === 0], ["down", "↓", position === state.order.length - 1]]) {
        const button = el("button", symbol);
        button.type = "button";
        button.dataset.action = action;
        button.setAttribute("aria-label", `Move ${p.name} ${action}`);
        // Remain focusable after reaching a boundary; event handlers enforce it.
        button.setAttribute("aria-disabled", String(limit));
        buttons.append(button);
      }
      li.append(handle, info, buttons);
      return li;
    });
    list.replaceChildren(...rows);
    root.querySelector("#filter-count").textContent = `${visible.length} plugins shown · positions refer to the full list`;
    root.querySelector("#no-plugins").hidden = visible.length > 0;
  }
  function refresh() { renderList(); renderPreview(); }
  function nudge(id, direction, focusAction) {
    const i = state.order.indexOf(id);
    const target = state.order[i + direction];
    if (!target) { announce(`${byId.get(id).name} is already at the ${direction < 0 ? "top" : "bottom"}.`); return; }
    state.order = move(state.order, id, target, direction > 0);
    refresh();
    focusControl(id, focusAction);
    announce(`${byId.get(id).name} moved to position ${state.order.indexOf(id) + 1} of ${catalog.length}.`);
  }
  list.addEventListener("change", event => {
    if (event.target.dataset.action !== "toggle") return;
    const row = event.target.closest("[data-id]");
    const id = row.dataset.id;
    if (event.target.checked) state.enabled.add(id); else state.enabled.delete(id);
    row.classList.toggle("is-enabled", event.target.checked);
    renderPreview();
    announce(`${byId.get(id).name} ${event.target.checked ? "enabled" : "disabled"} in the sample.`);
  });
  list.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button) return;
    const action = button.dataset.action;
    if (action === "up" || action === "down") nudge(button.closest("[data-id]").dataset.id, action === "up" ? -1 : 1, action);
  });
  list.addEventListener("keydown", event => {
    if (event.target.dataset.action !== "drag" || !["ArrowUp", "ArrowDown"].includes(event.key)) return;
    event.preventDefault();
    nudge(event.target.closest("[data-id]").dataset.id, event.key === "ArrowUp" ? -1 : 1, "drag");
  });

  // Pointer events support mouse, pen, and touch without an external drag library.
  function finishDrag(cancelled) {
    if (!drag) return;
    const { id, target, after, handle, pointerId, active } = drag;
    drag = null;
    if (handle.hasPointerCapture(pointerId)) handle.releasePointerCapture(pointerId);
    root.classList.remove("is-dragging");
    if (!cancelled && active && target && target !== id) {
      state.order = move(state.order, id, target, after);
      refresh();
      announce(`${byId.get(id).name} moved to position ${state.order.indexOf(id) + 1} of ${catalog.length}.`);
    } else {
      renderList();
      if (active) announce("Reorder cancelled. Order unchanged.");
    }
    focusControl(id, "drag");
  }
  list.addEventListener("pointerdown", event => {
    const handle = event.target.closest(".drag-handle");
    if (!handle || event.button !== 0 || drag) return;
    handle.focus({ preventScroll: true });
    drag = { id: handle.closest("[data-id]").dataset.id, handle, pointerId: event.pointerId, startY: event.clientY, active: false, target: null, after: false };
    handle.setPointerCapture(event.pointerId);
  });
  list.addEventListener("pointermove", event => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    if (!drag.active && Math.abs(event.clientY - drag.startY) < 5) return;
    drag.active = true;
    drag.handle.closest(".plugin-row").classList.add("is-picked");
    root.classList.add("is-dragging");
    const bounds = list.getBoundingClientRect();
    if (event.clientY < bounds.top + 40) list.scrollTop -= 18;
    if (event.clientY > bounds.bottom - 40) list.scrollTop += 18;
    const rows = [...list.querySelectorAll(".plugin-row")];
    rows.forEach(row => row.classList.remove("drop-before", "drop-after"));
    const inside = event.clientX >= bounds.left && event.clientX <= bounds.right && event.clientY >= bounds.top && event.clientY <= bounds.bottom;
    const target = inside && rows.find(row => {
      const rect = row.getBoundingClientRect();
      return event.clientY >= rect.top && event.clientY <= rect.bottom;
    });
    drag.target = target ? target.dataset.id : null;
    if (target && drag.target !== drag.id) {
      const rect = target.getBoundingClientRect();
      drag.after = event.clientY > rect.top + rect.height / 2;
      target.classList.add(drag.after ? "drop-after" : "drop-before");
    }
  });
  list.addEventListener("pointerup", event => { if (drag?.pointerId === event.pointerId) finishDrag(false); });
  list.addEventListener("pointercancel", () => finishDrag(true));
  list.addEventListener("lostpointercapture", () => { if (drag) finishDrag(true); });
  root.addEventListener("keydown", event => { if (event.key === "Escape" && drag) { event.preventDefault(); finishDrag(true); } });
  for (const group of new Set(catalog.map(p => p.category))) {
    const option = el("option", group); option.value = group; category.append(option);
  }
  search.addEventListener("input", renderList);
  category.addEventListener("change", renderList);
  root.querySelector("#demo-clear").addEventListener("click", () => {
    state.enabled.clear(); refresh(); announce("All sample plugins disabled. Your real email is unchanged.");
  });
  root.querySelector("#demo-reset").addEventListener("click", () => {
    state = initialState(); search.value = ""; category.value = ""; refresh(); list.scrollTop = 0;
    announce("Sample reset to five selected plugins and the original demo order.");
  });
  refresh();
  root.querySelector("#demo-interactive").hidden = false;
})();
