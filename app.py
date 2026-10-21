// =========================================================
// Aviation Accident Explorer
// Loads data/accidents.json (built by build_data.py), filters it in the
// browser, and redraws every chart when a filter changes.
// =========================================================

// ---------- Chart colors ----------
const COLOR = {
    all: "#3E8BCB",        // clear-sky blue
    fatal: "#B23A48",      // deep red
    destroyed: "#E08E2B",  // amber
    damage: { "Destroyed": "#B23A48", "Substantial": "#E08E2B", "Minor": "#3E8BCB", "Other / unknown": "#8A939E" },
    weather: { "VMC": "#3E8BCB", "IMC": "#6A4C9C", "Unknown": "#8A939E" },
    bar: "#3E8BCB",
    barActive: "#1F5F99",
    grid: "#E3EBF2",
    axis: "#4A5A6A",
    text: "#0E1A26"
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const fmt = d3.format(",");
const pct = v => (isFinite(v) ? (v * 100).toFixed(1) : "0.0") + "%";

const state = { from: null, to: null, weather: -1, damage: -1, purpose: -1, engine: -1, place: -1 };
let D = null;          // the loaded data
let rows = [];         // indexes of records that match the filters

const tooltip = d3.select("body").append("div").attr("class", "tooltip").style("display", "none");
function showTip(event, html) {
    tooltip.style("display", "block").html(html);
    const box = tooltip.node().getBoundingClientRect();
    let x = event.pageX + 14;
    if (x + box.width > window.scrollX + document.documentElement.clientWidth - 8) x = event.pageX - box.width - 14;
    tooltip.style("left", x + "px").style("top", (event.pageY - box.height - 10) + "px");
}
const hideTip = () => tooltip.style("display", "none");

// ---------- Load ----------
d3.json("data/accidents.json").then(data => {
    D = data;
    buildFilters();
    update();
    window.addEventListener("resize", debounce(drawAll, 150));
}).catch(err => {
    console.error(err);
    d3.select("#status").text("The accident data couldn't load. Make sure data/accidents.json is in the repository, then refresh.");
});

// ---------- Filters ----------
function buildFilters() {
    const years = d3.range(d3.min(D.year), d3.max(D.year) + 1);
    state.from = years[0];
    state.to = years[years.length - 1];

    fillSelect("#f-from", years.map(y => [y, y]), state.from);
    fillSelect("#f-to", years.map(y => [y, y]), state.to);
    ["weather", "damage", "purpose", "engine", "place"].forEach(key => {
        const allLabel = { weather: "All weather", damage: "All damage", purpose: "All purposes", engine: "All engines", place: "All locations" }[key];
        fillSelect("#f-" + key, [[-1, allLabel]].concat(D.labels[key].map((l, i) => [i, l])), -1);
    });

    d3.select("#f-from").on("change", function () { setFilter("from", +this.value); });
    d3.select("#f-to").on("change", function () { setFilter("to", +this.value); });
    ["weather", "damage", "purpose", "engine", "place"].forEach(key => {
        d3.select("#f-" + key).on("change", function () { setFilter(key, +this.value); });
    });
    d3.select("#f-reset").on("click", () => {
        Object.assign(state, { from: years[0], to: years[years.length - 1], weather: -1, damage: -1, purpose: -1, engine: -1, place: -1 });
        syncSelects();
        update();
    });
}

function fillSelect(sel, options, value) {
    d3.select(sel).selectAll("option").data(options).join("option")
        .attr("value", d => d[0]).text(d => d[1]);
    d3.select(sel).property("value", value);
}

function syncSelects() {
    Object.keys(state).forEach(k => d3.select("#f-" + (k === "from" || k === "to" ? k : k)).property("value", state[k]));
}

function setFilter(key, value) {
    state[key] = value;
    // Keep the year range the right way round
    if (state.from > state.to) {
        if (key === "from") state.to = state.from; else state.from = state.to;
    }
    syncSelects();
    update();
}

// Click a bar to filter by it; click the same bar again to clear that filter
function toggleFilter(key, value) {
    setFilter(key, state[key] === value ? -1 : value);
}

function matches(i, skip) {
    if (D.year[i] < state.from || D.year[i] > state.to) return false;
    for (const key of ["weather", "damage", "purpose", "engine", "place"]) {
        if (key !== skip && state[key] !== -1 && D[key][i] !== state[key]) return false;
    }
    return true;
}

// ---------- Update everything ----------
function update() {
    rows = [];
    for (let i = 0; i < D.count; i++) if (matches(i)) rows.push(i);

    const active = ["weather", "damage", "purpose", "engine", "place"].filter(k => state[k] !== -1)
        .map(k => D.labels[k][state[k]]);
    const yearText = state.from === state.to ? state.from : `${state.from}–${state.to}`;
    d3.select("#status").text(`Showing ${fmt(rows.length)} of ${fmt(D.count)} accidents · ${yearText}` + (active.length ? " · " + active.join(" · ") : ""));

    drawKpis();
    drawAll();
}

function drawAll() {
    if (!D) return;
    drawYears();
    drawWeather();
    drawDamage();
    drawCategory("#chart-purpose", "purpose");
    drawCategory("#chart-engine", "engine");
    drawCategory("#chart-place", "place");
    drawMonths();
    drawRiskContext();
}

function drawKpis() {
    const n = rows.length;
    let fatalAcc = 0, deaths = 0, destroyed = 0;
    rows.forEach(i => {
        if (D.fatal[i] > 0) fatalAcc++;
        deaths += D.fatal[i];
        if (D.damage[i] === 0) destroyed++;
    });
    const years = state.to - state.from + 1;
    d3.select("#k-acc").text(fmt(n));
    d3.select("#k-acc-sub").text(`about ${fmt(Math.round(n / years))} a year`);
    d3.select("#k-fatal").text(fmt(fatalAcc));
    d3.select("#k-fatal-sub").text(`${pct(fatalAcc / n)} of accidents`);
    d3.select("#k-deaths").text(fmt(deaths));
    d3.select("#k-deaths-sub").text(n ? `${(deaths / Math.max(fatalAcc, 1)).toFixed(1)} per fatal accident` : " ");
    d3.select("#k-destroyed").text(fmt(destroyed));
    d3.select("#k-destroyed-sub").text(`${pct(destroyed / n)} of accidents`);
}

// ---------- Helpers ----------
function chartSize(sel, ratio, minH) {
    const w = Math.max(280, d3.select(sel).node().clientWidth);
    return { w, h: Math.max(minH || 0, Math.round(w * ratio)) };
}

function emptyNote(sel, text) {
    d3.select(sel).html("").append("p").attr("class", "note").text(text);
}

// ---------- Accidents per year (line chart with hover) ----------
function drawYears() {
    const sel = "#chart-years";
    const { w, h } = chartSize(sel, 0.32, 240);
    const m = { top: 12, right: 18, bottom: 32, left: 56 };
    const iw = w - m.left - m.right, ih = h - m.top - m.bottom;

    const years = d3.range(state.from, state.to + 1);
    const all = new Map(years.map(y => [y, 0])), fatal = new Map(years.map(y => [y, 0]));
    rows.forEach(i => {
        all.set(D.year[i], all.get(D.year[i]) + 1);
        if (D.fatal[i] > 0) fatal.set(D.year[i], fatal.get(D.year[i]) + 1);
    });
    const series = years.map(y => ({ year: y, all: all.get(y), fatal: fatal.get(y) }));

    d3.select(sel).html("");
    if (!rows.length) return emptyNote(sel, "No accidents match these filters. Try Reset filters.");

    const svg = d3.select(sel).append("svg").attr("viewBox", `0 0 ${w} ${h}`)
        .attr("role", "img").attr("aria-label", "Line chart of accidents and fatal accidents per year");
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);

    const x = d3.scaleLinear().domain(d3.extent(years)).range([0, iw]);
    if (years.length === 1) x.domain([years[0] - 0.5, years[0] + 0.5]);
    const y = d3.scaleLinear().domain([0, d3.max(series, d => d.all) || 1]).nice().range([ih, 0]);

    g.append("g").call(d3.axisLeft(y).ticks(5).tickSize(-iw).tickFormat(""))
        .call(a => a.select(".domain").remove()).call(a => a.selectAll("line").attr("stroke", COLOR.grid));
    g.append("g").attr("transform", `translate(0,${ih})`)
        .call(d3.axisBottom(x).ticks(Math.min(years.length, Math.floor(iw / 70))).tickFormat(d3.format("d")))
        .call(a => a.selectAll("text").attr("fill", COLOR.axis).attr("font-size", 13))
        .call(a => a.selectAll("path,line").attr("stroke", "#9DB6CC"));
    g.append("g").call(d3.axisLeft(y).ticks(5).tickFormat(fmt))
        .call(a => a.selectAll("text").attr("fill", COLOR.axis).attr("font-size", 13))
        .call(a => a.select(".domain").remove()).call(a => a.selectAll("line").remove());

    const line = key => d3.line().x(d => x(d.year)).y(d => y(d[key]));
    // Area under all accidents (solid, light)
    g.append("path").datum(series).attr("fill", "#DCEBF7")
        .attr("d", d3.area().x(d => x(d.year)).y0(ih).y1(d => y(d.all)));
    g.append("path").datum(series).attr("fill", "none").attr("stroke", COLOR.all).attr("stroke-width", 2.5).attr("d", line("all"));
    g.append("path").datum(series).attr("fill", "none").attr("stroke", COLOR.fatal).attr("stroke-width", 2.5).attr("d", line("fatal"));

    // Hover: vertical guide, dots and tooltip for the nearest year
    const guide = g.append("line").attr("y1", 0).attr("y2", ih).attr("stroke", "#0B2545").attr("stroke-width", 1).style("display", "none");
    const dotAll = g.append("circle").attr("r", 5).attr("fill", COLOR.all).attr("stroke", "#fff").attr("stroke-width", 2).style("display", "none");
    const dotFatal = g.append("circle").attr("r", 5).attr("fill", COLOR.fatal).attr("stroke", "#fff").attr("stroke-width", 2).style("display", "none");
    g.append("rect").attr("width", iw).attr("height", ih).attr("fill", "transparent")
        .on("mousemove", function (event) {
            const yr = Math.round(x.invert(d3.pointer(event)[0]));
            const d = series.find(s => s.year === yr);
            if (!d) return;
            guide.style("display", null).attr("x1", x(d.year)).attr("x2", x(d.year));
            dotAll.style("display", null).attr("cx", x(d.year)).attr("cy", y(d.all));
            dotFatal.style("display", null).attr("cx", x(d.year)).attr("cy", y(d.fatal));
            showTip(event, `<strong>${d.year}</strong><br>${fmt(d.all)} accidents<br>${fmt(d.fatal)} fatal (${pct(d.fatal / (d.all || 1))})`);
        })
        .on("mouseleave", () => { guide.style("display", "none"); dotAll.style("display", "none"); dotFatal.style("display", "none"); hideTip(); });
}

