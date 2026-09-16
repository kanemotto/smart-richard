/* SGX Swing Dashboard — presentation only. All analysis comes from scan.json. */

const STORAGE = {
  watchlist: "sgx-watchlist-v4",
  favourites: "sgx-favourites-v4",
  theme: "sgx-theme-v4"
};

const state = {
  scan: null,
  directory: [],
  watchlist: [],
  favourites: new Set(),
  filter: "ALL",
  query: "",
  editing: false
};

const $ = (selector) => document.querySelector(selector);
const elements = {
  grid: $("#stockGrid"),
  empty: $("#emptyState"),
  detailDialog: $("#detailDialog"),
  detailContent: $("#detailContent"),
  addDialog: $("#addDialog"),
  directoryList: $("#directoryList"),
  toast: $("#toast")
};

function safeRead(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function saveLocalChoices() {
  localStorage.setItem(STORAGE.watchlist, JSON.stringify(state.watchlist));
  localStorage.setItem(STORAGE.favourites, JSON.stringify([...state.favourites]));
}

function signalClass(signal = "") {
  if (signal === "BUY WATCH") return "buy";
  if (signal === "AVOID") return "avoid";
  return "wait";
}

function stars(count = 0) {
  return `${"★".repeat(count)}${"☆".repeat(Math.max(0, 5 - count))}`;
}

function formatPrice(stock) {
  if (!Number.isFinite(stock.price)) return "Price unavailable";
  const prefix = stock.currency === "USD" ? "US$" : "S$";
  const digits = stock.price < 1 ? 3 : 2;
  return `${prefix}${stock.price.toFixed(digits)}`;
}

function formatChange(stock) {
  if (!Number.isFinite(stock.changePercent)) return "";
  const sign = stock.changePercent > 0 ? "+" : "";
  const direction = stock.changePercent > 0 ? "up" : stock.changePercent < 0 ? "down" : "flat";
  return `<span class="${direction}">${sign}${stock.changePercent.toFixed(2)}%</span>`;
}

function currencyPrefix(stock) {
  return stock.currency === "USD" ? "US$" : "S$";
}

function formatPlanPrice(stock, value) {
  if (!value || value === "—") return "—";
  const prefix = currencyPrefix(stock);
  return String(value).split("–").map((part) => `${prefix}${part}`).join("–");
}

function sparkline(stock, className = "mini-chart") {
  const values = Array.isArray(stock.sparkline)
    ? stock.sparkline.map(Number).filter(Number.isFinite)
    : [];
  if (values.length < 2) return "";

  const width = 180;
  const height = 52;
  const padding = 3;
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum || 1;
  const points = values.map((value, index) => {
    const x = padding + (index / (values.length - 1)) * (width - (padding * 2));
    const y = padding + ((maximum - value) / range) * (height - (padding * 2));
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const rising = values[values.length - 1] >= values[0];
  const plottedPoints = points.split(" ");
  const lastPoint = plottedPoints[plottedPoints.length - 1].split(",");
  const trend = rising ? "up" : "down";

  return `<figure class="${className} ${trend}" aria-label="${stock.name} two-month daily price trend">
    <figcaption>2-month trend</figcaption>
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-hidden="true" preserveAspectRatio="none">
      <polyline points="${points}" fill="none" vector-effect="non-scaling-stroke"></polyline>
      <circle cx="${lastPoint[0]}" cy="${lastPoint[1]}" r="3"></circle>
    </svg>
  </figure>`;
}

function stockInfo(symbol) {
  return state.directory.find((item) => item.symbol === symbol) || {};
}

function scanInfo(symbol) {
  return state.scan.stocks.find((item) => item.symbol === symbol);
}

function watchlistDecisionCounts() {
  const stocks = state.watchlist.map(scanInfo).filter(Boolean);
  return {
    buy: stocks.filter((stock) => stock.signal === "BUY WATCH").length,
    wait: stocks.filter((stock) => stock.signal === "WAIT").length,
    avoid: stocks.filter((stock) => stock.signal === "AVOID").length
  };
}

function renderDecisionCounts() {
  const counts = watchlistDecisionCounts();
  $("#buyCount").textContent = counts.buy;
  $("#waitCount").textContent = counts.wait;
  $("#avoidCount").textContent = counts.avoid;
}

function toast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => elements.toast.classList.remove("show"), 1800);
}

function renderMarket() {
  const { updated, market, mode } = state.scan;
  $("#updatedLabel").textContent = `Last updated ${updated}`;
  $("#marketScore").textContent = Number(market.score).toFixed(1);
  const marketTone = market.signal === "Bullish" ? "buy" : market.signal === "Bearish" ? "avoid" : "wait";
  const marketSignal = $("#marketSignal");
  marketSignal.textContent = market.signal;
  marketSignal.className = `market-signal ${marketTone}`;
  renderDecisionCounts();

  const dataMode = $("#dataMode");
  dataMode.hidden = !mode;
  dataMode.textContent = mode || "";
  $("#dataSourceNote").textContent = state.scan.source
    ? `${state.scan.source} · prices may be delayed`
    : "Prices may be delayed";

  const orb = $("#signalOrb");
  orb.className = `signal-orb ${marketTone}`;
}

function visibleStocks() {
  const stocks = state.watchlist.map(scanInfo).filter(Boolean);
  return stocks.filter((stock) => {
    const info = stockInfo(stock.symbol);
    const haystack = `${stock.name} ${stock.symbol} ${info.sector || ""}`.toLowerCase();
    const matchesSearch = haystack.includes(state.query.toLowerCase());
    const matchesFilter = state.filter === "ALL"
      || (state.filter === "FAVOURITES" && state.favourites.has(stock.symbol))
      || stock.signal === state.filter;
    return matchesSearch && matchesFilter;
  });
}

function renderWatchlist() {
  const stocks = visibleStocks();
  renderDecisionCounts();
  elements.grid.classList.toggle("editing", state.editing);
  elements.grid.innerHTML = stocks.map((stock) => {
    const info = stockInfo(stock.symbol);
    const favourite = state.favourites.has(stock.symbol);
    return `
      <article class="stock-card" data-symbol="${stock.symbol}" tabindex="0" role="button" aria-label="Open ${stock.name} details">
        <div class="card-top">
          <span class="stars" aria-label="${stock.stars} out of 5 stars">${stars(stock.stars)}</span>
          <button class="favourite-button ${favourite ? "is-favourite" : ""}" type="button" data-action="favourite" aria-label="${favourite ? "Remove" : "Add"} ${stock.name} ${favourite ? "from" : "to"} favourites" aria-pressed="${favourite}">★</button>
        </div>
        <h3 class="stock-name">${stock.name}</h3>
        <p class="stock-meta">${stock.symbol} · ${info.sector || "SGX"}</p>
        <div class="card-market-row">
          <p class="stock-live">${formatPrice(stock)} ${formatChange(stock)}</p>
          ${sparkline(stock)}
        </div>
        ${stock.signal === "BUY WATCH" ? `<div class="entry-zone">
          <span>Suggested entry zone</span>
          <strong>${formatPlanPrice(stock, stock.buyZone)}</strong>
          <small>Rule-based · wait for this price range</small>
        </div>` : ""}
        <div class="card-bottom">
          <div class="stock-score">${stock.score}<small> /100</small></div>
          <span class="signal-badge ${signalClass(stock.signal)}">${stock.signal}</span>
        </div>
        <div class="edit-controls" aria-label="Reorder or remove ${stock.name}">
          <button class="edit-control" type="button" data-action="up" aria-label="Move ${stock.name} up">↑ Up</button>
          <button class="edit-control" type="button" data-action="down" aria-label="Move ${stock.name} down">↓ Down</button>
          <button class="edit-control delete" type="button" data-action="delete" aria-label="Remove ${stock.name}">×</button>
        </div>
      </article>`;
  }).join("");

  elements.empty.hidden = stocks.length > 0;
}

function openDetail(symbol) {
  const stock = scanInfo(symbol);
  if (!stock) return;
  const decision = stock.signal === "BUY WATCH" ? "YES" : stock.signal === "AVOID" ? "NO" : "WAIT";
  const details = [
    ["Suggested entry", formatPlanPrice(stock, stock.buyZone)],
    ["Stop", formatPlanPrice(stock, stock.stop)],
    ["Target", formatPlanPrice(stock, stock.target)],
    ["Risk reward", stock.rr]
  ];

  elements.detailContent.innerHTML = `
    <p class="detail-symbol">${stock.symbol}</p>
    <h2 class="detail-title">${stock.name}</h2>
    <p class="stock-live">Latest delayed price: ${formatPrice(stock)} ${formatChange(stock)}</p>
    ${sparkline(stock, "detail-chart")}
    <div class="detail-score-row">
      <div class="detail-score">${stock.score}<small> /100</small></div>
      <span class="signal-badge ${signalClass(stock.signal)}">${stock.signal}</span>
    </div>
    <div class="detail-decision ${signalClass(stock.signal)}">
      <span>Should I buy today?</span>
      <strong>${decision}</strong>
    </div>
    <section class="detail-block">
      <h3>Why?</h3>
      <ul class="reason-list">
        ${stock.bullets.map((bullet, index) => {
          const positive = stock.bulletSentiments ? stock.bulletSentiments[index] : index < 3;
          return `<li><span class="reason-icon ${positive ? "" : "negative"}" aria-hidden="true">${positive ? "✓" : "×"}</span><span>${bullet}</span></li>`;
        }).join("")}
      </ul>
    </section>
    <section class="detail-block">
      <h3>Trade plan</h3>
      <p class="trade-plan-note">${stock.signal === "BUY WATCH" ? "The suggested entry waits for a pullback toward the recent trend. Confirm the live price before acting." : "Entry prices appear only when this stock reaches BUY WATCH."}</p>
      <div class="trade-plan">
        ${details.map(([label, value]) => `<div class="plan-card"><span>${label}</span><strong>${value}</strong></div>`).join("")}
      </div>
    </section>
    <section class="detail-block">
      <h3>In simple English</h3>
      <p class="eli5">${stock.eli5}</p>
    </section>`;
  elements.detailDialog.showModal();
}

function moveStock(symbol, direction) {
  const index = state.watchlist.indexOf(symbol);
  const nextIndex = index + direction;
  if (index < 0 || nextIndex < 0 || nextIndex >= state.watchlist.length) return;
  [state.watchlist[index], state.watchlist[nextIndex]] = [state.watchlist[nextIndex], state.watchlist[index]];
  saveLocalChoices();
  renderWatchlist();
}

function deleteStock(symbol) {
  const name = scanInfo(symbol)?.name || symbol;
  state.watchlist = state.watchlist.filter((item) => item !== symbol);
  state.favourites.delete(symbol);
  saveLocalChoices();
  renderWatchlist();
  toast(`${name} removed`);
}

function toggleFavourite(symbol) {
  state.favourites.has(symbol) ? state.favourites.delete(symbol) : state.favourites.add(symbol);
  saveLocalChoices();
  renderWatchlist();
}

function renderDirectory(query = "") {
  const lowered = query.trim().toLowerCase();
  const items = state.directory.filter((stock) => `${stock.name} ${stock.symbol} ${stock.sector}`.toLowerCase().includes(lowered));
  elements.directoryList.innerHTML = items.map((stock) => {
    const added = state.watchlist.includes(stock.symbol);
    const hasScan = Boolean(scanInfo(stock.symbol));
    return `<div class="directory-item">
      <div><strong>${stock.name}</strong><small>${stock.symbol} · ${stock.sector} · ${stock.universe || "SGX"}</small></div>
      <button type="button" data-symbol="${stock.symbol}" ${added || !hasScan ? "disabled" : ""}>${added ? "Added" : hasScan ? "Add" : "No scan"}</button>
    </div>`;
  }).join("");
}

function setFilter(filter) {
  state.filter = filter;
  document.querySelectorAll(".filter-tab").forEach((button) => {
    const active = button.dataset.filter === filter;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  renderWatchlist();
  $("#watchlistHeading").scrollIntoView({ behavior: "smooth", block: "start" });
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(STORAGE.theme, theme);
  const dark = theme === "dark";
  $("#themeToggle").setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
  $("#themeToggle").setAttribute("title", dark ? "Light mode" : "Dark mode");
  $(".theme-icon").textContent = dark ? "☀" : "☾";
}

function registerWebMCPTools() {
  const context = document.modelContext;
  if (!context?.registerTool) return;

  const register = (tool) => {
    try {
      void Promise.resolve(context.registerTool(tool)).catch(() => {});
    } catch {
      // WebMCP is an optional enhancement; the visible dashboard remains primary.
    }
  };

  register({
    name: "get_market_decision",
    title: "Get market decision",
    description: "Read today's market score, overall signal, update time, and BUY WATCH, WAIT, and AVOID totals.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true, untrustedContentHint: false },
    execute() {
      return { updated: state.scan.updated, ...state.scan.market, ...watchlistDecisionCounts() };
    }
  });

  register({
    name: "set_watchlist_filter",
    title: "Filter watchlist",
    description: "Show all stocks, favourites, BUY WATCH, WAIT, or AVOID stocks in the visible watchlist.",
    inputSchema: {
      type: "object",
      properties: { filter: { type: "string", enum: ["ALL", "FAVOURITES", "BUY WATCH", "WAIT", "AVOID"] } },
      required: ["filter"],
      additionalProperties: false
    },
    annotations: { readOnlyHint: false, untrustedContentHint: false },
    execute(input) {
      if (!input || !["ALL", "FAVOURITES", "BUY WATCH", "WAIT", "AVOID"].includes(input.filter)) throw new Error("Choose a valid watchlist filter.");
      setFilter(input.filter);
      return { filter: state.filter, visibleStocks: visibleStocks().length };
    }
  });

  register({
    name: "set_stock_favourite",
    title: "Set stock favourite",
    description: "Add or remove one scanned stock from the locally saved favourites list.",
    inputSchema: {
      type: "object",
      properties: { symbol: { type: "string" }, favourite: { type: "boolean" } },
      required: ["symbol", "favourite"],
      additionalProperties: false
    },
    annotations: { readOnlyHint: false, untrustedContentHint: false },
    execute(input) {
      const symbol = String(input?.symbol || "").toUpperCase();
      if (!scanInfo(symbol)) throw new Error("That stock is not in today's scan.");
      input.favourite ? state.favourites.add(symbol) : state.favourites.delete(symbol);
      saveLocalChoices();
      renderWatchlist();
      return { symbol, favourite: state.favourites.has(symbol) };
    }
  });
}

function bindEvents() {
  $("#themeToggle").addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  $("#stockSearch").addEventListener("input", (event) => { state.query = event.target.value.trim(); renderWatchlist(); });
  $("#directorySearch").addEventListener("input", (event) => renderDirectory(event.target.value));
  $("#closeDetail").addEventListener("click", () => elements.detailDialog.close());
  $("#addStockButton").addEventListener("click", () => { renderDirectory(); elements.addDialog.showModal(); setTimeout(() => $("#directorySearch").focus(), 0); });
  $("#editListButton").addEventListener("click", () => {
    state.editing = !state.editing;
    $("#editListButton").textContent = state.editing ? "Done" : "Edit list";
    $("#editListButton").classList.toggle("active", state.editing);
    renderWatchlist();
  });

  document.querySelectorAll(".filter-tab, .count-card").forEach((button) => button.addEventListener("click", () => setFilter(button.dataset.filter)));

  elements.grid.addEventListener("click", (event) => {
    const card = event.target.closest(".stock-card");
    if (!card) return;
    const action = event.target.closest("[data-action]")?.dataset.action;
    if (action) {
      event.stopPropagation();
      if (action === "favourite") toggleFavourite(card.dataset.symbol);
      if (action === "up") moveStock(card.dataset.symbol, -1);
      if (action === "down") moveStock(card.dataset.symbol, 1);
      if (action === "delete") deleteStock(card.dataset.symbol);
      return;
    }
    if (!state.editing) openDetail(card.dataset.symbol);
  });

  elements.grid.addEventListener("keydown", (event) => {
    if ((event.key === "Enter" || event.key === " ") && event.target.classList.contains("stock-card") && !state.editing) {
      event.preventDefault();
      openDetail(event.target.dataset.symbol);
    }
  });

  elements.directoryList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-symbol]");
    if (!button || button.disabled) return;
    state.watchlist.push(button.dataset.symbol);
    saveLocalChoices();
    renderDirectory($("#directorySearch").value);
    renderWatchlist();
    toast("Stock added");
  });

  [elements.detailDialog, elements.addDialog].forEach((dialog) => {
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  });
}

