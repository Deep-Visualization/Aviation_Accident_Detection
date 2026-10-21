// =========================================================
// Flight Weather Risk Check
// The web version of app.py: city + aircraft type -> live weather
// -> rule-based weather risk score (model_utils.py) -> historical
// context from the NTSB records in Accidents.json (built by Build_data.py).
// =========================================================

// ---------- Same lists as app.py ----------
const CITIES = [
    ["New York", 40.71, -74.01], ["Los Angeles", 34.05, -118.24], ["Chicago", 41.88, -87.63],
    ["Houston", 29.76, -95.37], ["Phoenix", 33.45, -112.07], ["Boston", 42.36, -71.06],
    ["San Francisco", 37.77, -122.42], ["Seattle", 47.61, -122.33], ["Miami", 25.76, -80.19],
    ["Dallas", 32.78, -96.80], ["London", 51.51, -0.13], ["Paris", 48.86, 2.35],
    ["Dubai", 25.20, 55.27], ["Tokyo", 35.68, 139.69], ["Delhi", 28.61, 77.21], ["Mumbai", 19.08, 72.88]
];

// Each aircraft type from app.py, matched to the closest engine group(s) in the NTSB records
const AIRCRAFT = [
    { name: "Commercial Jet",    engines: ["Turbo fan", "Turbo jet"],  group: "turbofan and turbojet aircraft" },
    { name: "Cargo Aircraft",    engines: ["Turbo prop", "Turbo fan"], group: "turboprop and turbofan aircraft" },
    { name: "Helicopter",        engines: ["Turbo shaft"],             group: "turboshaft aircraft (mostly helicopters)" },
    { name: "Plane",             engines: ["Reciprocating"],           group: "piston-engine aircraft" },
    { name: "Military Aircraft", engines: ["Turbo jet"],               group: "turbojet aircraft" },
    { name: "Glider",            engines: ["Without engine"],          group: "aircraft without an engine" },
    { name: "Ultralight",        engines: ["Other"],                   group: "other small engines (2- and 4-cycle, electric)" },
    { name: "Unknown",           engines: null,                        group: "all aircraft" }
];

// ---------- Chart colors ----------
const COLOR = {
    fatal: "#B23A48", destroyed: "#E08E2B", vmc: "#3E8BCB", imc: "#6A4C9C",
    axis: "#4A5A6A", text: "#0E1A26", grid: "#E3EBF2"
};

const fmt = d3.format(",");
const pct = v => (isFinite(v) ? (v * 100).toFixed(1) : "0.0") + "%";
const SMALL = 30;

let D = null;          // NTSB records
let weather = null;    // current conditions (live or entered)

const tooltip = d3.select("body").append("div").attr("class", "tooltip").style("display", "none");
function showTip(event, html) {
    tooltip.style("display", "block").html(html);
    const box = tooltip.node().getBoundingClientRect();
    let x = event.pageX + 14;
    if (x + box.width > window.scrollX + document.documentElement.clientWidth - 8) x = event.pageX - box.width - 14;
    tooltip.style("left", x + "px").style("top", (event.pageY - box.height - 10) + "px");
}
const hideTip = () => tooltip.style("display", "none");

// ---------- Risk rules: same as compute_rule_based_risk() in model_utils.py ----------
function riskRules(w) {
    const parts = [];
    let t = 0, tRule = "Between -5 °C and 30 °C";
    if (w.temp >= 40) { t = 25; tRule = "40 °C or hotter"; }
    else if (w.temp >= 30) { t = 15; tRule = "30 °C or hotter"; }
    else if (w.temp <= -5) { t = 10; tRule = "-5 °C or colder"; }
    parts.push(["Temperature", `${round1(w.temp)} °C`, tRule, t]);

    let h = 0, hRule = "Below 60%";
    if (w.humidity >= 80) { h = 20; hRule = "80% or more"; }
    else if (w.humidity >= 60) { h = 10; hRule = "60% or more"; }
    parts.push(["Humidity", `${Math.round(w.humidity)}%`, hRule, h]);

    let wd = 0, wRule = "Below 25 m/s";
    if (w.wind >= 40) { wd = 30; wRule = "40 m/s or more"; }
    else if (w.wind >= 25) { wd = 15; wRule = "25 m/s or more"; }
    parts.push(["Wind", `${round1(w.wind)} m/s`, wRule, wd]);

    let v = 0, vRule = "5,000 m or more";
    if (w.visibility < 2000) { v = 25; vRule = "Under 2,000 m"; }
    else if (w.visibility < 5000) { v = 10; vRule = "Under 5,000 m"; }
    parts.push(["Visibility", visText(w.visibility), vRule, v]);

    return { parts, score: Math.min(d3.sum(parts, p => p[3]), 100) };
}

