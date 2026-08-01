const $ = s => document.querySelector(s);

// In-flight request counter drives the busy bar. This helps with slow API
// calls -- 100k Monte Carlo iterations is a real wait -- but it cannot help
// with a cold start, since that stalls the HTML document before any of this
// script exists.
let INFLIGHT = 0;
function busy(delta) {
  INFLIGHT = Math.max(0, INFLIGHT + delta);
  const el = document.getElementById('busy');
  if (el) el.classList.toggle('on', INFLIGHT > 0);
}
const api = p => {
  busy(1);
  return fetch(p)
    .then(r => {
      if (!r.ok) throw new Error(`${p} -> ${r.status}`);
      return r.json();
    })
    .finally(() => busy(-1));
};
// Plotly comes from a CDN, so a public deployment depends on that host being
// reachable. If it is not, stub it rather than letting every chart-bearing
// view die on "Plotly is not defined" -- the numbers all exist in the tables
// and the API regardless, so the page stays useful.
if (typeof Plotly === 'undefined') {
  window.Plotly = {
    newPlot(target) {
      const el = typeof target === 'string'
        ? document.getElementById(target) : target;
      if (el) {
        el.innerHTML = '<p class="note">Charts could not load — Plotly is ' +
          'served from a CDN that is unreachable right now. Every figure is ' +
          'still available in the tables below and from the API.</p>';
        el.style.height = 'auto';
      }
      return Promise.resolve();
    },
    relayout() { return Promise.resolve(); },
  };
}

// Chart colours are read from the CSS custom properties at draw time, so a
// theme change re-colours every chart by re-running the view inits -- there
// is exactly one place a colour is defined, and it is the stylesheet.
const CHVARS = {
  stamp: '--stamp', stampSoft: '--stamp-soft', measured: '--measured',
  study: '--study', industry: '--industry', estimate: '--estimate',
  bad: '--bad', faint: '--faint', dim: '--dim', line: '--line',
  ink: '--ink', barMuted: '--bar-muted', barRecede: '--bar-recede',
  amber: '--amber', amber2: '--amber2', amberBright: '--amber-bright',
  scaleLo: '--scale-lo', scaleHi: '--scale-hi',
  grey: '--grey', grey2: '--grey2', brown: '--brown',
};
const CH = new Proxy({}, { get: (_, k) =>
  getComputedStyle(document.documentElement)
    .getPropertyValue(CHVARS[k]).trim() });

let PLOT;
function mkPlot() {
  PLOT = {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: CH.dim, size: 11 },
    margin: { l: 50, r: 16, t: 30, b: 40 },
    xaxis: { gridcolor: CH.line, zerolinecolor: CH.line },
    yaxis: { gridcolor: CH.line, zerolinecolor: CH.line },
  };
}
mkPlot();

function applyTheme() {
  const mode = localStorage.getItem('ccw-theme') ||
    (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.dataset.theme = mode;
  const t = document.getElementById('theme-toggle');
  if (t) {
    t.textContent = mode === 'dark' ? 'Light mode' : 'Dark mode';
    t.setAttribute('aria-pressed', mode === 'dark');
  }
  mkPlot();
  return mode;
}
// Redraw whatever view is showing; the others rebuild when opened.
function redrawTheme() {
  loaded = {};
  const cur = document.querySelector('nav button.on');
  if (cur && cur.dataset.v !== 'calc') load(cur.dataset.v);
}
document.getElementById('theme-toggle').onclick = () => {
  const now = document.documentElement.dataset.theme === 'dark'
    ? 'light' : 'dark';
  localStorage.setItem('ccw-theme', now);
  applyTheme();
  redrawTheme();
};
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (!localStorage.getItem('ccw-theme')) { applyTheme(); redrawTheme(); }
});
applyTheme();
const CFG = { displayModeBar: false, responsive: true };
let META = null, loaded = {};

// Show enough decimals to keep a near-ceiling value visibly below it.
function fmtDistinct(v, ceil) {
  // Same-day eggs actually REACH the ceiling -- a hen lays at most one a day,
  // so twelve eggs in a day is exactly twelve hens. Printing "12.000000"
  // implies a limit being approached when it has been hit, which is the
  // opposite of the truth. Wings approach and never arrive; eggs arrive.
  if (ceil - v <= 5e-7) return String(+v.toFixed(2));
  for (const p of [2,3,4,5,6]) {
    const s = v.toFixed(p);
    if (parseFloat(s) < ceil) return s;
  }
  return v.toFixed(6);
}
const badge = c => c ? `<span class="badge b-${c}">${c}</span>` : '';

// ---- navigation
document.querySelectorAll('nav button').forEach(b => {
  b.onclick = () => {
    document.querySelectorAll('nav button').forEach(x => x.classList.remove('on'));
    document.querySelectorAll('.view').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    $('#v-' + b.dataset.v).classList.add('on');
    load(b.dataset.v);
  };
});

// ---- calculator
let calcSeq = 0;

