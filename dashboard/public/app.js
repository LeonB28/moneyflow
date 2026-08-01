/* Moneyflow Dashboard — client logic (no framework, ECharts). */

const CURRENCY = "€"; // amount values come from the REST API as plain numbers

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

const fmt = new Intl.NumberFormat("en-GB", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const money = (n) => `${CURRENCY}${fmt.format(Math.abs(n))}`;
const signedMoney = (n) => `${n < 0 ? "-" : "+"}${money(n)}`;

/* ---------------------------------- state ---------------------------------- */

const state = {
  account: null,
  categories: {}, // id -> { name, group }
  transactions: [],
  start: null, // "YYYY-MM-DD"
  end: null,
  selectedCategory: "__all__",
  barChart: null,
  pieChart: null,
  catChart: null,
  catCompare: null,
  incomePie: null,
  outcomePie: null,
  incomePieSlices: [],
  outcomePieSlices: [],
  activeTab: "overview",
};

/* ---------------------------------- api ------------------------------------ */

async function api(path) {
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json();
}

function showNotice(message) {
  const n = $("notice");
  n.textContent = message;
  n.classList.remove("hidden");
}

function clearNotice() {
  $("notice").classList.add("hidden");
}

async function refreshData() {
  const btn = $("refresh-btn");
  btn.disabled = true;
  btn.classList.add("loading");
  try {
    const res = await fetch("/api/refresh", { method: "POST" });
    if (!res.ok) throw new Error(`refresh -> ${res.status}`);
    const info = await res.json();

    const [account, cats, tx] = await Promise.all([
      api("/account"),
      api("/categories"),
      api("/transactions?limit=1000"),
    ]);
    state.account = account;
    state.categories = cats.categories;
    state.transactions = tx.results;

    buildCategorySelect();
    syncDateInputs();
    update();

    let msg = `Refreshed ${info.transaction_count} transactions (${state.transactions.length} shown here).`;
    if (tx.count >= 1000) msg += " Showing up to the first 1,000 transactions.";
    showNotice(msg);
  } catch (err) {
    showNotice(`Refresh failed: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.classList.remove("loading");
  }
}

/* --------------------------------- helpers --------------------------------- */

function parseDate(s) {
  return new Date(`${s}T00:00:00`);
}

function addDays(s, days) {
  const d = parseDate(s);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function daysInRange() {
  const ms = parseDate(state.end) - parseDate(state.start);
  return Math.round(ms / 86400000) + 1;
}

function filterTransactions() {
  const s = parseDate(state.start);
  const e = parseDate(state.end);
  return state.transactions.filter((t) => {
    const d = parseDate(t.date);
    return d >= s && d <= e;
  });
}

/* ------------------------------- date presets ------------------------------ */

function setupDateControls() {
  const presets = document.querySelectorAll(".chip[data-days]");
  presets.forEach((chip) => {
    chip.addEventListener("click", () => {
      const days = Number(chip.dataset.days);
      state.end = latestDate();
      state.start = addDays(state.end, -(days - 1));
      syncDateInputs();
      presets.forEach((c) => c.classList.toggle("active", c === chip));
      $("chip-all")?.classList.remove("active");
      update();
    });
  });

  $("chip-all").addEventListener("click", () => {
    state.start = state.account?.date_range?.earliest || state.transactions[0]?.date;
    state.end = latestDate();
    syncDateInputs();
    document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    $("chip-all").classList.add("active");
    update();
  });

  $("date-from").addEventListener("change", (e) => {
    state.start = e.target.value;
    document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    update();
  });
  $("date-to").addEventListener("change", (e) => {
    state.end = e.target.value;
    document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    update();
  });
}

function latestDate() {
  return state.account?.date_range?.latest || state.transactions[0]?.date || todayStr();
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function syncDateInputs() {
  $("date-from").value = state.start;
  $("date-to").value = state.end;
  $("date-from").min = state.account?.date_range?.earliest || "";
  $("date-to").max = state.account?.date_range?.latest || "";
  const days = daysInRange();
  document.querySelectorAll(".chip[data-days]").forEach((c) => {
    c.classList.toggle("active", Number(c.dataset.days) === days && !document.querySelector("[data-all]").classList.contains("active"));
  });
}

/* -------------------------------- categories ------------------------------- */

function buildCategorySelect() {
  const select = $("category-select");
  select.innerHTML = "";
  const allOpt = document.createElement("option");
  allOpt.value = "__all__";
  allOpt.textContent = "All categories";
  allOpt.selected = state.selectedCategory === "__all__";
  select.appendChild(allOpt);

  for (const [group, names] of Object.entries(state.categories).sort()) {
    const optGroup = document.createElement("optgroup");
    optGroup.label = group;
    [...names].sort().forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      opt.selected = state.selectedCategory === name;
      optGroup.appendChild(opt);
    });
    select.appendChild(optGroup);
  }
}

function setupCategoryControls() {
  const select = $("category-select");
  select.addEventListener("change", () => {
    state.selectedCategory = select.value;
    updatePie();
  });

  $("reset-category").addEventListener("click", () => {
    state.selectedCategory = "__all__";
    select.value = "__all__";
    updatePie();
  });
}

/* ------------------------------- KPI numbers ------------------------------- */

function animateNumber(node, target, formatter) {
  const start = performance.now();
  const duration = 700;
  const from = 0;
  const step = (now) => {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    node.textContent = formatter(from + (target - from) * eased);
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function updateKpis(txs) {
  const income = txs.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0);
  const expense = txs.filter((t) => t.amount < 0).reduce((s, t) => s + t.amount, 0);
  const net = income + expense;
  const saveRate = income > 0 ? (net / income) * 100 : 0;

  const fmtMoney = (n) => (n < 0 ? `-${money(n)}` : money(n));
  animateNumber($("kpi-income"), income, (v) => money(v));
  animateNumber($("kpi-expense"), Math.abs(expense), (v) => money(v));
  animateNumber($("kpi-net"), net, (v) => `${v < 0 ? "-" : "+"}${money(v)}`);
  animateNumber($("kpi-save"), saveRate, (v) => `${v.toFixed(1)}%`);

  const incCount = txs.filter((t) => t.amount > 0).length;
  const expCount = txs.filter((t) => t.amount < 0).length;
  $("kpi-income-sub").textContent = `${incCount} transaction${incCount === 1 ? "" : "s"}`;
  $("kpi-expense-sub").textContent = `${expCount} transaction${expCount === 1 ? "" : "s"}`;
  $("kpi-net-sub").textContent = net >= 0 ? "saved this period" : "overspent this period";
  $("kpi-save-sub").textContent = income > 0 ? "of income" : "no income this period";
}

/* ------------------------------- bar chart --------------------------------- */

function bucketKey(dateStr) {
  const d = parseDate(dateStr);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return { key: `${y}-${m}`, label: d.toLocaleDateString("en-GB", { month: "short", year: "2-digit" }) };
}

function buildBarData(txs) {
  const series = new Map();
  for (const t of txs) {
    const { key, label } = bucketKey(t.date);
    if (!series.has(key)) series.set(key, { label, income: 0, expense: 0, incomeCount: 0, expenseCount: 0 });
    const b = series.get(key);
    if (t.amount > 0) {
      b.income += t.amount;
      b.incomeCount++;
    } else {
      b.expense += -t.amount;
      b.expenseCount++;
    }
  }
  return [...series.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([, v]) => v);
}

function renderBarChart(txs) {
  const data = buildBarData(txs);
  $("bar-sub").textContent = "by month · hover for transaction counts";

  const labels = data.map((d) => d.label);
  const income = data.map((d) => +d.income.toFixed(2));
  const expense = data.map((d) => +d.expense.toFixed(2));

  if (!state.barChart) state.barChart = echarts.init($("bar-chart"), null, { renderer: "canvas" });

  state.barChart.setOption(
    {
      animationDuration: 800,
      animationEasing: "cubicOut",
      grid: { left: 70, right: 20, top: 40, bottom: 30 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(13,18,32,0.92)",
        borderColor: "rgba(255,255,255,0.12)",
        textStyle: { color: "#e6eaf4", fontSize: 12 },
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(255,255,255,0.05)" } },
        formatter: (params) => {
          const bucket = data[params[0].dataIndex];
          let html = `<b>${bucket.label}</b>`;
          for (const p of params) {
            const count = p.seriesName === "Income" ? bucket.incomeCount : bucket.expenseCount;
            html += `<br/>${p.marker} ${p.seriesName}: <b>${money(p.value)}</b> · ${count} transaction${count === 1 ? "" : "s"}`;
          }
          return html;
        },
      },
      legend: { show: false },
      xAxis: {
        type: "category",
        data: labels,
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.12)" } },
        axisTick: { show: false },
        axisLabel: { color: "#8b93a7", fontSize: 11 },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.07)", type: "dashed" } },
        axisLabel: {
          color: "#8b93a7",
          fontSize: 11,
          formatter: (v) => (Math.abs(v) >= 1000 ? `€${v / 1000}k` : `€${v}`),
        },
      },
      series: [
        {
          name: "Income",
          type: "bar",
          data: income,
          barMaxWidth: 26,
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: {
              type: "linear", x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: "#5eead4" },
                { offset: 1, color: "#0d9488" },
              ],
            },
          },
          emphasis: { itemStyle: { shadowBlur: 18, shadowColor: "rgba(45,212,191,0.5)" } },
        },
        {
          name: "Spending",
          type: "bar",
          data: expense,
          barMaxWidth: 26,
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: {
              type: "linear", x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: "#fda4af" },
                { offset: 1, color: "#e11d48" },
              ],
            },
          },
          emphasis: { itemStyle: { shadowBlur: 18, shadowColor: "rgba(251,113,133,0.5)" } },
        },
      ],
    },
    { notMerge: true },
  );
}

/* --------------------------------- pie chart ------------------------------- */

const PIE_COLORS = [
  "#2dd4bf", "#60a5fa", "#a78bfa", "#f472b6", "#fbbf24",
  "#34d399", "#f87171", "#818cf8", "#2dd4bf", "#f97316",
  "#4ade80", "#c084fc", "#22d3ee", "#fb923c", "#e879f9",
  "#a3e635", "#38bdf8", "#fda4af", "#facc15", "#5eead4",
];

function buildPieData(txs) {
  const byKey = new Map(); // key -> { value, txs: [] }
  const drill = state.selectedCategory !== "__all__";

  for (const t of txs) {
    if (t.amount >= 0) continue;
    const cat = t.category || "Uncategorized";
    if (drill && cat !== state.selectedCategory) continue;
    const key = drill ? t.merchant || "Unknown merchant" : cat;
    if (!byKey.has(key)) byKey.set(key, { value: 0, txs: [] });
    const rec = byKey.get(key);
    rec.value += -t.amount;
    rec.txs.push(t);
  }

  let rows = [...byKey.entries()].map(([name, rec]) => ({
    name,
    value: +rec.value.toFixed(2),
    txs: rec.txs,
  }));
  rows.sort((a, b) => b.value - a.value);

  const MAX_SLICES = 12;
  if (rows.length > MAX_SLICES) {
    const top = rows.slice(0, MAX_SLICES - 1);
    const rest = rows.slice(MAX_SLICES - 1);
    rows = [
      ...top,
      {
        name: "Other",
        value: +rest.reduce((s, r) => s + r.value, 0).toFixed(2),
        txs: rest.flatMap((r) => r.txs),
      },
    ];
  }
  return rows;
}

function renderPieChart(txs) {
  const data = buildPieData(txs);
  const total = data.reduce((s, d) => s + d.value, 0);
  const drill = state.selectedCategory !== "__all__";
  state.pieSlices = data;

  $("pie-title").textContent = drill ? `Inside ${state.selectedCategory}` : "Spending by Category";
  $("pie-sub").textContent = drill ? "share by merchant · click a slice for details" : "share of total spending · click a slice for details";

  if (!state.pieChart) {
    state.pieChart = echarts.init($("pie-chart"), null, { renderer: "canvas" });
    state.pieChart.on("click", (params) => {
      const slice = state.pieSlices?.[params.dataIndex];
      if (slice && slice.txs && slice.txs.length) openTransactionsModal(slice.name, slice.txs);
    });
  }

  state.pieChart.setOption(
    {
      animationDuration: 800,
      animationEasing: "cubicOut",
      color: PIE_COLORS,
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(13,18,32,0.92)",
        borderColor: "rgba(255,255,255,0.12)",
        textStyle: { color: "#e6eaf4", fontSize: 12 },
        formatter: (p) => `${p.marker} ${p.name}<br/>${money(p.value)}<br/><b>${p.percent}%</b>`,
      },
      legend: {
        orient: "vertical",
        right: 8,
        top: "middle",
        type: "scroll",
        icon: "circle",
        itemWidth: 9,
        itemHeight: 9,
        textStyle: { color: "#aab3c7", fontSize: 11 },
      },
      graphic: [
        {
          type: "text",
          left: "center",
          top: "42%",
          style: {
            text: money(total),
            textAlign: "center",
            fill: "#fff",
            fontSize: 22,
            fontWeight: 800,
          },
        },
        {
          type: "text",
          left: "center",
          top: "53%",
          style: {
            text: "total spending",
            textAlign: "center",
            fill: "#8b93a7",
            fontSize: 11,
          },
        },
      ],
      series: [
        {
          name: "Spending",
          type: "pie",
          radius: ["48%", "72%"],
          center: ["38%", "50%"],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 8, borderColor: "#070a14", borderWidth: 2 },
          label: { show: false },
          emphasis: {
            scale: true,
            scaleSize: 8,
            label: { show: false },
            itemStyle: { shadowBlur: 24, shadowColor: "rgba(0,0,0,0.6)" },
          },
          data,
        },
      ],
    },
    { notMerge: true },
  );
}

/* ------------------------------ uncategorized ------------------------------ */

function isUncategorized(t) {
  return !t.category || t.category === "Uncategorized" || t.category === "";
}

function splitByCategory(pred) {
  const out = { categorized: 0, uncategorized: 0, catTxs: [], uncatTxs: [] };
  for (const t of state.transactions) {
    if (!pred(t)) continue;
    const amount = Math.abs(t.amount);
    if (isUncategorized(t)) {
      out.uncategorized += amount;
      out.uncatTxs.push(t);
    } else {
      out.categorized += amount;
      out.catTxs.push(t);
    }
  }
  return out;
}

const CAT_COLOR = "#2dd4bf";
const UNCAT_COLOR = "#fb7185";

function renderSplitDonut(key, domId, subId, slices) {
  const total = slices.reduce((s, d) => s + d.value, 0);
  const uncat = slices.find((d) => d.name === "Uncategorized")?.value ?? 0;
  const pct = total > 0 ? (uncat / total) * 100 : 0;
  $(subId).textContent = `total ${money(total)} · ${pct.toFixed(1)}% uncategorized`;

  state[`${key}Slices`] = slices;

  if (!state[key]) {
    state[key] = echarts.init($(domId), null, { renderer: "canvas" });
    state[key].on("click", (params) => {
      const slice = state[`${key}Slices`]?.[params.dataIndex];
      if (slice && slice.txs && slice.txs.length) openTransactionsModal(slice.name, slice.txs);
    });
  }

  state[key].setOption(
    {
      animationDuration: 800,
      animationEasing: "cubicOut",
      color: [CAT_COLOR, UNCAT_COLOR],
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(13,18,32,0.92)",
        borderColor: "rgba(255,255,255,0.12)",
        textStyle: { color: "#e6eaf4", fontSize: 12 },
        formatter: (p) => `${p.marker} ${p.name}<br/>${money(p.value)}<br/><b>${p.percent}%</b>`,
      },
      legend: {
        orient: "vertical",
        right: 8,
        top: "middle",
        icon: "circle",
        itemWidth: 9,
        itemHeight: 9,
        textStyle: { color: "#aab3c7", fontSize: 11 },
      },
      graphic: [
        {
          type: "text",
          left: "center",
          top: "40%",
          style: { text: money(total), textAlign: "center", fill: "#fff", fontSize: 20, fontWeight: 800 },
        },
        {
          type: "text",
          left: "center",
          top: "51%",
          style: { text: "total", textAlign: "center", fill: "#8b93a7", fontSize: 11 },
        },
      ],
      series: [
        {
          name: "Split",
          type: "pie",
          radius: ["48%", "72%"],
          center: ["38%", "50%"],
          itemStyle: { borderRadius: 8, borderColor: "#070a14", borderWidth: 2 },
          label: { show: false },
          emphasis: {
            scale: true,
            scaleSize: 8,
            label: { show: false },
            itemStyle: { shadowBlur: 24, shadowColor: "rgba(0,0,0,0.6)" },
          },
          data: slices.map(({ name, value }) => ({ name, value: +value.toFixed(2) })),
        },
      ],
    },
    { notMerge: true },
  );
}

function renderCatSplitPies() {
  const income = splitByCategory((t) => t.amount > 0);
  const outcome = splitByCategory((t) => t.amount < 0);

  renderSplitDonut("incomePie", "income-pie-chart", "income-pie-sub", [
    { name: "Categorized", value: income.categorized, txs: income.catTxs },
    { name: "Uncategorized", value: income.uncategorized, txs: income.uncatTxs },
  ]);
  renderSplitDonut("outcomePie", "outcome-pie-chart", "outcome-pie-sub", [
    { name: "Categorized", value: outcome.categorized, txs: outcome.catTxs },
    { name: "Uncategorized", value: outcome.uncategorized, txs: outcome.uncatTxs },
  ]);
}

function buildOutstanding() {
  const uncat = state.transactions.filter(isUncategorized);
  const anchor = state.end || latestDate();
  const windowStart = addDays(anchor, -89);
  const counts = new Map();
  for (const t of uncat) {
    if (t.date >= windowStart) counts.set(t.merchant, (counts.get(t.merchant) || 0) + 1);
  }

  const rows = [];
  for (const t of uncat) {
    const reasons = [];
    if (t.amount > 0) reasons.push("Income");
    if (-t.amount > 10) reasons.push("Spent > €10");
    if (t.date >= windowStart && (counts.get(t.merchant) || 0) >= 3) reasons.push("3+ in 90d");
    if (reasons.length) rows.push({ t, reasons });
  }
  rows.sort((a, b) => b.t.date.localeCompare(a.t.date));
  return rows;
}

function renderOutstanding() {
  const rows = buildOutstanding();
  const list = $("outstanding-list");
  list.innerHTML = "";
  if (!rows.length) {
    list.appendChild(el("p", "empty", "Nothing outstanding — you're all caught up."));
    return;
  }
  const frag = document.createDocumentFragment();
  for (const { t, reasons } of rows) {
    const item = el("div", "outstanding-item");
    item.appendChild(el("span", "mono", t.date));
    item.appendChild(el("span", "out-merchant", t.merchant || "—"));
    const amt = el("span", `num out-amount ${t.amount < 0 ? "expense-text" : "income-text"}`, signedMoney(t.amount));
    item.appendChild(amt);
    const badges = el("span", "out-reasons");
    reasons.forEach((r) => badges.appendChild(el("span", "out-reason", r)));
    item.appendChild(badges);
    frag.appendChild(item);
  }
  list.appendChild(frag);
}

function renderUncatTable() {
  const uncat = state.transactions.filter(isUncategorized);
  const sorted = [...uncat].sort((a, b) => a.date.localeCompare(b.date));
  $("uncat-table-sub").textContent = `${sorted.length} transaction${sorted.length === 1 ? "" : "s"} · sorted by date`;
  const body = $("uncat-table-body");
  body.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const t of sorted) {
    const tr = el("tr");
    tr.appendChild(el("td", "mono", t.date));
    tr.appendChild(el("td", "merchant-cell", t.merchant || "—"));
    tr.appendChild(el("td", "muted-cell", t.category || "Uncategorized"));
    const amt = el("td", `num amount-cell ${t.amount < 0 ? "expense-text" : "income-text"}`, signedMoney(t.amount));
    tr.appendChild(amt);
    frag.appendChild(tr);
  }
  body.appendChild(frag);
}

function renderUncategorized() {
  renderOutstanding();
  renderUncatTable();
  if ($("tab-uncategorized").classList.contains("active")) renderCatSplitPies();
}

function renderIncomeTable() {
  const income = state.transactions
    .filter((t) => t.amount > 0)
    .sort((a, b) => b.date.localeCompare(a.date));
  const total = income.reduce((s, t) => s + t.amount, 0);
  $("income-table-sub").textContent =
    `${income.length} transaction${income.length === 1 ? "" : "s"} · total ${money(total)}`;

  const body = $("income-table-body");
  body.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const t of income) {
    const tr = el("tr");
    tr.appendChild(el("td", "mono", t.date));
    tr.appendChild(el("td", "merchant-cell", t.merchant || "—"));
    tr.appendChild(el("td", "muted-cell", t.category || "—"));
    tr.appendChild(el("td", `num amount-cell income-text`, signedMoney(t.amount)));
    frag.appendChild(tr);
  }
  body.appendChild(frag);
}

/* --------------------------- categories comparison -------------------------- */

const CATEGORY_ICON_RULES = [
  [/grocery|supermarket|market|convenience|food hall|corner store/, "🛒"],
  [/restaurant|dining|takeout|takeaway|coffee|café|cafe|bar|pub|drink|food|delivery|meal|breakfast|lunch|dinner/, "🍽️"],
  [/health|medical|pharma|pharmac|doctor|dental|dentist|fitness|gym|wellness|vitamin|therapy|clinic|hospital/, "🏥"],
  [/transport|transit|gas|fuel|uber|lyft|taxi|metro|train|bus|parking|car|auto|bike|scooter|airport/, "🚗"],
  [/entertain|cinema|movie|stream|netflix|spotify|game|gaming|music|concert|theatre|theater|hobby/, "🎬"],
  [/shopping|clothing|retail|amazon|department|store|electronics|fashion|apparel|furniture|decor/, "🛍️"],
  [/utility|utilities|electric|water|internet|phone|mobile|tv|subscription|bill|energy|broadband/, "💡"],
  [/housing|rent|mortgage|home|repair|maintenance|property|real estate|landlord/, "🏠"],
  [/travel|flight|hotel|vacation|airline|airbnb|trip|holiday|lodging/, "✈️"],
  [/education|tuition|book|books|course|school|training|university|college|class/, "📚"],
  [/salary|income|pay|paycheck|payroll|interest|refund|dividend|deposit|bonus|wage/, "💰"],
  [/insurance/, "🛡️"],
  [/pet|vet|veterinar|animal/, "🐾"],
  [/child|baby|kids|daycare|toy|toys|nursery/, "🧸"],
  [/tax/, "🧾"],
  [/bank|fee|atm|service charge|overdraft|finance|interest charge/, "🏦"],
  [/gift|donation|charity|present|giving/, "🎁"],
  [/beauty|hair|salon|spa|cosmetic|barber|nails/, "💇"],
  [/sport|sports|fitness club|club membership|athletic/, "⚽"],
  [/uncategorized|other|misc|miscellaneous|various/, "🏷️"],
];

function iconForCategory(name) {
  const n = String(name).toLowerCase();
  for (const [re, icon] of CATEGORY_ICON_RULES) {
    if (re.test(n)) return icon;
  }
  return "🏷️";
}

function hexToRgba(hex, alpha) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function buildCategoryCompareData() {
  const len = daysInRange();
  const prevEnd = addDays(state.start, -1);
  const prevStart = addDays(prevEnd, -(len - 1));

  const byCat = new Map();
  for (const t of state.transactions) {
    if (t.amount >= 0) continue;
    const cat = t.category || "Uncategorized";
    let rec = byCat.get(cat);
    if (!rec) {
      rec = { cur: 0, prev: 0, curCount: 0, prevCount: 0 };
      byCat.set(cat, rec);
    }
    if (t.date >= state.start && t.date <= state.end) {
      rec.cur += -t.amount;
      rec.curCount++;
    } else if (t.date >= prevStart && t.date <= prevEnd) {
      rec.prev += -t.amount;
      rec.prevCount++;
    }
  }

  const rows = [...byCat.entries()]
    .map(([name, rec]) => ({ name, ...rec }))
    .filter((r) => r.cur > 0 || r.prev > 0)
    .sort((a, b) => b.cur - a.cur)
    .slice(0, 15);

  return {
    names: rows.map((r) => r.name),
    current: rows.map((r) => +r.cur.toFixed(2)),
    previous: rows.map((r) => +r.prev.toFixed(2)),
    currentCounts: rows.map((r) => r.curCount),
    previousCounts: rows.map((r) => r.prevCount),
    prevStart,
    prevEnd,
  };
}

function renderCategoriesChart() {
  if (state.activeTab !== "categories") return;

  const data = buildCategoryCompareData();
  state.catCompare = data;
  const names = data.names;
  const colors = names.map((_, i) => PIE_COLORS[i % PIE_COLORS.length]);

  $("cat-chart-sub").textContent =
    `${state.start} → ${state.end} · previous ${data.prevStart} → ${data.prevEnd}`;

  if (!state.catChart) {
    state.catChart = echarts.init($("cat-chart"), null, { renderer: "canvas" });
    state.catChart.on("click", (params) => {
      const d = state.catCompare;
      const cat = d?.names[params.dataIndex];
      if (!cat) return;
      const isPrev = params.seriesName === "Previous";
      const s = isPrev ? d.prevStart : state.start;
      const e = isPrev ? d.prevEnd : state.end;
      const txs = state.transactions.filter(
        (t) => t.category === cat && t.amount < 0 && t.date >= s && t.date <= e,
      );
      const period = isPrev ? `Previous ${d.prevStart} → ${d.prevEnd}` : `${state.start} → ${state.end}`;
      if (txs.length) openTransactionsModal(cat, txs, period);
    });
  }

  state.catChart.setOption(
    {
      animationDuration: 800,
      animationEasing: "cubicOut",
      grid: { left: 8, right: 44, top: 34, bottom: 24, containLabel: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow", shadowStyle: { color: "rgba(255,255,255,0.05)" } },
        backgroundColor: "rgba(13,18,32,0.92)",
        borderColor: "rgba(255,255,255,0.12)",
        textStyle: { color: "#e6eaf4", fontSize: 12 },
        formatter: (params) => {
          const i = params[0].dataIndex;
          const name = names[i];
          let html = `${iconForCategory(name)} <b>${name}</b><br/>`;
          for (const p of params) {
            const count = p.seriesName === "Current" ? data.currentCounts[i] : data.previousCounts[i];
            html += `${p.marker} ${p.seriesName}: <b>${money(p.value)}</b> · ${count} transaction${count === 1 ? "" : "s"}<br/>`;
          }
          return html;
        },
      },
      legend: {
        top: 0,
        right: 8,
        icon: "circle",
        itemWidth: 9,
        itemHeight: 9,
        textStyle: { color: "#aab3c7", fontSize: 11 },
        data: [
          { name: "Current", itemStyle: { color: "#e11d48" } },
          { name: "Previous", itemStyle: { color: "rgba(251,113,133,0.4)" } },
        ],
      },
      xAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.07)", type: "dashed" } },
        axisLabel: {
          color: "#8b93a7",
          fontSize: 11,
          formatter: (v) => (Math.abs(v) >= 1000 ? `€${v / 1000}k` : `€${v}`),
        },
      },
      yAxis: {
        type: "category",
        data: names,
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.12)" } },
        axisTick: { show: false },
        axisLabel: {
          color: "#8b93a7",
          fontSize: 12,
          formatter: (v) => `${iconForCategory(v)} ${v}`,
        },
      },
      series: [
        {
          name: "Current",
          type: "bar",
          data: data.current.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
          barMaxWidth: 16,
          barGap: "20%",
          barCategoryGap: "55%",
          itemStyle: { borderRadius: [0, 6, 6, 0] },
          emphasis: { itemStyle: { shadowBlur: 16, shadowColor: "rgba(0,0,0,0.45)" } },
        },
        {
          name: "Previous",
          type: "bar",
          data: data.previous.map((v, i) => ({ value: v, itemStyle: { color: hexToRgba(colors[i], 0.35) } })),
          barMaxWidth: 16,
          barGap: "20%",
          barCategoryGap: "55%",
          itemStyle: { borderRadius: [0, 6, 6, 0] },
          emphasis: { itemStyle: { shadowBlur: 16, shadowColor: "rgba(0,0,0,0.45)" } },
        },
      ],
    },
    { notMerge: true },
  );
}

/* --------------------------------- tabs ------------------------------------ */

function usesDateRange() {
  return state.activeTab === "categories" || state.activeTab === "uncategorized";
}

function toggleDateControls() {
  $("controls").classList.toggle("hidden", !usesDateRange());
}

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".tab-panel");
  tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      state.activeTab = btn.dataset.tab;
      tabs.forEach((b) => {
        const on = b === btn;
        b.classList.toggle("active", on);
        b.setAttribute("aria-selected", on);
      });
      panels.forEach((p) => {
        p.classList.toggle("active", p.id === `tab-${btn.dataset.tab}`);
      });
      toggleDateControls();
      requestAnimationFrame(() => {
        update();
        state.barChart?.resize();
        state.pieChart?.resize();
        state.incomePie?.resize();
        state.outcomePie?.resize();
        state.catChart?.resize();
      });
    });
  });
}

/* ---------------------------------- update --------------------------------- */

function updatePie() {
  if (!state.start || !state.end) return;
  renderPieChart(usesDateRange() ? filterTransactions() : state.transactions);
}

/* ---------------------------------- modal ---------------------------------- */

function openTransactionsModal(name, txs, period) {
  const sorted = [...txs].sort((a, b) => b.date.localeCompare(a.date));
  const total = sorted.reduce((s, t) => s + t.amount, 0);

  $("tx-modal-title").textContent = name;
  $("tx-modal-sub").textContent = period
    ? `${period} · ${sorted.length} transaction${sorted.length === 1 ? "" : "s"}`
    : usesDateRange()
      ? `${state.start} → ${state.end} · ${sorted.length} transaction${sorted.length === 1 ? "" : "s"}`
      : `All time · ${sorted.length} transaction${sorted.length === 1 ? "" : "s"}`;
  $("tx-modal-total").textContent = `Total: ${signedMoney(total)}`;

  const body = $("tx-modal-body");
  body.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const t of sorted) {
    const tr = el("tr");
    tr.appendChild(el("td", "mono", t.date));
    tr.appendChild(el("td", "merchant-cell", t.merchant || "—"));
    tr.appendChild(el("td", "muted-cell", t.category || "—"));
    const amt = el("td", `num amount-cell ${t.amount < 0 ? "expense-text" : "income-text"}`, signedMoney(t.amount));
    tr.appendChild(amt);
    frag.appendChild(tr);
  }
  body.appendChild(frag);

  $("tx-modal").classList.remove("hidden");
  document.body.classList.add("modal-open");
}

function closeTransactionsModal() {
  $("tx-modal").classList.add("hidden");
  document.body.classList.remove("modal-open");
}

function setupModal() {
  $("tx-modal-close").addEventListener("click", closeTransactionsModal);
  $("tx-modal").addEventListener("click", (e) => {
    if (e.target.id === "tx-modal") closeTransactionsModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeTransactionsModal();
  });
}

function update() {
  const rangeBased = usesDateRange();
  if (rangeBased && (!state.start || !state.end)) return;
  if (rangeBased && parseDate(state.start) > parseDate(state.end)) {
    showNotice("Start date is after end date — check your range.");
    return;
  }
  clearNotice();

  const txs = rangeBased ? filterTransactions() : state.transactions;
  const rangeDays = daysInRange();

  if (state.activeTab === "overview") {
    updateKpis(txs);
    renderBarChart(txs);
    renderPieChart(txs);
  } else if (state.activeTab === "categories") {
    renderCategoriesChart();
  } else if (state.activeTab === "income") {
    renderIncomeTable();
  } else if (state.activeTab === "uncategorized") {
    renderUncategorized();
  }

  const n = txs.length;
  $("foot-range").textContent = rangeBased
    ? `${state.start} → ${state.end} · ${rangeDays} day${rangeDays === 1 ? "" : "s"} · ` +
      `${n} transaction${n === 1 ? "" : "s"}`
    : `All data · ${n} transaction${n === 1 ? "" : "s"}`;
  $("foot-source").textContent =
    `${state.account?.name ?? "account"} · moneyflow REST API`;
}

function onResize() {
  state.barChart?.resize();
  state.pieChart?.resize();
  state.incomePie?.resize();
  state.outcomePie?.resize();
  state.catChart?.resize();
}
window.addEventListener("resize", () => {
  clearTimeout(onResize._t);
  onResize._t = setTimeout(onResize, 150);
});

/* ---------------------------------- init ----------------------------------- */

async function init() {
  const loader = $("loader");
  try {
    const [account, cats, tx] = await Promise.all([
      api("/account"),
      api("/categories"),
      api("/transactions?limit=1000"),
    ]);

    state.account = account;
    state.categories = cats.categories;

    state.transactions = tx.results;
    if (tx.count >= 1000) {
      showNotice("Showing up to the first 1,000 transactions. For larger datasets the dashboard aggregates server-side only.");
    }

    state.activeTab = "overview";
    state.end = latestDate();
    state.start = addDays(state.end, -44);

    $("account-line").textContent =
      `${account.name} · ${account.backend_type} · ` +
      `${account.transaction_count} transactions · ${account.category_count} categories`;

    buildCategorySelect();
    setupCategoryControls();
    setupDateControls();
    setupModal();
    setupTabs();
    syncDateInputs();
    toggleDateControls();
    $("refresh-btn").addEventListener("click", refreshData);
    update();
  } catch (err) {
    showNotice(`Failed to load data: ${err.message}. Make sure the moneyflow REST server is running (uv run python -m moneyflow.rest).`);
    console.error(err);
  } finally {
    loader.classList.add("hidden");
  }
}

init();