const round1 = v => Math.round(v * 10) / 10;
const visText = v => (v >= 10000 ? "10+ km" : `${fmt(Math.round(v))} m`);

// Instrument-like conditions: under 3 statute miles (about 4,800 m), fog or thunderstorms
function flightRules(w) {
    return (w.visibility < 4800 || w.condition === "Fog" || w.condition === "Thunderstorm") ? "IMC" : "VMC";
}

// Open-Meteo weather codes to the condition names used in app.py
function conditionName(code) {
    if (code <= 1) return "Clear";
    if (code <= 3) return "Clouds";
    if (code <= 48) return "Fog";
    if (code <= 67 || (code >= 80 && code <= 82)) return "Rain";
    if (code <= 77 || code === 85 || code === 86) return "Snow";
    return "Thunderstorm";
}

// ---------- Setup ----------
d3.select("#city").selectAll("option").data(CITIES).join("option").attr("value", (d, i) => i).text(d => d[0]);
d3.select("#aircraft").selectAll("option").data(AIRCRAFT).join("option").attr("value", (d, i) => i).text(d => d.name);
d3.select("#aircraft").property("value", 3); // Plane

d3.select("#plan").on("submit", event => {
    event.preventDefault();
    if (d3.select("#manual").property("checked")) useManual();
    else getLiveWeather();
});
d3.select("#aircraft").on("change", render);
d3.select("#city").on("change", () => {
    if (!d3.select("#manual").property("checked")) getLiveWeather();
    else render();
});
d3.select("#manual").on("change", function () {
    d3.select("#manual-panel").attr("hidden", this.checked ? null : true);
    d3.select("#check-btn").text(this.checked ? "Update briefing" : "Check flight risk");
    if (this.checked) {
        // Start the sliders from the current weather, if there is any
        if (weather) {
            d3.select("#s-temp").property("value", Math.round(weather.temp));
            d3.select("#s-hum").property("value", Math.round(weather.humidity));
            d3.select("#s-wind").property("value", Math.round(weather.wind));
            d3.select("#s-vis").property("value", Math.min(10000, Math.round(weather.visibility)));
            d3.select("#s-cond").property("value", weather.condition);
        }
        useManual();
    } else {
        getLiveWeather();
    }
});
d3.selectAll("#s-temp, #s-hum, #s-wind, #s-vis").on("input", useManual);
d3.select("#s-cond").on("change", useManual);

function useManual() {
    weather = {
        temp: +d3.select("#s-temp").property("value"),
        humidity: +d3.select("#s-hum").property("value"),
        wind: +d3.select("#s-wind").property("value"),
        visibility: +d3.select("#s-vis").property("value"),
        condition: d3.select("#s-cond").property("value"),
        time: null,
        source: "Entered by you"
    };
    d3.select("#o-temp").text(`${weather.temp} °C`);
    d3.select("#o-hum").text(`${weather.humidity}%`);
    d3.select("#o-wind").text(`${weather.wind} m/s`);
    d3.select("#o-vis").text(visText(weather.visibility));
    d3.select("#live-status").text("Using the weather you entered.");
    render();
}