async function calc() {
  const mine = ++calcSeq;
  const q = new URLSearchParams({
    count: $('#count').value || 12,
    product: $('#product').value || 'whole_wing',
    chain: $('#chain').value,
    pieces: $('#pieces').checked,
    include_mortality: $('#mort').checked,
  });
  // Only meaningful for recurring products, and the server ignores it for
  // the rest -- but sending it regardless would put a misleading window in
  // the query string for wings.
  if (!$('#window-wrap').hidden && $('#window-days').value)
    q.set('window_days', $('#window-days').value);
  const d = await api('/api/calculate?' + q);
  if (mine !== calcSeq) return;     // superseded by a newer request
  const a = d.answer, plural = d.question.individual_plural;

  $('#hl').textContent = fmtDistinct(a.distinct, a.ceiling);
  $('#hl-label').textContent = 'different ' + plural + ' on your plate';

  // The band runs floor..ceiling, so it must use the HARD floor. `a.floor` is
  // the expected requirement, which for same-day eggs is 15.21 against a
  // ceiling of 12 -- above the top of its own scale, which made the band
  // meaningless and the label wrong.
  //
  // The scale counts INDIVIDUALS, so its floor is a whole one. hard_floor is
  // continuous and for a dozen eggs gathered over a year it is 0.033 -- a
  // third of a hen's daily output, which is a true statement about laying
  // rate and a false one about how many hens are on your plate. The prose
  // below already rounds it up for exactly this reason; the band printing
  // "floor 0.03 hens" directly above that prose contradicted it.
  const bandFloor = a.hard_floor != null
    ? Math.max(1, Math.ceil(a.hard_floor - 1e-9)) : a.floor;
  const span = a.ceiling - bandFloor;
  const pct = span > 0 ? ((a.distinct - bandFloor) / span) * 100 : 100;
  $('#bandfill').style.width = Math.max(1, Math.min(100, pct)) + '%';
  $('#band-lo').textContent = 'floor ' + (+bandFloor.toFixed(2)) + ' '
    + (bandFloor === 1 ? d.question.individual_noun : plural);
  $('#band-hi').textContent = span <= 1e-9
    // Floor and ceiling coincide: there is no band left for the supply chain
    // to move anything within, and saying so is the whole point of eggs.
    ? 'ceiling ' + (+a.ceiling.toFixed(2)) + ' — floor meets ceiling'
    : 'ceiling ' + (+a.ceiling.toFixed(2));

  let fl;
  // What this species calls its rate, and why its ceiling is physiology,
  // both out of the corpus. Hardcoded here as 'laying rate' and 'a hen lays
  // at most one egg a day', they described a maple tree as a bird.
  const rateLabel = a.rate_label || 'production rate';
  const w = a.window_days;
  const when = w === 1 ? 'in a single day' : `over ${w} days`;
  if (a.hard_floor != null) {
    // Recurring products carry two floors and quoting one alone misleads.
    // hard_floor is physiology; floor is what you actually need, because a
    // hen does not lay every day.
    const birds = Math.ceil(a.hard_floor - 1e-9);
    fl = `Gathered ${when}, that took <b>at least ${birds}
      ${birds === 1 ? d.question.individual_noun : plural}</b>`;
    fl += a.cap_note ? ` — ${a.cap_note}.` : '.';
    fl += a.floor >= 1
      ? ` At the real ${rateLabel} you would need about
          <b>${a.floor.toFixed(2)}</b> ${plural} to count on it.`
      : ` That is about <b>${(a.floor * 100).toFixed(0)}%</b> of one
          ${d.question.individual_noun}'s output over that window.`;
  } else if (w != null) {
    // Recurring with no per-day ceiling recorded — a maple. One floor, and
    // it is a yield floor: what the average individual turns out, never a
    // physiological limit. Claiming the harder one is what this replaced.
    fl = `Gathered ${when}, that took <b>at least
      ${+a.floor.toFixed(2)} ${plural}</b> — that is a ${rateLabel} floor,
      not a physiological one: no per-day ceiling is recorded for a
      ${d.question.individual_noun}.`;
  } else {
    fl = `It took <b>at least ${+a.floor.toFixed(2)} ${plural}</b> — that
      part is arithmetic, not estimation.`;
    if (a.required > a.floor + 1e-9)
      fl += ` Accounting for every loss from the farm to the fryer,
        <b>${a.required.toFixed(2)}</b> ${plural} had to enter the system.`;
  }
  if (d.question.segments_per_unit)
    fl = `${d.question.count} pieces is ${(+d.question.units.toFixed(2))}
      whole wings. ` + fl;
  $('#floorline').innerHTML = fl;

  $('#trace').innerHTML = d.trace.map(s => {
    const counts = s.kind !== 'loss' || !/does not change/.test(s.explanation);
    const src = d.sources[s.source];
    return `<div class="step ${counts ? 'count' : ''}">
      <h4>${s.label} ${badge(s.confidence)}</h4>
      <p>${s.explanation}</p>
      ${src ? `<div class="cite">${src.title} — ${src.publisher}
        ${src.url ? `· <a href="${src.url}" target="_blank" rel="noopener">source</a>` : ''}
      </div>` : ''}
    </div>`;
  }).join('');

  // The closing paragraph is the chain's own floor_note, never text written
  // here. Hardcoded, it was wing prose -- an egg query was told about a
  // cut-up line and "the instant the wings leave the bird". The CLI has read
  // this field since it was added; this page had kept its own stale copy.
  $('#mixnotes').innerHTML = (d.mixing_notes.length || d.floor_note)
    ? `<div class="step count"><h4>Why not exactly the floor?</h4>
       ${d.mixing_notes.map(n => `<p>• ${n}</p>`).join('')}
       ${d.floor_note
         ? `<p style="margin-top:8px">${d.floor_note}</p>` : ''}</div>` : '';

  const f = await api('/api/facts?placement=result&limit=1');
  if (mine !== calcSeq) return;
  if (f.facts.length) {
    const x = f.facts[0];
    $('#resultfact').innerHTML =
      `<div class="fact"><h4>${x.headline}</h4><p>${x.body}</p>
       <div class="cite">${x.source_title} — ${x.publisher}</div></div>`;
  }
}

// ---- scientific mode
const CONF_COLOUR = () => ({
  measured: CH.measured, derived: CH.measured, study: CH.study,
  industry: CH.industry, estimate: CH.estimate,
});

// Requests are not guaranteed to resolve in the order they were sent, and a
// 100,000-iteration run can easily finish after a 2,000-iteration one fired
// later. Stamp each call and discard any response that has been superseded,
// otherwise changing two controls quickly renders a stale answer.
let sciSeq = 0;

async function sci() {
  const mine = ++sciSeq;
  const conf = $('#s-conf').value;
  const q = new URLSearchParams({
    count: $('#s-count').value || 12,
    chain: $('#s-chain').value,
    confidence_level: $('#s-ci').value,
    iterations: $('#s-iter').value,
  });
  if (conf) q.set('min_confidence', conf);

  const d = await api('/api/scientific?' + q);
  if (mine !== sciSeq) return;      // superseded by a newer request
  const a = d.answer, pct = Math.round(d.question.confidence_level * 100);

  $('#s-req').textContent = a.required.toFixed(2);
  $('#s-req-ci').textContent =
    `${pct}% interval  ${a.required_lo.toFixed(2)} – ${a.required_hi.toFixed(2)}`;
  $('#s-dist').textContent = fmtDistinct(a.distinct, a.ceiling);
  $('#s-dist-ci').textContent =
    `${pct}% interval  ${fmtDistinct(a.distinct_lo, a.ceiling)} – ` +
    `${fmtDistinct(a.distinct_hi, a.ceiling)}`;

  $('#s-excluded').innerHTML = a.excluded_stages.length
    ? `<div class="step"><h4>${a.excluded_stages.length} stage(s) excluded
       ${badge('estimate')}</h4>
       <p>Below the evidence grade you selected, so they are not contributing
       to the numbers above: <b>${a.excluded_stages.join(', ')}</b>.
       The result is therefore an <em>underestimate</em> — these are real
       losses we simply cannot cite yet.</p></div>`
    : '';

  // Tornado, sorted by swing, coloured by evidence grade.
  const t = d.tornado.filter(x => x.swing > 1e-9).reverse();
  Plotly.newPlot('s-tornado', [{
    type: 'bar', orientation: 'h',
    x: t.map(x => x.swing), y: t.map(x => x.label),
    marker: { color: t.map(x => CONF_COLOUR()[x.confidence] || CH.faint) },
    customdata: t.map(x => [x.share, x.confidence, x.low, x.high]),
    hovertemplate: '%{y}<br>swing %{x:.4f} chickens<br>' +
      '%{customdata[0]:.1%} of total uncertainty<br>' +
      'grade: %{customdata[1]}<extra></extra>',
  }], Object.assign({}, PLOT, {
    margin: { l: 210, r: 20, t: 10, b: 44 },
    xaxis: Object.assign({}, PLOT.xaxis, { title: 'swing in chickens required' }),
  }), CFG);

  // Monte Carlo histogram with the interval marked.
  const h = d.required_hist;
  Plotly.newPlot('s-hist', [{
    type: 'bar', x: h.centres, y: h.counts,
    marker: { color: CH.stamp }, name: 'draws',
    hovertemplate: '%{x:.3f} chickens<br>%{y:,} draws<extra></extra>',
  }], Object.assign({}, PLOT, {
    bargap: 0.02,
    xaxis: Object.assign({}, PLOT.xaxis, { title: 'chickens required' }),
    yaxis: Object.assign({}, PLOT.yaxis, { title: 'draws' }),
    shapes: [
      { type: 'line', x0: a.required_lo, x1: a.required_lo, yref: 'paper',
        y0: 0, y1: 1, line: { color: CH.stampSoft, width: 2, dash: 'dash' } },
      { type: 'line', x0: a.required_hi, x1: a.required_hi, yref: 'paper',
        y0: 0, y1: 1, line: { color: CH.stampSoft, width: 2, dash: 'dash' } },
      { type: 'line', x0: a.required, x1: a.required, yref: 'paper',
        y0: 0, y1: 1, line: { color: CH.ink, width: 2 } },
    ],
    annotations: [
      { x: a.required, yref: 'paper', y: 1.06, showarrow: false,
        text: `mean ${a.required.toFixed(2)}`, font: { color: CH.ink } },
      { x: a.required_lo, yref: 'paper', y: 1.06, showarrow: false,
        text: a.required_lo.toFixed(2), font: { color: CH.stampSoft } },
      { x: a.required_hi, yref: 'paper', y: 1.06, showarrow: false,
        text: a.required_hi.toFixed(2), font: { color: CH.stampSoft } },
    ],
  }), CFG);

  // Waterfall from floor to requirement.
  const w = d.waterfall;
  Plotly.newPlot('s-waterfall', [{
    type: 'waterfall', orientation: 'v',
    measure: ['absolute'].concat(w.map(() => 'relative')),
    x: ['Anatomical floor'].concat(w.map(s => s.label)),
    y: [a.floor].concat(w.map(s => s.delta)),
    connector: { line: { color: CH.line } },
    increasing: { marker: { color: CH.stampSoft } },
    totals: { marker: { color: CH.stamp } },
    hovertemplate: '%{x}<br>%{y:+.4f} chickens<extra></extra>',
  }], Object.assign({}, PLOT, {
    margin: { l: 50, r: 16, t: 10, b: 110 },
    xaxis: Object.assign({}, PLOT.xaxis, { tickangle: -35 }),
    yaxis: Object.assign({}, PLOT.yaxis, { title: 'chickens' }),
  }), CFG);

  const modeEnd = w.length ? w[w.length - 1].to : a.floor;
  $('#s-waterfall-gap').textContent =
    `Mode path ends at ${modeEnd.toFixed(3)}; Monte Carlo mean is ` +
    `${a.required.toFixed(3)} — a gap of ${(a.required - modeEnd).toFixed(3)} ` +
    `chickens from band asymmetry.`;

  // Evidence mix across count-affecting stages.
  const keys = Object.keys(d.evidence_mix);
  Plotly.newPlot('s-evidence', [{
    type: 'bar', orientation: 'h', x: keys.map(k => d.evidence_mix[k]),
    y: keys, marker: { color: keys.map(k => CONF_COLOUR()[k] || CH.faint) },
    hovertemplate: '%{y}: %{x} stage(s)<extra></extra>',
  }], Object.assign({}, PLOT, {
    margin: { l: 90, r: 20, t: 10, b: 40 },
    xaxis: Object.assign({}, PLOT.xaxis, { title: 'count-affecting stages',
      dtick: 1 }),
  }), CFG);
}