// ---------- Weather: % fatal and % destroyed by condition ----------
function drawWeather() {
    const sel = "#chart-weather";
    // Ignore the weather filter here, so all conditions stay visible for comparison
    const stats = D.labels.weather.map((label, k) => ({ label, k, n: 0, fatal: 0, destroyed: 0 }));
    for (let i = 0; i < D.count; i++) {
        if (!matches(i, "weather")) continue;
        const s = stats[D.weather[i]];
        s.n++;
        if (D.fatal[i] > 0) s.fatal++;
        if (D.damage[i] === 0) s.destroyed++;
    }
    const data = stats.filter(s => s.n > 0);
    d3.select(sel).html("");
    if (!data.length) { d3.select("#weather-insight").text(""); return emptyNote(sel, "No accidents match these filters."); }

    const { w } = chartSize(sel, 0, 0);
    const rowH = 64, m = { top: 6, right: 70, bottom: 24, left: 92 };
    const h = m.top + m.bottom + data.length * rowH;
    const iw = w - m.left - m.right;
    const svg = d3.select(sel).append("svg").attr("viewBox", `0 0 ${w} ${h}`)
        .attr("role", "img").attr("aria-label", "Bar chart of the share of fatal accidents and destroyed aircraft by weather condition");
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);
    const x = d3.scaleLinear().domain([0, Math.max(0.01, d3.max(data, d => Math.max(d.fatal / d.n, d.destroyed / d.n)))]).nice().range([0, iw]);

    g.append("g").attr("transform", `translate(0,${data.length * rowH})`)
        .call(d3.axisBottom(x).ticks(4).tickFormat(d3.format(".0%")))
        .call(a => a.selectAll("text").attr("fill", COLOR.axis).attr("font-size", 12))
        .call(a => a.selectAll("path,line").attr("stroke", "#9DB6CC"));

    const row = g.selectAll(".wrow").data(data).join("g")
        .attr("class", "wrow clickable")
        .attr("transform", (d, i) => `translate(0,${i * rowH})`)
        .attr("opacity", d => state.weather === -1 || state.weather === d.k ? 1 : 0.35)
        .on("click", (e, d) => toggleFilter("weather", d.k));

    row.append("rect").attr("x", -m.left).attr("width", w).attr("height", rowH).attr("fill", "transparent");
    row.append("text").attr("x", -10).attr("y", rowH / 2 - 6).attr("text-anchor", "end").attr("font-weight", 600).attr("fill", COLOR.text).text(d => d.label);
    row.append("text").attr("x", -10).attr("y", rowH / 2 + 12).attr("text-anchor", "end").attr("font-size", 12).attr("fill", COLOR.axis).text(d => fmt(d.n) + " acc.");

    [["fatal", COLOR.fatal, 10], ["destroyed", COLOR.destroyed, 34]].forEach(([key, col, yOff]) => {
        row.append("rect").attr("y", yOff).attr("height", 20).attr("fill", col)
            .attr("width", d => x(d[key] / d.n))
            .on("mousemove", (e, d) => showTip(e, `<strong>${d.label}</strong><br>${fmt(d[key])} of ${fmt(d.n)} accidents ${key === "fatal" ? "were fatal" : "destroyed the aircraft"} (${pct(d[key] / d.n)})`))
            .on("mouseleave", hideTip);
        row.append("text").attr("y", yOff + 15).attr("x", d => x(d[key] / d.n) + 6)
            .attr("font-size", 13).attr("font-weight", 600).attr("fill", COLOR.text).text(d => pct(d[key] / d.n));
    });

    const vmc = data.find(d => d.label === "VMC"), imc = data.find(d => d.label === "IMC");
    if (vmc && imc && vmc.n >= 20 && imc.n >= 20) {
        const ratio = (imc.fatal / imc.n) / (vmc.fatal / vmc.n);
        d3.select("#weather-insight").html(
            `In instrument conditions (IMC), <strong>${pct(imc.fatal / imc.n)}</strong> of accidents were fatal, compared with <strong>${pct(vmc.fatal / vmc.n)}</strong> in clear visual conditions (VMC): about <strong>${ratio.toFixed(1)} times</strong> as likely.`);
    } else {
        d3.select("#weather-insight").text("Select a wider range to compare visual (VMC) and instrument (IMC) conditions.");
    }
}