async function loadData() {
  const [scanResponse, watchlistResponse, directoryResponse] = await Promise.all([
    fetch("scan.json?v=5.2.0", { cache: "no-store" }),
    fetch("watchlist.json?v=5.2.0", { cache: "no-store" }),
    fetch("stocks.json?v=5.2.0", { cache: "no-store" })
  ]);
  if (!scanResponse.ok || !watchlistResponse.ok || !directoryResponse.ok) throw new Error("Data could not be loaded");

  state.scan = await scanResponse.json();
  state.directory = await directoryResponse.json();
  const defaultWatchlist = await watchlistResponse.json();
  state.watchlist = safeRead(STORAGE.watchlist, defaultWatchlist);
  state.favourites = new Set(safeRead(STORAGE.favourites, []));
}

async function refreshScan() {
  try {
    const response = await fetch(`scan.json?refresh=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return;
    const updatedScan = await response.json();
    if (updatedScan.updated !== state.scan.updated) {
      state.scan = updatedScan;
      renderMarket();
      renderWatchlist();
      toast("Today’s scan was updated");
    }
  } catch {
    // Keep the last working scan visible if a refresh is unavailable.
  }
}

async function start() {
  const savedTheme = localStorage.getItem(STORAGE.theme);
  const preferredTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  applyTheme(savedTheme || preferredTheme);
  bindEvents();
  try {
    await loadData();
    renderMarket();
    renderWatchlist();
    registerWebMCPTools();
    setInterval(refreshScan, 60000);
  } catch (error) {
    elements.grid.innerHTML = `<div class="empty-state"><h3>Dashboard data did not load</h3><p>Close this window, then double-click START.command again.</p></div>`;
  }
}

start();