function initSci() {
  $('#s-chain').innerHTML = META.chains.map(c =>
    `<option value="${c.slug}" ${c.is_default ? 'selected' : ''}>${c.label}</option>`
  ).join('');
  ['s-count','s-chain','s-ci','s-conf','s-iter'].forEach(id => {
    $('#' + id).addEventListener('change', sci);
  });
  sci();
}

// ---- mixing simulator
let CURVE = null;
async function initMix() {
  CURVE = await api('/api/mixing-curve?draw=12');
  const xs = CURVE.points.map(p => p.pool);
  const ys = CURVE.points.map(p => p.distinct);
  Plotly.newPlot('mixchart', [
    { x: xs, y: ys, mode: 'lines', line: { color: CH.stamp, width: 3 },
      name: 'distinct chickens', hovertemplate:
      '%{x:,} chickens in pool<br>%{y:.4f} distinct<extra></extra>' },
    { x: [xs[0], xs[xs.length-1]], y: [CURVE.ceiling, CURVE.ceiling],
      mode: 'lines', line: { color: CH.faint, dash: 'dot', width: 1 },
      name: 'ceiling (12)', hoverinfo: 'skip' },
    { x: [xs[0], xs[xs.length-1]], y: [CURVE.floor, CURVE.floor],
      mode: 'lines', line: { color: CH.faint, dash: 'dot', width: 1 },
      name: 'floor (6)', hoverinfo: 'skip' },
  ], Object.assign({}, PLOT, {
      xaxis: Object.assign({}, PLOT.xaxis, { type: 'log',
        title: 'chickens in the pool (log scale)' }),
      yaxis: Object.assign({}, PLOT.yaxis, { title: 'distinct chickens',
        range: [5.5, 12.5] }),
      showlegend: false,
    }), CFG);
  $('#mixnote').textContent = CURVE.note;
  $('#pool').max = CURVE.points.length - 1;
  mixMove();
}
function mixMove() {
  if (!CURVE) return;
  const p = CURVE.points[+$('#pool').value];
  $('#poollabel').textContent = p.pool.toLocaleString();
  $('#mixout').textContent = fmtDistinct(p.distinct, CURVE.ceiling);
  Plotly.relayout('mixchart', {
    shapes: [{ type: 'line', x0: p.pool, x1: p.pool, y0: 5.5, y1: 12.5,
               line: { color: CH.stampSoft, width: 2 } }]
  });
}
$('#pool').oninput = mixMove;

// ---- states
const ABBR = {Alabama:'AL',Arkansas:'AR',Delaware:'DE',Georgia:'GA',
  Illinois:'IL',Iowa:'IA',Kentucky:'KY',Louisiana:'LA',Maryland:'MD',
  Mississippi:'MS',Missouri:'MO','New Jersey':'NJ','New York':'NY',
  'North Carolina':'NC',Ohio:'OH',Oklahoma:'OK',Pennsylvania:'PA',
  'South Carolina':'SC',Tennessee:'TN',Texas:'TX',Vermont:'VT',Virginia:'VA'};

async function initStates() {
  const d = await api('/api/states');
  const rows = d.regions.filter(r => ABBR[r.region]);
  Plotly.newPlot('statemap', [{
    type: 'choropleth', locationmode: 'USA-states',
    locations: rows.map(r => ABBR[r.region]),
    z: rows.map(r => r.avg_size),
    text: rows.map(r => `${r.region}<br>${r.avg_size} lb<br>${r.program || ''}`),
    hovertemplate: '%{text}<extra></extra>',
    colorscale: [[0, CH.scaleLo], [0.5, CH.amber], [1, CH.scaleHi]],
    colorbar: { title: 'lb', thickness: 12 },
  }], Object.assign({}, PLOT, {
    geo: { scope: 'usa', bgcolor: 'rgba(0,0,0,0)',
           lakecolor: 'rgba(0,0,0,0)', subunitcolor: CH.line },
  }), CFG);

  $('#statetable').innerHTML = `<table><tr><th>State</th>
    <th class="num">Live weight</th><th>Program</th>
    <th class="num">Production</th></tr>` +
    d.regions.filter(r => r.region !== 'United States').map(r =>
      `<tr><td>${r.region}</td><td class="num">${r.avg_size} lb</td>
       <td>${r.program || '—'}</td>
       <td class="num">${r.volume ? (r.volume/1000).toLocaleString(
          undefined,{maximumFractionDigits:0}) + ' M lb' : '—'}</td></tr>`
    ).join('') + '</table>';
}

// ---- by country
//
// The capability labels are keyed off the API's `answers` map rather than
// written here, so a country can never be shown a question its statistics
// cannot answer. That is the whole point of the view: Israel publishes tonnage,
// value and 55 districts, and cannot say how many chickens -- head slaughtered
// is in none of the CBS tables and no Israeli average bird weight is published
// either, so there is no denominator. Naming the gap is more honest than
// filling it with a US figure.
const CAN_LABEL = {
  head_slaughtered: 'how many chickens',
  national_output:  'national output',
  subnational:      'subnational detail',
  per_capita:       'per-capita consumption',
};

// Rendered as tonnes/value/head, each on its own chart. Countries are never
// put on a shared axis: the US answers head slaughtered and not national
// output, Israel the exact inverse, so a side-by-side would invite a
// comparison the data cannot support.
const MEASURE = () => ({
  meat_output:  { title: 'Broiler meat output', colour: CH.amber2 },
  head_slaughtered: { title: 'Birds slaughtered per year',
                      colour: CH.measured },
  output_value: { title: 'Output value',        colour: CH.faint },
  inventory_eoy:{ title: 'Flock, end of year',  colour: CH.amberBright },
});