// ---------- Aircraft damage ----------
function drawDamage() {
    const sel = "#chart-damage";
    const counts = D.labels.damage.map((label, k) => ({ label, k, n: 0 }));
    for (let i = 0; i < D.count; i++) if (matches(i, "damage")) counts[D.damage[i]].n++;
    const total = d3.sum(counts, d => d.n);
    d3.select(sel).html("");
    if (!total) return emptyNote(sel, "No accidents match these filters.");

    const { w } = chartSize(sel, 0, 0);
    const rowH = 46, m = { top: 4, right: 110, bottom: 6, left: 130 };
    const h = m.top + m.bottom + counts.length * rowH;
    const iw = w - m.left - m.right;
    const svg = d3.select(sel).append("svg").attr("viewBox", `0 0 ${w} ${h}`)
        .attr("role", "img").attr("aria-label", "Bar chart of accidents by aircraft damage");
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);
    const x = d3.scaleLinear().domain([0, d3.max(counts, d => d.n) || 1]).range([0, iw]);

    const row = g.selectAll(".drow").data(counts).join("g")
        .attr("class", "drow clickable")
        .attr("transform", (d, i) => `translate(0,${i * rowH})`)
        .attr("opacity", d => state.damage === -1 || state.damage === d.k ? 1 : 0.35)
        .on("click", (e, d) => toggleFilter("damage", d.k))
        .on("mousemove", (e, d) => showTip(e, `<strong>${d.label}</strong><br>${fmt(d.n)} accidents (${pct(d.n / total)})`))
        .on("mouseleave", hideTip);
    row.append("rect").attr("x", -m.left).attr("width", w).attr("height", rowH).attr("fill", "transparent");
    row.append("text").attr("x", -10).attr("y", rowH / 2).attr("dy", "0.35em").attr("text-anchor", "end").attr("font-weight", 600).attr("fill", COLOR.text).text(d => d.label);
    row.append("rect").attr("y", 8).attr("height", rowH - 16).attr("fill", d => COLOR.damage[d.label]).attr("width", d => x(d.n));
    row.append("text").attr("x", d => x(d.n) + 6).attr("y", rowH / 2).attr("dy", "0.35em").attr("font-size", 13).attr("fill", COLOR.text)
        .text(d => `${fmt(d.n)} · ${pct(d.n / total)}`);
}