function getLiveWeather() {
    const [name, lat, lon] = CITIES[+d3.select("#city").property("value")];
    d3.select("#live-status").text(`Getting the current weather for ${name}…`);
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
        `&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,visibility&wind_speed_unit=ms&timezone=auto`;
    fetch(url)
        .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(data => {
            const c = data.current;
            weather = {
                temp: c.temperature_2m,
                humidity: c.relative_humidity_2m,
                wind: c.wind_speed_10m,
                visibility: c.visibility != null ? c.visibility : 10000,
                condition: conditionName(c.weather_code),
                time: c.time,
                source: "Live weather · Open-Meteo"
            };
            d3.select("#live-status").text(`Live weather for ${name} loaded.`);
            render();
        })
        .catch(() => {
            d3.select("#live-status").text("Live weather isn't available right now. Tick \"Enter the weather myself\" to set the conditions.");
        });
}

// ---------- Render the briefing ----------
function render() {
    if (!weather) return;
    const city = CITIES[+d3.select("#city").property("value")][0];
    const ac = AIRCRAFT[+d3.select("#aircraft").property("value")];
    const rules = flightRules(weather);
    const { parts, score } = riskRules(weather);

    d3.select("#p-source").text(weather.source);
    d3.select("#p-city").text(city);
    d3.select("#p-aircraft").text(ac.name);
    d3.select("#p-time").text(weather.time ? weather.time.replace("T", " ") : "Not live");
    d3.select("#p-cond").text(weather.condition);
    d3.select("#p-temp").text(`${round1(weather.temp)} °C`);
    d3.select("#p-hum").text(`${Math.round(weather.humidity)}%`);
    d3.select("#p-wind").text(`${round1(weather.wind)} m/s`);
    d3.select("#p-vis").text(visText(weather.visibility));
    d3.select("#p-rules").text(rules === "IMC" ? "Instrument (IMC)" : "Visual (VMC)");

    d3.select("#score").text(score);
    d3.select("#needle").style("left", score + "%");
    const band = score >= 60 ? ["High", "#B23A48", "#FFFFFF"] : score >= 30 ? ["Moderate", "#E08E2B", "#000000"] : ["Low", "#3E8BCB", "#000000"];
    d3.select("#band").text(band[0] + " risk").style("background", band[1]).style("color", band[2]);

    d3.select("#breakdown").selectAll("tr").data(parts).join("tr")
        .attr("class", p => p[3] ? "hit" : null)
        .html(p => `<td>${p[0]}</td><td class="now">${p[1]}</td><td>${p[2]}</td><td class="num">${p[3] ? "+" + p[3] : "0"}</td>`);
    d3.select("#total").text(score);

    if (D) {
        renderHistory(ac, rules);
        renderCompare(ac);
    }
}

// ---------- Historical context ----------
function groupStats(ac) {
    const codes = ac.engines ? ac.engines.map(e => D.labels.engine.indexOf(e)) : null;
    const vmc = D.labels.weather.indexOf("VMC"), imc = D.labels.weather.indexOf("IMC");
    const s = { VMC: { n: 0, fatal: 0, destroyed: 0 }, IMC: { n: 0, fatal: 0, destroyed: 0 }, all: 0 };
    for (let i = 0; i < D.count; i++) {
        if (codes && !codes.includes(D.engine[i])) continue;
        s.all++;
        const key = D.weather[i] === vmc ? "VMC" : D.weather[i] === imc ? "IMC" : null;
        if (!key) continue;
        s[key].n++;
        if (D.fatal[i] > 0) s[key].fatal++;
        if (D.damage[i] === 0) s[key].destroyed++;
    }
    return s;
}