let COUNTRIES = null;

// The evidence filter, held here because it survives a country change: a
// reader who asked for government figures only should not have that quietly
// undone by clicking a different country.
let C_GRADE = '';
let C_ISO = null;

async function initCountry() {
  COUNTRIES = (await api('/api/countries')).countries;
  document.querySelectorAll('input[name="c-grade"]').forEach(r => {
    r.onchange = () => { C_GRADE = r.value; if (C_ISO) showCountry(C_ISO); };
  });
  const box = $('#c-picker');
  box.innerHTML = '';
  COUNTRIES.forEach(c => {
    const b = document.createElement('button');
    b.textContent = c.name;
    b.disabled = !c.has_data;
    if (!c.has_data) b.title = 'No statistics loaded for this country yet';
    b.onclick = () => {
      box.querySelectorAll('button').forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      showCountry(c.iso3);
    };
    box.appendChild(b);
  });
  // Default to the first country that actually has data, so the view is never
  // blank on arrival.
  const first = box.querySelector('button:not([disabled])');
  if (first) first.click();
  else $('#c-answers').innerHTML =
    '<p class="muted">No country has statistics loaded yet.</p>';
}

async function showCountry(iso3) {
  C_ISO = iso3;
  const meta = COUNTRIES.find(c => c.iso3 === iso3) || {};
  const a = meta.answers || {};

  // /api/output/{iso3} 404s for a country with no output_stat_year rows, and
  // that is a legitimate state rather than an error: the US enumerates head
  // slaughtered and 50 states and publishes no national output series at all,
  // so it answers this question through "By state" instead.
  //
  // Letting the throw propagate is what a first pass did, and because the
  // rejection was swallowed by the click handler the United States button
  // simply did nothing when pressed -- no error, no change, no clue. Absence
  // of data has to render as absence, not as a dead control.
  let d = { national: [], regional: [], suppressed_regions: 0,
            excluded: [], derived_weight: [] };
  try {
    d = await api(`/api/output/${iso3}` +
                  (C_GRADE ? `?min_confidence=${C_GRADE}` : ''));
  } catch (err) {
    if (!String(err.message || '').includes('404')) throw err;
  }

  // ---- what this country can and cannot answer
  //
  // Every word here is derived from the API's `answers` map. Nothing is
  // asserted, deliberately: an earlier draft of this view hardcoded "Israel
  // cannot answer how many chickens", which was true when it was typed and
  // false a few hours later once an industry-grade head figure was sourced.
  // A UI that states a coverage fact in prose will eventually contradict the
  // corpus it is describing.
  // The capability map is unfiltered, so under a filter it would contradict the
  // panel below it -- claiming Israel can answer the count question on a view
  // that has just dropped the only figure that answers it.
  const can = k => (C_GRADE === 'measured' && k === 'head_slaughtered')
    ? a.head_slaughtered_measured : a[k];

  const items = Object.keys(CAN_LABEL).map(k => {
    // The count question is the one where a bare yes/no misleads. "We have a
    // bird count" means something very different when a federal agency
    // enumerated it than when a trade association secretary said it in an
    // interview, so the grade rides along with it.
    const grade = k === 'head_slaughtered' && can(k) && a.head_slaughtered_grade
      ? ` <span class="note">(${a.head_slaughtered_grade})</span>` : '';
    return `<li class="${can(k) ? 'yes' : 'no'}">${CAN_LABEL[k]}${grade}</li>`;
  }).join('');

  let calcNote = '';
  if (C_GRADE === 'measured' && a.head_slaughtered
      && !a.head_slaughtered_measured) {
    calcNote = `<p class="note warn">On government figures alone ${meta.name}
      cannot answer this project's headline question. It has a bird count, but
      not one anybody enumerated — switch back to all evidence to see it, and
      read it as what it is.</p>`;
  } else if (!a.head_slaughtered) {
    calcNote = `<p class="note warn">${meta.name} cannot answer this project's
      headline question from its own statistics. Head slaughtered per year is
      not published, and without it or an average bird weight there is no way
      to turn tonnes into birds. Borrowing another country's figure would dress
      a foreign assumption up as a local one.</p>`;
  } else if (!a.head_slaughtered_measured) {
    calcNote = `<p class="note warn">${meta.name} answers the count question on
      <strong>${a.head_slaughtered_grade || 'weaker'}</strong> evidence rather
      than a government enumeration — so it is a real answer, and not the same
      kind of answer the US figure is. Read it as the order of magnitude it is,
      not as a census.</p>`;
  }

  // The count answer itself, and the weight it implies. Under the
  // government-only filter these disappear along with the figure they rest
  // on, which is the honest result rather than a gap: without an industry
  // head count Israel can say how much chicken it produced and not how many
  // chickens that took.
  const head = (d.national || []).find(r => r.measure === 'head_slaughtered');
  const w = (d.derived_weight || [])[0];
  const cards = (head || w) ? `<div class="grid2" style="margin-top:14px">` +
    (head ? `<div class="verdict">
        <div class="v-val">${(head.value / 1000).toLocaleString(undefined,
          { maximumFractionDigits: 1 })}M</div>
        <div class="v-key">birds slaughtered per year</div>
        <div class="note">${badge(head.confidence)} ${head.source_slug}</div>
      </div>` : '') +
    (w ? `<div class="verdict">
        <div class="v-val">${w.kg_per_head.toFixed(2)} kg</div>
        <div class="v-key">implied average bird</div>
        <div class="note">${badge(w.confidence)} ${w.output_year} output ÷
          ${w.head_year} head${w.year_gap
            ? `, ${w.year_gap} year apart` : ''}</div>
      </div>` : '') + `</div>` : '';

  $('#c-answers').innerHTML = `
    <h3>${meta.name} <span class="note">${
      [meta.native_mass_unit, meta.native_currency].filter(Boolean).join(' · ')
    }</span></h3>
    <p class="muted">What this country's own statistics can answer:</p>
    <ul class="can">${items}</ul>${calcNote}${cards}`;

  // A filtered answer that does not say what it filtered is just a different
  // number, so name the dropped rows rather than quietly showing fewer.
  $('#c-excluded').innerHTML = (d.excluded || []).length
    ? 'Hidden by this filter: ' + d.excluded.map(e =>
        `<strong>${(MEASURE()[e.measure] || {}).title || e.measure}</strong>
         (${e.confidence}, <code>${e.source}</code>)`).join(', ') + '.'
    : (C_GRADE && (d.national || []).length
        ? `Nothing hidden — every figure ${meta.name} has in this panel is
           government-measured.`
        : '');

  // ---- national series, one chart per measure that exists
  const nat = d.national || [];
  const byMeasure = m => nat.filter(r => r.measure === m)
                            .slice().sort((x, y) => x.year - y.year);
  const prov = nat.some(r => r.provisional);

  $('#c-national-title').textContent = `${meta.name} — national series`;
  $('#c-national-note').innerHTML = nat.length
    ? `${nat.length} figures.` + (prov
        ? ' Points marked provisional are the publisher\'s own flag, carried' +
          ' through rather than smoothed away.' : '')
    : `No national series loaded. ${meta.name} answers this question` +
      ` elsewhere — see "By state".`;

  plotSeries('c-output', ['meat_output', 'output_value'], byMeasure, meta);
  plotSeries('c-flock', ['inventory_eoy'], byMeasure, meta);

  // ---- subnational
  const reg = (d.regional || []).filter(r => r.region_level !== 'total');
  const total = (d.regional || []).find(r => r.region_level === 'total');
  $('#c-regional-title').textContent = `${meta.name} — subnational`;
  // "No subnational detail" would be false for the US, which has 23 regions --
  // they simply live in the size/production tables rather than in this one.
  // The capability map is the authority on whether the data exists; this panel
  // only knows whether IT has any, so it must not generalise from that.
  $('#c-regional-note').innerHTML = reg.length
    ? `${reg.length} regions.` + (d.suppressed_regions
        ? ` <span class="warn">${d.suppressed_regions} suppressed by the
            publisher's disclosure rules</span> — a real constraint, not a gap
            to fill by estimating.` : '')
    : (a.subnational
        ? `${meta.name} has subnational data
           (${meta.subnational_regions || 0} regions), but as live weight and
           production rather than as an output series — see “By state”.`
        : 'No subnational detail loaded.');

  if (reg.length) {
    // Districts and councils are different levels of the same hierarchy, so
    // they are labelled rather than mixed into one flat ranking that would
    // double-count a district against the councils inside it.
    const rows = reg.slice().sort((x, y) => y.value - x.value);
    $('#c-regional').innerHTML =
      `<table><tr><th>Region</th><th>Level</th>
        <th class="num">Marketed</th><th class="num">Share</th></tr>` +
      rows.map(r => {
        const level = r.region_level || 'council';
        const share = total && total.value
          ? ((r.value / total.value) * 100).toFixed(1) + '%' : '—';
        return `<tr><td>${r.region}</td><td class="note">${level}</td>
          <td class="num">${Math.round(r.value).toLocaleString()} ${r.unit}</td>
          <td class="num">${r.region_level === 'district' ? share : ''}</td></tr>`;
      }).join('') +
      (total ? `<tr><td><strong>${total.region}</strong></td><td></td>` +
        `<td class="num"><strong>${
          Math.round(total.value).toLocaleString()} ${total.unit
        }</strong></td><td></td></tr>` : '') + '</table>';
  } else {
    $('#c-regional').innerHTML = '';
  }

  // ---- sources, because a figure without one does not ship
  const slugs = [...new Set([...nat, ...(d.regional || [])]
    .map(r => r.source_slug).filter(Boolean))];
  $('#c-sources').innerHTML = slugs.length
    ? `<ul class="can" style="flex-direction:column;gap:6px">` +
      slugs.map(s => `<li class="yes"><code>${s}</code></li>`).join('') +
      '</ul>'
    : '<p class="muted">None — nothing is loaded for this country.</p>';
  $('#c-sources-panel').hidden = !slugs.length;
}