// ---------- Purpose / engine / place: count bars with % fatal ----------
function drawCategory(sel, key) {
    const stats = D.labels[key].map((label, k) => ({ label, k, n: 0, fatal: 0 }));
    for (let i = 0; i < D.count; i++) {
        if (!matches(i, key)) continue;
        const s = stats[D[key][i]];
        s.n++;
        if (D.fatal[i] > 0) s.fatal++;
    }
    const data = stats.filter(s => s.n > 0).sort((a, b) => b.n - a.n);
    d3.select(sel).html("");
    if (!data.length) return emptyNote(sel, "No accidents match these filters.");

    const { w } = chartSize(sel, 0, 0);
    const rowH = 34, m = { top: 4, right: 118, bottom: 6, left: 140 };
    const h = m.top + m.bottom + data.length * rowH;
    const iw = w - m.left - m.right;
    const svg = d3.select(sel).append("svg").attr("viewBox", `0 0 ${w} ${h}`)
        .attr("role", "img").attr("aria-label", `Bar chart of accidents by ${key}`);
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);
    const x = d3.scaleLinear().domain([0, d3.max(data, d => d.n)]).range([0, iw]);

    const row = g.selectAll(".crow").data(data).join("g")
        .attr("class", "crow clickable")
        .attr("transform", (d, i) => `translate(0,${i * rowH})`)
        .attr("opacity", d => state[key] === -1 || state[key] === d.k ? 1 : 0.35)
        .on("click", (e, d) => toggleFilter(key, d.k))
        .on("mousemove", (e, d) => showTip(e, `<strong>${d.label}</strong><br>${fmt(d.n)} accidents<br>${fmt(d.fatal)} fatal (${pct(d.fatal / d.n)})`))
        .on("mouseleave", hideTip);
    row.append("rect").attr("x", -m.left).attr("width", w).attr("height", rowH).attr("fill", "transparent");
    row.append("text").attr("x", -10).attr("y", rowH / 2).attr("dy", "0.35em").attr("text-anchor", "end").attr("fill", COLOR.text).attr("font-size", 14).text(d => d.label);
    row.append("rect").attr("y", 6).attr("height", rowH - 12)
        .attr("fill", d => state[key] === d.k ? COLOR.barActive : COLOR.bar).attr("width", d => Math.max(1, x(d.n)));
    row.append("text").attr("x", d => x(d.n) + 6).attr("y", rowH / 2).attr("dy", "0.35em").attr("font-size", 13).attr("fill", COLOR.text)
        .text(d => `${fmt(d.n)} · `)
        .append("tspan").attr("fill", COLOR.fatal).attr("font-weight", 600).text(d => `${pct(d.fatal / d.n)} fatal`);
}