function renderHistory(ac, rules) {
    const s = groupStats(ac);
    const now = s[rules], other = s[rules === "IMC" ? "VMC" : "IMC"];
    d3.select("#hist-note").text(`Accidents involving ${ac.group}: ${fmt(s.all)} in the records.`);

    d3.select("#history").html(
        `<div><span class="big">${fmt(now.n)}</span><span class="lbl">accidents in ${rules}</span></div>` +
        `<div><span class="big" style="color:${COLOR.fatal}">${pct(now.fatal / now.n)}</span><span class="lbl">were fatal</span></div>` +
        `<div><span class="big">${pct(now.destroyed / now.n)}</span><span class="lbl">destroyed the aircraft</span></div>`);

    // Small chart: fatal and destroyed rates in VMC and IMC
    const sel = "#chart-hist";
    const data = ["VMC", "IMC"].map(k => ({ k, ...s[k] })).filter(d => d.n > 0);
    d3.select(sel).html("");
    const w = Math.max(280, d3.select(sel).node().clientWidth);
    const rowH = 62, m = { top: 4, right: 64, bottom: 24, left: 100 };
    const h = m.top + m.bottom + data.length * rowH, iw = w - m.left - m.right;
    const svg = d3.select(sel).append("svg").attr("viewBox", `0 0 ${w} ${h}`)
        .attr("role", "img").attr("aria-label", `Fatal and destroyed rates for ${ac.group} in visual and instrument conditions`);
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);
    const x = d3.scaleLinear().domain([0, 1]).range([0, iw]);
    g.append("g").attr("transform", `translate(0,${data.length * rowH})`)
        .call(d3.axisBottom(x).ticks(w < 420 ? 2 : 4).tickFormat(d3.format(".0%")))
        .call(a => a.selectAll("text").attr("fill", COLOR.axis).attr("font-size", 12))
        .call(a => a.selectAll("path,line").attr("stroke", "#9DB6CC"));

    const row = g.selectAll(".hrow").data(data).join("g")
        .attr("transform", (d, i) => `translate(0,${i * rowH})`);
    row.append("rect").attr("x", -m.left).attr("y", 2).attr("width", w).attr("height", rowH - 4)
        .attr("fill", d => d.k === rules ? "#DCEBF7" : "#FFFFFF");
    row.append("text").attr("x", -10).attr("y", rowH / 2 - 6).attr("text-anchor", "end").attr("font-weight", 600).attr("fill", COLOR.text)
        .text(d => d.k + (d.k === rules ? " (now)" : ""));
    row.append("text").attr("x", -10).attr("y", rowH / 2 + 12).attr("text-anchor", "end").attr("font-size", 12).attr("fill", COLOR.axis)
        .text(d => fmt(d.n) + (d.n < SMALL ? " · small" : ""));
    [["fatal", COLOR.fatal, 10], ["destroyed", COLOR.destroyed, 32]].forEach(([key, col, yOff]) => {
        row.append("rect").attr("y", yOff).attr("height", 18).attr("fill", col).attr("width", d => x(d[key] / d.n))
            .on("mousemove", (e, d) => showTip(e, `<strong>${d.k}</strong><br>${fmt(d[key])} of ${fmt(d.n)} accidents ${key === "fatal" ? "were fatal" : "destroyed the aircraft"}`))
            .on("mouseleave", hideTip);
        row.append("text").attr("y", yOff + 14).attr("x", d => x(d[key] / d.n) + 6).attr("font-size", 13).attr("font-weight", 600)
            .attr("fill", COLOR.text).text(d => pct(d[key] / d.n));
    });

    let text;
    if (now.n < SMALL) {
        text = `Only ${fmt(now.n)} accidents in the records match ${ac.group} in ${rules}, so treat these figures with caution.`;
    } else if (other.n >= SMALL) {
        const a = now.fatal / now.n, b = other.fatal / other.n;
        const nowName = rules === "IMC" ? "instrument conditions, like now," : "visual conditions, like now,";
        const otherName = rules === "IMC" ? "visual conditions" : "instrument conditions";
        text = a >= b
            ? `For ${ac.group}, an accident in ${nowName} was ${(a / b).toFixed(1)} times as likely to be fatal as one in ${otherName} (${pct(a)} against ${pct(b)}).`
            : `For ${ac.group}, accidents in ${nowName} were less often fatal than in ${otherName} (${pct(a)} against ${pct(b)}).`;
    } else {
        text = `${pct(now.fatal / now.n)} of accidents involving ${ac.group} in ${rules} were fatal.`;
    }
    d3.select("#hist-insight").text(text);
}