// One y-axis per unit. Tonnes and shekels share a chart only because they
// share a shape; the axis titles carry the unit so neither is read as the
// other.
function plotSeries(div, measures, byMeasure, meta) {
  const traces = measures.map(m => {
    const rows = byMeasure(m);
    if (!rows.length) return null;
    const cfg = MEASURE()[m] || { title: m, colour: CH.amber2 };
    return {
      x: rows.map(r => r.year),
      y: rows.map(r => r.value),
      name: `${cfg.title} (${rows[0].unit})`,
      type: 'scatter', mode: 'lines+markers',
      line: { color: cfg.colour, width: 2 },
      // Provisional points get an open marker, so the publisher's own hedge
      // survives into the chart instead of being flattened.
      marker: {
        size: 7,
        symbol: rows.map(r => r.provisional ? 'circle-open' : 'circle'),
      },
      hovertemplate: `%{x}: %{y:,} ${rows[0].unit}<extra></extra>`,
      yaxis: measures.indexOf(m) === 0 ? 'y' : 'y2',
    };
  }).filter(Boolean);

  const el = document.getElementById(div);
  if (!traces.length) { el.innerHTML = ''; el.style.height = '0'; return; }
  el.style.height = '300px';

  const layout = Object.assign({}, PLOT, {
    showlegend: traces.length > 1,
    legend: { orientation: 'h', y: 1.15 },
    xaxis: Object.assign({}, PLOT.xaxis, { title: '' }),
    yaxis: Object.assign({}, PLOT.yaxis, { title: traces[0].name }),
  });
  if (traces.length > 1) {
    layout.yaxis2 = { overlaying: 'y', side: 'right',
                      gridcolor: 'rgba(0,0,0,0)', title: traces[1].name };
    layout.margin = Object.assign({}, PLOT.margin, { r: 60 });
  }
  Plotly.newPlot(div, traces, layout, CFG);
}

// ---- trends
async function initTrends() {
  const d = await api('/api/trends');
  const yr = d.husbandry.map(r => r.year);
  const line = (div, x, y, title, colour) => Plotly.newPlot(div,
    [{ x, y, mode: 'lines+markers', line: { color: colour, width: 2 } }],
    Object.assign({}, PLOT, { title: { text: title, font: { size: 13 } } }),
    CFG);
  line('t-weight', yr, d.husbandry.map(r => r.end_size),
       'Market weight (lb)', CH.stamp);
  line('t-mort', yr, d.husbandry.map(r => r.mortality_pct),
       'Grow-out mortality (%) — rising since 2013', CH.bad);
  line('t-fcr', yr, d.husbandry.map(r => r.feed_conversion),
       'Feed conversion ratio (lower is better)', CH.study);
  line('t-yield', d.dressing_yield.map(r => r.year),
       d.dressing_yield.map(r => r.dressing_yield * 100),
       'Dressing yield (%) — measured, not estimated', CH.measured);
}

// ---- seasons
//
// Two charts, and the second is the point. The national line shows how little
// the year moves; the peak-month histogram shows the states agreeing anyway.
// Showing only the line would understate the finding, and showing only the
// histogram would overstate it.
const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// A verdict is a claim about evidence, so it gets a colour that says how much
// to trust it -- never one that just looks nice.
const SEASON_COLOUR = () => ({
  cycle: CH.measured, weak: CH.stamp, trend: CH.study,
  spike: CH.bad, noise: CH.grey2, insufficient: CH.grey,
});

async function initSeason() {
  const d = await api('/api/seasonality');
  $('#se-summary').textContent = d.verdict.summary;

  const nat = d.national;
  if (nat) {
    Plotly.newPlot('se-national', [{
      x: MONTHS_SHORT, y: nat.values, mode: 'lines+markers',
      line: { color: CH.stamp, width: 2 },
      hovertemplate: '%{x}: %{y:.2f} lb<extra></extra>',
    }], Object.assign({}, PLOT, {
      title: {
        text: `United States — ${nat.swing_pct.toFixed(1)}% across the year `
            + `(${nat.verdict})`,
        font: { size: 13 },
      },
      // Zero-based would flatten a 2.7% swing into a straight line and imply
      // there is nothing there; a tight axis would imply drama. Pad the real
      // range instead and let the axis labels carry the scale.
      yaxis: { title: 'lb live weight', range: [nat.lo - 0.25, nat.hi + 0.25] },
    }), CFG);
  }

  const counts = MONTHS_SHORT.map((_, i) =>
    d.regions.filter(r => r.peak_month === i + 1).length);
  const window = d.concordance.peak.window || [];
  Plotly.newPlot('se-peaks', [{
    x: MONTHS_SHORT, y: counts, type: 'bar',
    marker: {
      color: MONTHS_SHORT.map((_, i) =>
        window.includes(i + 1) ? CH.measured : CH.barRecede),
    },
    hovertemplate: '%{y} states peak in %{x}<extra></extra>',
  }, {
    x: MONTHS_SHORT,
    y: MONTHS_SHORT.map(() => d.regions.length / 12),
    mode: 'lines', line: { color: CH.bad, width: 1, dash: 'dot' },
    name: 'if the peak month were random',
    hovertemplate: 'expected by chance: %{y:.1f}<extra></extra>',
  }], Object.assign({}, PLOT, {
    title: { text: 'Which month each state peaks in', font: { size: 13 } },
    yaxis: { title: 'states' },
    showlegend: false,
  }), CFG);

  const co = d.concordance;
  $('#se-concordance').innerHTML =
    `<strong>Peak:</strong> ${co.peak.explanation}
     <strong>Trough:</strong> ${co.trough.explanation}
     <br><br>` + co.peak.caveats.map(c => `— ${c}`).join('<br>');

  $('#se-table').innerHTML = `<table><tr><th>State</th>
    <th class="num">Range (lb)</th><th class="num">Swing</th>
    <th class="num">Signal</th><th class="num">Survives smoothing</th>
    <th>Peak</th><th>Verdict</th></tr>` +
    d.regions.map(r => `<tr>
      <td>${r.region}</td>
      <td class="num">${r.lo.toFixed(2)}–${r.hi.toFixed(2)}</td>
      <td class="num">${r.swing_pct.toFixed(1)}%</td>
      <td class="num">${r.signal_ratio.toFixed(1)}×</td>
      <td class="num">${(r.persistence * 100).toFixed(0)}%</td>
      <td>${r.peak_month_name}</td>
      <td title="${r.explanation.replace(/"/g, '&quot;')}"
          style="color:${SEASON_COLOUR()[r.verdict] || CH.grey2}">
        ${r.verdict}</td>
    </tr>`).join('') + '</table>';

  $('#se-notmodelled').innerHTML =
    d.not_modelled.map(n => `<li>${n}</li>`).join('');
}