// ---------- Months ----------
function drawMonths() {
    const sel = "#chart-month";
    const counts = MONTHS.map((label, k) => ({ label, k, n: 0 }));
    rows.forEach(i => counts[D.month[i] - 1].n++);
    d3.select(sel).html("");
    if (!rows.length) return emptyNote(sel, "No accidents match these filters.");

    const { w, h } = chartSize(sel, 0.5, 220);
    const m = { top: 18, right: 6, bottom: 26, left: 6 };
    const iw = w - m.left - m.right, ih = h - m.top - m.bottom;
    const svg = d3.select(sel).append("svg").attr("viewBox", `0 0 ${w} ${h}`)
        .attr("role", "img").attr("aria-label", "Column chart of accidents by month");
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);
    const x = d3.scaleBand().domain(MONTHS).range([0, iw]).padding(0.18);
    const y = d3.scaleLinear().domain([0, d3.max(counts, d => d.n) || 1]).range([ih, 0]);
    const peak = d3.max(counts, d => d.n);

    const col = g.selectAll(".mcol").data(counts).join("g").attr("class", "mcol")
        .on("mousemove", (e, d) => showTip(e, `<strong>${d.label}</strong><br>${fmt(d.n)} accidents (${pct(d.n / rows.length)})`))
        .on("mouseleave", hideTip);
    col.append("rect").attr("x", d => x(d.label)).attr("width", x.bandwidth())
        .attr("y", d => y(d.n)).attr("height", d => ih - y(d.n))
        .attr("fill", d => d.n === peak ? COLOR.barActive : COLOR.bar);
    col.append("text").attr("x", d => x(d.label) + x.bandwidth() / 2).attr("y", ih + 18).attr("text-anchor", "middle")
        .attr("font-size", 12).attr("fill", COLOR.axis).text(d => d.label);
    col.filter(d => d.n === peak).append("text").attr("x", d => x(d.label) + x.bandwidth() / 2).attr("y", d => y(d.n) - 5)
        .attr("text-anchor", "middle").attr("font-size", 12).attr("font-weight", 600).attr("fill", COLOR.text).text(d => fmt(d.n));
}