// ---------- Compare all aircraft groups ----------
function renderCompare(selected) {
    const sel = "#chart-compare";
    const data = AIRCRAFT.map((ac, i) => ({ ac, i, ...groupStats(ac) }));
    d3.select(sel).html("");
    const w = Math.max(300, d3.select(sel).node().clientWidth);
    const narrow = w < 560;
    const rowH = 52, m = { top: 4, right: narrow ? 96 : 120, bottom: 26, left: narrow ? 112 : 150 };
    const h = m.top + m.bottom + data.length * rowH, iw = w - m.left - m.right;
    const svg = d3.select(sel).append("svg").attr("viewBox", `0 0 ${w} ${h}`)
        .attr("role", "img").attr("aria-label", "Fatal accident rates by aircraft group in visual and instrument conditions");
    const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);
    const x = d3.scaleLinear().domain([0, 1]).range([0, iw]);

    g.append("g").call(d3.axisBottom(x).ticks(narrow ? 2 : 5).tickSize(data.length * rowH).tickFormat(""))
        .call(a => a.select(".domain").remove()).call(a => a.selectAll("line").attr("stroke", COLOR.grid));
    g.append("g").attr("transform", `translate(0,${data.length * rowH})`)
        .call(d3.axisBottom(x).ticks(narrow ? 2 : 5).tickFormat(d3.format(".0%")))
        .call(a => a.selectAll("text").attr("fill", COLOR.axis).attr("font-size", 12))
        .call(a => a.selectAll("path,line").attr("stroke", "#9DB6CC"));

    const row = g.selectAll(".crow").data(data).join("g")
        .attr("class", "crow clickable")
        .attr("transform", (d, i) => `translate(0,${i * rowH})`)
        .on("click", (e, d) => { d3.select("#aircraft").property("value", d.i); render(); });
    row.append("rect").attr("x", -m.left).attr("y", 1).attr("width", w).attr("height", rowH - 2)
        .attr("fill", d => d.ac === selected ? "#DCEBF7" : "#FFFFFF");
    row.append("text").attr("x", -10).attr("y", rowH / 2).attr("dy", "0.35em").attr("text-anchor", "end")
        .attr("font-weight", d => d.ac === selected ? 700 : 500).attr("font-size", 14).attr("fill", COLOR.text).text(d => d.ac.name);

    [["VMC", COLOR.vmc, 8], ["IMC", COLOR.imc, 27]].forEach(([k, col, yOff]) => {
        row.append("rect").attr("y", yOff).attr("height", 16).attr("fill", col)
            .attr("width", d => d[k].n ? x(d[k].fatal / d[k].n) : 0)
            .on("mousemove", (e, d) => showTip(e, `<strong>${d.ac.name}</strong> · ${k}<br>${fmt(d[k].fatal)} of ${fmt(d[k].n)} accidents were fatal (${pct(d[k].fatal / d[k].n)})<br>Group: ${d.ac.group}`))
            .on("mouseleave", hideTip);
        row.append("text").attr("y", yOff + 12).attr("x", d => (d[k].n ? x(d[k].fatal / d[k].n) : 0) + 6)
            .attr("font-size", 12).attr("fill", COLOR.text)
            .text(d => d[k].n ? pct(d[k].fatal / d[k].n) + (d[k].n < SMALL ? (narrow ? " small" : " (small sample)") : "") : "no records");
    });
}

// ---------- Load the records, then show the default briefing ----------
d3.json("Accidents.json").then(data => {
    D = data;
    render();
}).catch(err => {
    console.error(err);
    d3.select("#hist-note").text("The accident records couldn't load. Make sure Accidents.json is in the repository, then refresh.");
});

getLiveWeather();

window.addEventListener("resize", debounce(render, 150));
function debounce(fn, ms) { let t; return () => { clearTimeout(t); t = setTimeout(fn, ms); }; }

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