// ---- does size make it better
//
// One view, one species at a time. "Is a fatter chicken better?" is a broiler
// question; a laying hen is graded on egg size and saffron on colouring
// strength, so the question, the x-axis and the verdict all arrive from the
// API rather than being written here. An axis the corpus cannot answer yet
// renders as an open question -- that absence is a real finding about the
// data, and hiding it would misrepresent the corpus as more complete than it
// is.

// A verdict word carries its own colour: this is a claim about evidence, so
// "we cannot say" must never be able to look like a settled answer.
const VERDICT_CLASS = {
  better: 'v-better', worse: 'v-worse', unchanged: 'v-same',
};
const verdictCell = (key, v) => {
  const open = v == null;
  return `<div class="verdict"><div class="v-val ${
    open ? 'v-open' : VERDICT_CLASS[v] || 'v-same'}">${
    open ? 'open question' : v}</div>
    <div class="v-key">${key}</div></div>`;
};

async function initSize() {
  const { axes } = await api('/api/quality-axes');
  const box = $('#size-picker');
  box.innerHTML = axes.map((a, i) =>
    `<button data-sp="${a.slug}" class="${i ? '' : 'on'}"${
      a.has_figures ? '' : ' data-thin="1"'}>${a.common_name}</button>`
  ).join('');
  box.querySelectorAll('button').forEach(b => {
    b.onclick = () => {
      box.querySelectorAll('button').forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      showSize(b.dataset.sp);
    };
  });
  await showSize(axes[0].slug);
}

async function showSize(species) {
  const d = await api('/api/bird-size?species=' + encodeURIComponent(species));
  const ax = d.axis, sp = d.species, s = d.spread;
  const unit = ax.x_unit ? ` ${ax.x_unit}` : '';

  $('#size-question').textContent = ax.question;
  $('#size-intro').textContent = d.verdict.summary || '';

  // The three legs of the verdict, named for this species rather than for
  // chickens: "wings per chicken" is meaningless on a crocus.
  $('#size-verdict').innerHTML = [
    [`Yield per ${sp.individual_noun}`, d.verdict.yield_per_individual],
    ['Quality', d.verdict.quality],
    [`${sp.individual_plural} on the plate`, d.verdict.count_floor],
  ].map(([k, v]) => verdictCell(k, v)).join('');

  // ---- the axis itself
  const bands = d.axis_bands;
  const bandsPanel = $('#size-bands-panel');
  bandsPanel.hidden = !bands.length;
  if (bands.length) {
    const continuous = ax.x_kind === 'continuous';
    $('#size-bands-title').textContent = continuous
      ? `${ax.x_label} bands` : `${ax.x_label}es`;
    $('#size-bands-note').textContent = continuous
      ? 'Not biology, market segment. Each band is a different business ' +
        'buying a different bird.'
      : 'A graded ladder rather than a measured quantity: the grade is the ' +
        'axis, so there is nothing in between the rungs.';

    $('#size-programs').innerHTML = continuous
      ? `<table><tr><th>Program</th><th class="num">${ax.x_label}</th>
         <th>Serves</th></tr>` +
        bands.map(p => `<tr><td><b>${p.label}</b></td>
          <td class="num">${p.size_lo}–${p.size_hi} ${p.size_unit || unit}</td>
          <td>${p.typical_market || '—'}</td></tr>`).join('') + '</table>'
      : `<table><tr><th>Grade</th><th>Product</th>
         <th class="num">Per lb</th></tr>` +
        bands.map(g => `<tr><td><b>${g.label}</b></td>
          <td>${g.product_label}</td>
          <td class="num">${g.units_per_lb_lo != null
            ? `${g.units_per_lb_lo}–${g.units_per_lb_hi}` : '—'}</td>
          </tr>`).join('') + '</table>';
  }

  // Regional spread is a broiler-only series, so the chart and its summary
  // line appear only where there is one. Everything above still renders.
  const reg = d.regions;
  const chart = $('#size-chart');
  chart.hidden = !reg.length;
  if (reg.length) {
    $('#size-programs').insertAdjacentHTML('beforeend',
      `<p class="note" style="margin-top:10px">
       ${s.heaviest.region} averages ${s.heaviest.avg_size}${unit} against
       ${s.lightest.region}'s ${s.lightest.avg_size}${unit} —
       <b>${s.ratio.toFixed(2)}× heavier</b>, national average
       ${d.national_avg}${unit}.</p>`);

    // Coloured by which band each region falls in, read from the bands
    // themselves rather than from thresholds retyped here.
    const bandOf = v => {
      const i = bands.findIndex(b => v >= b.size_lo && v <= b.size_hi);
      return [CH.brown, CH.amber2, CH.amberBright][
        i < 0 ? (v > (bands[bands.length - 1] || {}).size_hi ? 2 : 0) : i];
    };
    Plotly.newPlot('size-chart', [{
      type: 'bar', x: reg.map(r => r.region), y: reg.map(r => r.avg_size),
      marker: { color: reg.map(r => bandOf(r.avg_size)) },
      hovertemplate: `%{x}<br>%{y}${unit}<extra></extra>`,
    }], Object.assign({}, PLOT, {
      margin: { l: 50, r: 16, t: 10, b: 96 },
      yaxis: Object.assign({}, PLOT.yaxis, { title: ax.x_label + unit }),
      xaxis: Object.assign({}, PLOT.xaxis, { tickangle: -45 }),
      shapes: d.national_avg ? [{
        type: 'line', x0: -0.5, x1: reg.length - 0.5,
        y0: d.national_avg, y1: d.national_avg,
        line: { color: CH.faint, dash: 'dot', width: 1 },
      }] : [],
    }), CFG);
  }

  // ---- what more of it costs
  const def = d.defects.slice().reverse();
  const dp = $('#size-defects-panel');
  if (!def.length) {
    // No defect figures is itself the finding, and it reads very differently
    // from "no defects". Say which one this is.
    dp.hidden = false;
    $('#size-defects-title').textContent = 'What more of it costs you';
    $('#size-defects-note').innerHTML =
      `No quality figures for ${sp.common_name.toLowerCase()} are in the ` +
      'corpus yet. That is a gap in the sourcing, not a finding that ' +
      'nothing goes wrong — the difference matters, so the panel says so ' +
      'rather than showing an empty chart.';
    $('#size-defects').innerHTML = '';
    $('#size-defects').hidden = true;
    $('#size-defect-notes').innerHTML = '';
    return;
  }
  dp.hidden = false;
  $('#size-defects').hidden = false;
  $('#size-defects-title').textContent = `What more ${
    ax.x_label.toLowerCase()} costs you`;
  $('#size-defects-note').textContent =
    'Every defect measured gets more common as the axis rises. The contrast ' +
    'between parts is the point: one is riddled with problems and the other ' +
    'has essentially none.';

  // The zero wing-myopathy row is deliberate: it makes the asymmetry visible
  // instead of an absent category.
  Plotly.newPlot('size-defects', [{
    type: 'bar', orientation: 'h',
    x: def.map(x => x.prevalence_pct_mode), y: def.map(x => x.label),
    marker: { color: def.map(x => x.weight_association === 'none'
                                ? CH.study : CH.bad) },
    customdata: def.map(x => [x.affected_part, x.weight_association]),
    hovertemplate: '%{y}<br>%{x}% affected<br>' +
      'part: %{customdata[0]}<br>with axis: %{customdata[1]}<extra></extra>',
  }], Object.assign({}, PLOT, {
    margin: { l: 250, r: 20, t: 10, b: 44 },
    xaxis: Object.assign({}, PLOT.xaxis, { title: '% prevalence' }),
  }), CFG);

  $('#size-defect-notes').innerHTML = def.slice().reverse().map(x =>
    `<div class="step ${x.weight_association === 'none' ? '' : 'count'}">
      <h4>${x.label} ${badge(x.weight_association === 'none'
        ? 'study' : 'estimate')}
      </h4>
      <p>${x.notes || ''}</p>
      <div class="cite">${x.source_title} — ${x.publisher}
      ${x.url ? `· <a href="${x.url}" target="_blank" rel="noopener">source</a>` : ''}
      </div></div>`).join('');
}