// =========================================================
// Weather risk check
// Same rules as compute_rule_based_risk() in model_utils.py
// =========================================================
const CITIES = [
    ["New York", 40.71, -74.01], ["Los Angeles", 34.05, -118.24], ["Chicago", 41.88, -87.63],
    ["Houston", 29.76, -95.37], ["Phoenix", 33.45, -112.07], ["Boston", 42.36, -71.06],
    ["San Francisco", 37.77, -122.42], ["Seattle", 47.61, -122.33], ["Miami", 25.76, -80.19],
    ["Dallas", 32.78, -96.80], ["London", 51.51, -0.13], ["Paris", 48.86, 2.35],
    ["Dubai", 25.20, 55.27], ["Tokyo", 35.68, 139.69], ["Delhi", 28.61, 77.21], ["Mumbai", 19.08, 72.88]
];

function riskRules(temp, humidity, wind, visibility) {
    const parts = [];
    let t = 0, tRule = "Between -5 °C and 30 °C";
    if (temp >= 40) { t = 25; tRule = "40 °C or hotter"; }
    else if (temp >= 30) { t = 15; tRule = "30 °C or hotter"; }
    else if (temp <= -5) { t = 10; tRule = "-5 °C or colder"; }
    parts.push(["Temperature", tRule, t]);

    let h = 0, hRule = "Below 60%";
    if (humidity >= 80) { h = 20; hRule = "80% or more"; }
    else if (humidity >= 60) { h = 10; hRule = "60% or more"; }
    parts.push(["Humidity", hRule, h]);

    let wd = 0, wRule = "Below 25 m/s";
    if (wind >= 40) { wd = 30; wRule = "40 m/s or more"; }
    else if (wind >= 25) { wd = 15; wRule = "25 m/s or more"; }
    parts.push(["Wind", wRule, wd]);

    let v = 0, vRule = "5,000 m or more";
    if (visibility < 2000) { v = 25; vRule = "Under 2,000 m"; }
    else if (visibility < 5000) { v = 10; vRule = "Under 5,000 m"; }
    parts.push(["Visibility", vRule, v]);

    return { parts, score: Math.min(d3.sum(parts, p => p[2]), 100) };
}