// ---- nutrition & impact
async function impact() {
  const count = $('#i-count').value || 12;
  const product = $('#i-product').value || 'whole_wing';

  const [n, f] = await Promise.all([
    api(`/api/nutrition?product=${product}`),
    api(`/api/footprint?count=${count}&product=${product}`),
  ]);

  $('#i-alloc').textContent = f.allocation_note;

  $('#i-nutrition').innerHTML = n.nutrition.length
    ? `<table><tr><th>Preparation</th><th class="num">kcal/100g</th>
       <th class="num">per piece</th><th class="num">protein</th>
       <th class="num">fat</th><th class="num">carbs</th></tr>` +
      n.nutrition.map(r => `<tr><td><b>${r.label}</b></td>
        <td class="num">${r.kcal ?? '—'}</td>
        <td class="num">${r.per_unit ? r.per_unit.kcal.toFixed(0) : '—'}</td>
        <td class="num">${r.protein_g ?? '—'} g</td>
        <td class="num">${r.fat_g ?? '—'} g</td>
        <td class="num">${r.carbohydrate_g ?? 0} g</td></tr>`).join('') +
      '</table>' + n.nutrition.filter(r => r.notes).map(r =>
        `<div class="step"><h4>${r.label}</h4><p>${r.notes}</p>
         <div class="cite">${r.source_title} — ${r.publisher}</div></div>`
      ).join('')
    : '<p class="note">No nutrition data for this product yet.</p>';

  const m = f.metrics.filter(x => x.allocated_total != null);
  Plotly.newPlot('i-footprint', [
    { type: 'bar', name: 'charged to whole birds',
      x: m.map(x => x.label), y: m.map(x => x.naive_total),
      marker: { color: CH.barMuted },
      hovertemplate: '%{x}<br>%{y:.2f}<extra>naive</extra>' },
    { type: 'bar', name: 'this product’s share',
      x: m.map(x => x.label), y: m.map(x => x.allocated_total),
      marker: { color: CH.stamp },
      hovertemplate: '%{x}<br>%{y:.2f}<extra>allocated</extra>' },
  ], Object.assign({}, PLOT, {
    barmode: 'group', showlegend: true,
    legend: { orientation: 'h', y: 1.15 },
    margin: { l: 56, r: 16, t: 30, b: 70 },
    xaxis: Object.assign({}, PLOT.xaxis, { tickangle: -20 }),
    yaxis: Object.assign({}, PLOT.yaxis, { type: 'log',
      title: 'log scale — units differ per metric' }),
  }), CFG);

  $('#i-footprint-table').innerHTML = `<table><tr><th>Metric</th>
    <th class="num">Per bird</th><th class="num">Allocated to your order</th>
    <th class="num">Since 2010</th><th>Unit</th></tr>` +
    f.metrics.map(x => `<tr><td>${x.label}</td>
      <td class="num">${x.per_individual ?? '—'}</td>
      <td class="num">${x.allocated_total != null
          ? x.allocated_total.toFixed(2) : '—'}</td>
      <td class="num">${x.pct_change_decade != null
          ? x.pct_change_decade + '%' : '—'}</td>
      <td>${x.unit}</td></tr>`).join('') + '</table>';

  const g = f.grower_pay;
  $('#i-econ').innerHTML = (g ? `<div class="step count">
      <h4>The farmer's share</h4>
      <p>${f.birds.toFixed(2)} birds at
      ${(g.live_weight_lb / f.birds).toFixed(2)} lb each is
      ${g.live_weight_lb.toFixed(1)} lb of live weight. At
      ${(g.rate * 100).toFixed(1)}¢ per lb the grower was paid
      <b>$${g.paid_for_birds.toFixed(2)}</b> for raising them — of which
      <b>$${g.allocated_to_product.toFixed(2)}</b> is this product's share.</p>
    </div>` : '') +
    `<table><tr><th>Measure</th><th class="num">Value</th><th>Unit</th>
     <th>Basis</th></tr>` +
    f.economics.map(e => `<tr><td><b>${e.label}</b></td>
      <td class="num">${(e.value_mode ?? 0).toLocaleString()}</td>
      <td>${e.unit}</td><td>${badge(e.confidence)}</td></tr>`).join('') +
    '</table>';
}

async function initImpact() {
  // Default to the headline product explicitly. Products come back ordered
  // by slug, which puts "boneless_wing" first alphabetically -- and boneless
  // has no nutrition rows yet, so the default view would open on an empty
  // panel.
  $('#i-product').innerHTML = META.products
    .filter(p => p.active)
    .map(p => `<option value="${p.slug}"${
      p.slug === 'whole_wing' ? ' selected' : ''}>${p.label}</option>`)
    .join('');
  ['i-count', 'i-product'].forEach(id => {
    $('#' + id).addEventListener('change', impact);
    $('#' + id).addEventListener('input', impact);
  });
  await impact();
}

// ---- facts + sources
// ---- fact card deck
let FACTS = [], DECK = [], POS = 0;

function renderCard() {
  if (!DECK.length) {
    $('#f-headline').textContent = 'No facts at that surprise level';
    $('#f-body').textContent = '';
    $('#f-cite').textContent = '';
    $('#f-stars').textContent = '';
    $('#f-dots').innerHTML = '';
    $('#f-count').textContent = '';
    return;
  }
  POS = (POS + DECK.length) % DECK.length;
  const f = DECK[POS];

  $('#f-stars').textContent = '★'.repeat(f.surprise) +
                              '☆'.repeat(5 - f.surprise);
  $('#f-headline').textContent = f.headline;
  $('#f-body').textContent = f.body;
  $('#f-cite').innerHTML = `${f.source_title} — ${f.publisher}` +
    (f.url ? ` · <a href="${f.url}" target="_blank" rel="noopener">source</a>`
           : '');
  $('#f-count').textContent = `${POS + 1} of ${DECK.length}`;

  // Deck wraps, so the arrows are never disabled -- but keep the handles in
  // sync in case that changes.
  $('#f-prev').disabled = DECK.length < 2;
  $('#f-next').disabled = DECK.length < 2;

  $('#f-dots').innerHTML = DECK.map((_, i) =>
    `<button class="dot${i === POS ? ' on' : ''}" data-i="${i}"
      aria-label="Fact ${i + 1}"></button>`).join('');
  $('#f-dots').querySelectorAll('.dot').forEach(d => {
    d.onclick = () => { POS = +d.dataset.i; renderCard(); };
  });
}