function updateRisk() {
    const temp = +d3.select("#s-temp").property("value");
    const hum = +d3.select("#s-hum").property("value");
    const wind = +d3.select("#s-wind").property("value");
    const vis = +d3.select("#s-vis").property("value");

    d3.select("#o-temp").text(`${temp} °C`);
    d3.select("#o-hum").text(`${hum}%`);
    d3.select("#o-wind").text(`${wind} m/s`);
    d3.select("#o-vis").text(vis >= 10000 ? "10+ km" : `${fmt(vis)} m`);

    const { parts, score } = riskRules(temp, hum, wind, vis);
    d3.select("#score").text(score);
    d3.select("#needle").style("left", score + "%");
    const band = score >= 60 ? ["High", "#B23A48", "#FFFFFF"] : score >= 30 ? ["Moderate", "#E08E2B", "#000000"] : ["Low", "#3E8BCB", "#000000"];
    d3.select("#band").text(band[0]).style("background", band[1]).style("color", band[2]);

    d3.select("#breakdown").selectAll("tr").data(parts).join("tr")
        .html(p => `<td>${p[0]}</td><td>${p[1]}</td><td class="num">${p[2] ? "+" + p[2] : "0"}</td>`);
}

function drawRiskContext() {
    // Fatal share by visibility condition, from all records (not the filters), for context
    let vN = 0, vF = 0, iN = 0, iF = 0;
    const vmc = D.labels.weather.indexOf("VMC"), imc = D.labels.weather.indexOf("IMC");
    for (let i = 0; i < D.count; i++) {
        if (D.weather[i] === vmc) { vN++; if (D.fatal[i] > 0) vF++; }
        else if (D.weather[i] === imc) { iN++; if (D.fatal[i] > 0) iF++; }
    }
    d3.select("#risk-context").html(
        `<strong>Why visibility matters:</strong> across all ${fmt(D.count)} records, ${pct(iF / iN)} of accidents in instrument conditions (low visibility) were fatal, against ${pct(vF / vN)} in clear visual conditions.`);
}

// Map Open-Meteo weather codes to the condition names used in app.py
function conditionName(code) {
    if (code <= 1) return "Clear";
    if (code <= 48) return "Clouds or fog";
    if (code <= 67 || (code >= 80 && code <= 82)) return "Rain";
    if (code <= 77 || code === 85 || code === 86) return "Snow";
    return "Thunderstorm";
}

function setupRisk() {
    d3.select("#city").selectAll("option").data(CITIES).join("option").attr("value", (d, i) => i).text(d => d[0]);
    d3.selectAll("#s-temp, #s-hum, #s-wind, #s-vis").on("input", () => {
        d3.select("#live-status").text("Using the values you set.");
        updateRisk();
    });

    d3.select("#live-btn").on("click", () => {
        const [name, lat, lon] = CITIES[+d3.select("#city").property("value")];
        const status = d3.select("#live-status").text(`Getting the current weather for ${name}…`);
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
            `&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,visibility&wind_speed_unit=ms&timezone=auto`;
        fetch(url)
            .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(data => {
                const c = data.current;
                const vis = c.visibility != null ? Math.min(10000, Math.round(c.visibility)) : 10000;
                d3.select("#s-temp").property("value", Math.round(c.temperature_2m));
                d3.select("#s-hum").property("value", Math.round(c.relative_humidity_2m));
                d3.select("#s-wind").property("value", Math.round(c.wind_speed_10m));
                d3.select("#s-vis").property("value", vis);
                updateRisk();
                const when = c.time ? c.time.replace("T", " ") : "now";
                status.text(`${name}, local time ${when}: ${conditionName(c.weather_code)}, ${c.temperature_2m} °C, ${c.relative_humidity_2m}% humidity, wind ${c.wind_speed_10m} m/s` +
                    (c.visibility != null ? `, visibility ${fmt(Math.round(c.visibility))} m.` : "."));
            })
            .catch(() => status.text("Live weather isn't available right now. Check your internet connection, or set the conditions with the sliders."));
    });

    updateRisk();
}
setupRisk();

// ---------- Fade sections in as they scroll into view ----------
(function () {
    const items = document.querySelectorAll(".fade-item");
    if (!("IntersectionObserver" in window)) { items.forEach(el => el.classList.add("show")); return; }
    let first = true;
    const io = new IntersectionObserver(entries => {
        let order = 0;
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            if (first) { entry.target.style.transitionDelay = Math.min(order * 0.12, 0.6) + "s"; order++; }
            entry.target.classList.add("show");
            io.unobserve(entry.target);
        });
        first = false;
    }, { threshold: 0.08 });
    requestAnimationFrame(() => items.forEach(el => io.observe(el)));
})();

function debounce(fn, ms) {
    let t;
    return () => { clearTimeout(t); t = setTimeout(fn, ms); };
}