function filterDeck() {
  const min = +$('#f-surprise').value;
  DECK = FACTS.filter(f => f.surprise >= min);
  POS = 0;
  renderCard();
}

async function initFacts() {
  // limit high enough to take everything; the deck filters client-side so
  // changing the surprise floor does not re-fetch.
  const d = await api('/api/facts?placement=learning&limit=500');
  FACTS = d.facts;

  $('#f-prev').onclick = () => { POS--; renderCard(); };
  $('#f-next').onclick = () => { POS++; renderCard(); };
  $('#f-surprise').onchange = filterDeck;
  $('#f-random').onclick = () => {
    if (DECK.length < 2) return;
    let n = POS;
    while (n === POS) n = Math.floor(Math.random() * DECK.length);
    POS = n;
    renderCard();
  };

  // Arrow keys, scoped to the facts view so they do not hijack the page
  // while someone is on the calculator.
  document.addEventListener('keydown', ev => {
    if (!$('#v-facts').classList.contains('on')) return;
    if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'SELECT') return;
    if (ev.key === 'ArrowLeft') { POS--; renderCard(); }
    if (ev.key === 'ArrowRight') { POS++; renderCard(); }
  });

  // Swipe. Horizontal intent only, so vertical scrolling still works.
  let x0 = null, y0 = null;
  const card = $('#f-card');
  card.addEventListener('touchstart', e => {
    x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
  }, { passive: true });
  card.addEventListener('touchend', e => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    const dy = e.changedTouches[0].clientY - y0;
    if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy)) {
      POS += dx < 0 ? 1 : -1;
      renderCard();
    }
    x0 = y0 = null;
  }, { passive: true });

  filterDeck();
}
async function initSources() {
  const d = await api('/api/sources');
  $('#sourcelist').innerHTML = `<table><tr><th>Source</th><th>Type</th>
    <th class="num">Figures</th></tr>` + d.sources.map(s =>
    `<tr><td><b>${s.title}</b><br><span class="note">${s.publisher}
     ${s.url ? `· <a href="${s.url}" target="_blank" rel="noopener">link</a>` : ''}</span></td>
     <td>${badge(s.source_type === 'government' ? 'measured'
        : s.source_type === 'peer_reviewed' ? 'study'
        : s.source_type === 'estimate' ? 'estimate' : 'industry')}
       <span class="note">${s.source_type.replace('_',' ')}</span></td>
     <td class="num">${s.used_by}</td></tr>`).join('') + '</table>';
}

// Views that read META must not initialise before the boot fetch resolves.
// A nav click can land first, and initSci reading META.chains on a null META
// throws, aborting before it ever calls sci() -- which shows up as an empty
// supply-chain dropdown and blank results rather than as a visible error.
let READY = null;

async function load(v) {
  if (loaded[v]) return;
  loaded[v] = true;
  const init = { sci: initSci, mix: initMix, states: initStates,
                 country: initCountry,
                 size: initSize, impact: initImpact,
                 trends: initTrends, season: initSeason, facts: initFacts,
                 sources: initSources }[v];
  if (!init) return;
  try {
    await READY;
    await init();
  } catch (err) {
    // Let the view be retried rather than silently staying blank forever.
    loaded[v] = false;
    console.error(`failed to initialise "${v}"`, err);
  }
}

// ---- build stamp
//
// The version is never written here. It comes from /api/version, which reads
// installed package metadata, so pyproject.toml stays the single source of
// truth -- see docs/VERSIONING.md. Hardcoding it would give the page a second
// place to be wrong.
function renderBuild(v) {
  const bits = [`<span class="ver">v${v.package_version}</span>`];

  // Locally there is no commit -- say "local" rather than printing "null" or
  // quietly implying the tag is what is running.
  bits.push(v.git_commit_short
    ? `build <code>${v.git_commit_short}</code>`
    : `<code>local</code>`);
  if (v.branch) bits.push(`<code>${v.branch}</code>`);

  const r = v.row_counts || {};
  const corpus = [
    [r.source, 'source'],
    [r.fact, 'fact'],
    [r.loss_factor, 'loss factor'],
  ].filter(([n]) => n != null)
   .map(([n, label]) => `${n} ${label}${n === 1 ? '' : 's'}`);
  if (corpus.length) bits.push(corpus.join(', '));

  $('#build').innerHTML = bits.join('<span class="sep">·</span>');
  $('#build').hidden = false;
}

// ---- boot
READY = (async () => {
  // Logo is decorative, so a failure here must never block the page.
  api('/api/brand')
    .then(b => { $('#logo').textContent = b.chicken; })
    .catch(() => {});

  // Same rule for the build stamp: informational, so it must never be able to
  // take the page down with it. It stays hidden if the fetch fails.
  api('/api/version').then(renderBuild).catch(() => {});

  META = await api('/api/meta');

  const active = META.products.filter(p => p.active);
  $('#product').innerHTML = active.map(p =>
    `<option value="${p.slug}"${p.slug === 'whole_wing' ? ' selected' : ''}>${
      p.label}</option>`).join('');

  // The window control only makes sense for a rate, so it follows the
  // selected product rather than sitting there permanently confusing anyone
  // asking about wings.
  // The chain list belongs to the SELECTED PRODUCT'S SPECIES, not to the whole
  // corpus. `is_default` is per-species -- the schema's unique index enforces
  // exactly that -- so rendering every chain flat and marking each default
  // `selected` leaves whichever sorts last in charge. Adding saffron made that
  // "Commodity spice trade", so the wing calculator opened on a saffron route
  // and was one step from narrating a chicken through a picking tray. Eggs had
  // the same collision already and won it only by alphabetical luck.
  const syncChains = () => {
    const p = active.find(x => x.slug === $('#product').value);
    const mine = META.chains.filter(c =>
      !c.species_slug || !p || c.species_slug === p.species_slug);
    const keep = mine.some(c => c.slug === $('#chain').value)
      ? $('#chain').value
      : (mine.find(c => c.is_default) || mine[0] || {}).slug;
    $('#chain').innerHTML = mine.map(c =>
      `<option value="${c.slug}"${c.slug === keep ? ' selected' : ''}>${
        c.label}</option>`).join('');
  };

  const syncWindow = () => {
    const p = active.find(x => x.slug === $('#product').value);
    $('#window-wrap').hidden = !p || p.yield_mode !== 'recurring';
    $('#pieces').closest('label').hidden =
      !p || p.slug !== 'whole_wing';
  };
  // Chains before the window, so a product change has a valid chain selected
  // by the time calc() reads it.
  //
  // Both are also bound to `input`, not just `change`: a <select> fires
  // `input` before `change`, and calc() below listens on both. Without this,
  // the first calc() after a product switch ran on `input` before syncChains
  // had a chance to run on `change` -- so it read the PREVIOUS product's
  // chain and briefly rendered a contradictory answer (egg with a wing
  // chain: floor > ceiling). Listeners for the same event fire in
  // registration order, so registering these before calc's own `input`
  // listener (below) is what makes the ordering hold.
  $('#product').addEventListener('change', syncChains);
  $('#product').addEventListener('change', syncWindow);
  $('#product').addEventListener('input', syncChains);
  $('#product').addEventListener('input', syncWindow);
  syncChains();
  syncWindow();

  ['count','product','chain','pieces','mort','window-days'].forEach(id => {
    $('#' + id).addEventListener('change', calc);
    $('#' + id).addEventListener('input', calc);
  });
  await calc();
})();
