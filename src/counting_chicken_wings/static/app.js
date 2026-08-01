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
      if (!r.ok) {
        // FastAPI's HTTPException body is {"detail": "..."} -- surface that
        // rather than a bare status code, so "count must be <= 100000" reaches
        // the person who typed the count instead of only the console.
        //
        // A 422 is the other shape: RequestValidationError makes `detail` a
        // LIST of {msg, loc, ...} objects, and interpolating that straight into
        // a template literal renders "[object Object]" to the person who simply
        // typed a zero. Join the messages instead.
        //
        // And an OBJECT is the third shape. /api/bird-size answers "which of
        // the two 404s is this?" in the body -- a species the corpus has never
        // been asked about is a different thing from a slug that does not
        // exist, and only the first is renderable. An object reaching the
        // template literal is the same "[object Object]" bug as the list, one
        // shape over, so it reads `message` and the caller reads the rest.
        return r.json().catch(() => null).then(body => {
          const d = body && body.detail;
          const msg = Array.isArray(d)
            ? d.map(e => e && e.msg).filter(Boolean).join('; ')
            : (d && typeof d === 'object') ? d.message : d;
          const err = new Error(msg || `${p} -> ${r.status}`);
          // The status and the structured detail travel WITH the error, so a
          // caller can act on the failure instead of only reporting it. Every
          // catch that just wants a sentence still gets one from `.message`.
          err.status = r.status;
          err.detail = d;
          throw err;
        });
      }
      return r.json();
    })
    .finally(() => busy(-1));
};

// Shared inline error affordance. Small and next to the control it concerns,
// not a modal -- and cleared on the next successful call so it cannot outlive
// the problem it described. Every fetch path (calc/sci/impact/boot) used to
// let a rejected request -- typically a 422 from an out-of-range count --
// disappear silently, leaving the previous answer on screen with no
// indication anything had gone wrong.
function setError(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg || '';
  el.hidden = !msg;
}
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
// ---- the one redraw path
//
// A Plotly chart reads its colours from the CSS custom properties AND sizes
// itself to its container, both at draw time. Neither is re-read afterwards,
// so both go stale without a data change: rotate a phone and the chart keeps
// the width it was born with.
//
// `responsive: true` in CFG is not enough on its own, and the gap is
// measurable: at 1280px the mixing chart sat at 700px inside an 820px
// container, and dispatching a `resize` event by hand fixed it instantly.
// Charts drawn in a view that was hidden at the time never get a size worth
// keeping either, and revisiting the view does not redraw them because
// `loaded[v]` is still true. So ask for the resize explicitly, on the two
// occasions a chart's container can have changed size under it.
//
// Guarded on `Plotly.Plots`, because the CDN-failure stub at the top of this
// file defines `newPlot` and `relayout` and nothing else. A missing chart
// library must stay a degraded page, never a thrown error.
function resizeCharts() {
  if (!window.Plotly || !Plotly.Plots || !Plotly.Plots.resize) return;
  const view = document.querySelector('.view.on');
  if (!view) return;
  // `.js-plotly-plot` is Plotly's own marker class, so a container that was
  // never drawn into -- or that holds the stub's failure paragraph -- is
  // skipped rather than resized into an error.
  view.querySelectorAll('.js-plotly-plot').forEach(el => {
    try { Plotly.Plots.resize(el); } catch (e) { /* one chart, not the page */ }
  });
}

// Debounced, because a drag-resize fires this continuously and a relayout is
// not free. 120ms is below the threshold where a redraw reads as lag.
let resizeTimer = null;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(resizeCharts, 120);
});

// Redraw whatever view is showing; the others rebuild when opened.
//
// Colours cannot be restyled in place here: trace colours come from the same
// CSS variables as the frame does, so half a chart would follow the theme and
// half would not. A full re-init is the honest redraw, and it is what makes
// the additive listeners the inits used to register accumulate on every
// toggle -- see initSci/initImpact/initFacts, now assigning handlers instead.
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
  // Truncate rather than round. A value a hair below the ceiling
  // (11.99997 against 12) rounds UP to "12.00" at 2 decimals -- the exact
  // ambiguity this function exists to avoid -- so the old loop kept adding
  // decimal places until rounding finally landed strictly below the ceiling,
  // which is how "11.99997 different chickens" reached the headline instead
  // of a clean, short value. Truncating never overshoots the true value, so
  // it never manufactures a false tie with the ceiling and two decimals is
  // enough except in a genuinely pathological case.
  for (const p of [2,3,4,5,6]) {
    const scale = 10 ** p;
    const truncated = Math.floor(v * scale) / scale;
    if (truncated < ceil) return truncated.toFixed(p);
  }
  return v.toFixed(6);
}
const badge = c => c ? `<span class="badge b-${c}">${c}</span>` : '';

// The product the page is built around. Four copies of the literal
// 'whole_wing' used to sit in this file -- the calculator's default option,
// the Nutrition tab's default option, the Scientific tab's fixed product, and
// the mixing curve's implied one -- and nothing tied them together, so
// changing which question the page opens on meant finding all four.
const HEADLINE_PRODUCT = 'whole_wing';

// ---- scope
//
// Eight of the eleven views answer for one species, and the product dropdown
// offers twelve products across six as equals. Picking "Silk dress" and
// opening Trends showed broiler chickens with nothing saying they were not
// about silk -- the DATA was already honest (/api/nutrition returns an empty
// list rather than borrowing chicken figures), so this is entirely a
// navigation and framing gap.
//
// The rule that keeps the fix from rotting: no species is named in this file.
// A scoped endpoint reports the species ITS OWN query reached, and what is
// printed below is that. A view that widens to a second species relabels
// itself; one that narrows does too.
const VIEW_SCOPE = {};

// The species behind a product, for the two views that are pinned to a
// product by this page rather than scoped by their endpoint. Read out of
// META, so it is the corpus talking, not this file.
function productScope(slug) {
  const p = META && META.products.find(x => x.slug === slug);
  return p ? { species: [{ slug: p.species_slug, common_name: p.species }],
               label: p.species } : null;
}

// ---- the page's product selection
//
// ONE selection, two controls. The calculator and Nutrition & impact each had
// their own <select> and neither knew about the other, so setting Nutrition to
// a silk product and walking to Trends produced a scope marker citing whatever
// the CALCULATOR still had -- the marker was right about the view and wrong
// about the question. The page describes itself as one document that "re-scopes
// itself to whatever you ask it about"; two independent product states
// contradict that before any marker gets involved.
//
// Assigning `.value` does not fire `change` or `input`, so mirroring cannot
// loop. The refresh of the OTHER view is therefore explicit, and only when
// that view has been built -- calling impact() before initImpact has populated
// its controls would read an empty select.
let PRODUCT = HEADLINE_PRODUCT;

// Set by boot once the calculator's controls exist. A no-op before that, so
// an early product change cannot call into a half-built calculator.
let syncCalcControls = () => {};

// Take a new product from whichever control the reader used, and bring the
// other one with it. The control that fired already refreshed its own view --
// `calc` and `impact` are bound to their own selects -- so this refreshes the
// OTHER one, and only if it has been built.
function adoptProduct(slug) {
  if (!slug || slug === PRODUCT) return;
  PRODUCT = slug;

  const calcSel = $('#product'), impactSel = $('#i-product');
  const has = (sel) => sel && [...sel.options].some(o => o.value === slug);

  if (has(calcSel) && calcSel.value !== slug) {
    calcSel.value = slug;
    // The chain belongs to the product's species and calc() reads it, so the
    // controls have to be re-derived before the answer is recomputed.
    syncCalcControls();
    calc();
  }
  if (has(impactSel) && impactSel.value !== slug) {
    impactSel.value = slug;
    impact();
  }

  // The sentences are per-product, so they are refetched here rather than per
  // tab switch. renderScope() runs inside, and again immediately below so the
  // marker's scope line updates without waiting on the network.
  refreshBorrowNotes();
  renderScope();
}

// What the page is asking about, as a product row rather than a slug.
function selectedProduct() {
  return META ? META.products.find(p => p.slug === PRODUCT) : null;
}

// The mismatch sentences for the current product, one per species, from
// /api/scope. Null until the first fetch resolves and whenever it fails --
// `renderScope` degrades to the bare scope line rather than composing prose
// this file is not allowed to hold.
let BORROW = null;

async function refreshBorrowNotes() {
  try {
    const d = await api('/api/scope?product=' + encodeURIComponent(PRODUCT));
    BORROW = d.selected ? d.selected.borrow_notes : null;
  } catch (err) {
    BORROW = null;                // the scope line still renders without it
  }
  renderScope();
}

function renderScope() {
  const el = $('#scope-note');
  const cur = document.querySelector('nav button.on');
  const s = cur ? VIEW_SCOPE[cur.dataset.v] : null;
  if (!el) return;
  if (!s || !s.label) {          // product-aware or corpus-wide: nothing to say
    el.hidden = true;
    el.innerHTML = '';
    el.classList.remove('mismatch');
    return;
  }
  const p = selectedProduct();
  const mismatch = !!p && s.species.length > 0 &&
    !s.species.some(x => x.slug === p.species_slug);
  el.classList.toggle('mismatch', mismatch);

  // The refusal sentence is the API's, not this file's. #110's constraint is
  // that scope copy is either app copy or comes from the API, and the second
  // is the better one: every noun in it is the corpus' own, so renaming a
  // species renames the sentence. The scope LABEL is still interpolated here
  // because it names no species by itself.
  //
  // One species is looked up rather than the whole set: a view scoped to two
  // species is not a mismatch unless the product belongs to neither, and the
  // first one it does not belong to is enough to say why.
  const note = mismatch && BORROW
    ? s.species.map(x => BORROW[x.slug]).find(Boolean)
    : null;
  el.innerHTML = note
    ? `Showing <b>${s.label}</b>. ${note}`
    : `Showing <b>${s.label}</b>.`;
  el.hidden = false;
}

// ---- navigation
document.querySelectorAll('nav button').forEach(b => {
  b.onclick = () => {
    document.querySelectorAll('nav button').forEach(x => x.classList.remove('on'));
    document.querySelectorAll('.view').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    $('#v-' + b.dataset.v).classList.add('on');
    // Twice on purpose: once now from whatever this view already reported, so
    // the marker never lags a tab behind, and once after load() in case this
    // is the view's first visit and its scope arrives with its data.
    renderScope();
    // A view already loaded does not redraw, so a chart drawn before the
    // window changed size is still carrying the old one. It has a container
    // to measure now, which it did not while hidden.
    load(b.dataset.v).then(() => { renderScope(); resizeCharts(); });
  };
});

// The strapline's three names, wired to the same nav buttons rather than to a
// second copy of the switching logic. `.click()` on the real control keeps one
// definition of what opening a view means, and keeps the rail's `.on` marker
// honest -- a duplicate switcher was how the nav and the visible section came
// apart in an earlier draft of this page.
document.querySelectorAll('[data-goto]').forEach(b => {
  b.onclick = () => {
    const target = document.querySelector(`nav button[data-v="${b.dataset.goto}"]`);
    if (target) target.click();
  };
});

// ---- calculator
let calcSeq = 0;

// An empty field means "use the default", but `value || fallback` treats
// "0" as truthy (it is a non-empty string) and sends it straight to the API,
// which then 422s on a bound the field's own `min` already implied. Only an
// actually-empty field should fall back; anything else -- including "0" or
// a negative -- goes to the server and surfaces through the catch below,
// rather than silently becoming the fallback value or silently failing.
const numOrDefault = (id, def) => {
  const v = $('#' + id).value;
  return v === '' ? def : v;
};

async function calc() {
  const mine = ++calcSeq;
  const q = new URLSearchParams({
    count: numOrDefault('count', 12),
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

  let d;
  try {
    d = await api('/api/calculate?' + q);
  } catch (err) {
    if (mine !== calcSeq) return;   // superseded by a newer request
    setError('calc-error', `Could not calculate: ${err.message}`);
    return;
  }
  if (mine !== calcSeq) return;     // superseded by a newer request
  setError('calc-error', '');       // clear whatever the last attempt showed
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
  // > 1, not just truthy: the server returns segments_per_unit: 1 for any
  // product with no piece breakdown (e.g. maple syrup), and "1 pieces is 1
  // whole wings" glued a wing-specific sentence onto a non-wing answer.
  if (d.question.segments_per_unit > 1)
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

  // Informational only -- a failure here must not blank out the answer
  // above, which already rendered successfully.
  let f;
  try {
    f = await api('/api/facts?placement=result&limit=1');
  } catch (err) {
    console.error('failed to load a result fact', err);
    return;
  }
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

// Shares of a variance always fill the axis, so a saturated cascade whose
// answer cannot move renders as a chart full of confident-looking bars. The
// absolute spread therefore goes ABOVE the chart, in words, computed from the
// response — never written into the markup, where it would go stale and where
// test_static.py would rightly object to it.
function renderSobol(v) {
  const panel = $('#s-sobol'), verdict = $('#s-sobol-verdict');
  if (!v || !v.shares || !v.shares.length) {
    if (panel) panel.innerHTML = '';
    if (verdict) verdict.textContent =
      'The variance decomposition is unavailable for this question.';
    return;
  }

  // Below about a thousandth the fixed notation is all zeroes, and the whole
  // point of the sentence is how small the number is.
  const fine = x => Math.abs(x) < 1e-3 ? x.toExponential(2) : x.toFixed(5);

  verdict.textContent =
    `Across all ${v.shares.length} mixing inputs, ${v.output} moves between ` +
    `${fine(v.sample_lo)} and ${fine(v.sample_hi)} — a standard deviation of ` +
    `${fine(v.sd)} on a mean of ${fine(v.mean)}. The bars below divide that ` +
    `spread; they do not say it is large.`;

  $('#s-sobol-notes').innerHTML = v.notes.map(n => `<div>${n}</div>`).join('');

  $('#s-sobol-cost').textContent =
    `${v.samples.toLocaleString()} samples, ` +
    `${v.evaluations.toLocaleString()} model evaluations, ` +
    `${v.bootstrap} bootstrap replicates, seed ${v.seed}. First-order shares ` +
    `sum to ${v.sum_first_order.toFixed(3)} and total-order to ` +
    `${v.sum_total_order.toFixed(3)}; the gap is interaction.`;

  const s = v.shares.slice().reverse();
  // A zero bar is three different claims — never read, no band recorded, or
  // genuinely unimportant — and they are not interchangeable. Say which.
  const why = x => x.degenerate
    ? 'no band recorded, so nothing to propagate'
    : (x.inert ? 'the model never reads this input' : `grade: ${x.confidence}`);
  const err = (val, lo, hi) => ({
    type: 'data', symmetric: false,
    array: val.map((x, i) => hi[i] - x),
    arrayminus: val.map((x, i) => x - lo[i]),
    color: CH.dim, thickness: 1,
  });
  const f = s.map(x => x.first_order), t = s.map(x => x.total_order);

  Plotly.newPlot('s-sobol', [{
    type: 'bar', orientation: 'h', name: 'first-order (alone)',
    x: f, y: s.map(x => x.label),
    marker: {
      color: s.map(x => (x.degenerate || x.inert)
        ? CH.faint : (CONF_COLOUR()[x.confidence] || CH.faint)),
    },
    error_x: err(f, s.map(x => x.first_lo), s.map(x => x.first_hi)),
    customdata: s.map(x => [why(x), x.kind]),
    hovertemplate: '%{y}<br>first-order %{x:.4f}<br>' +
      '%{customdata[1]} — %{customdata[0]}<extra></extra>',
  }, {
    type: 'bar', orientation: 'h', name: 'total (with interactions)',
    x: t, y: s.map(x => x.label),
    marker: { color: CH.barRecede },
    error_x: err(t, s.map(x => x.total_lo), s.map(x => x.total_hi)),
    hovertemplate: '%{y}<br>total-order %{x:.4f}<extra></extra>',
  }], Object.assign({}, PLOT, {
    barmode: 'group', showlegend: true,
    legend: { orientation: 'h', y: 1.12 },
    margin: { l: 230, r: 20, t: 34, b: 44 },
    xaxis: Object.assign({}, PLOT.xaxis, {
      title: `share of variance in ${v.output}`, range: [0, 1],
    }),
  }), CFG);
}

async function sci() {
  const mine = ++sciSeq;
  const conf = $('#s-conf').value;
  const q = new URLSearchParams({
    count: numOrDefault('s-count', 12),
    // Sent rather than left to the endpoint's default, so the product the
    // chain list was filtered for is the product the server routes.
    product: SCI_PRODUCT,
    chain: $('#s-chain').value,
    confidence_level: $('#s-ci').value,
    iterations: $('#s-iter').value,
  });
  if (conf) q.set('min_confidence', conf);

  // The variance decomposition is a second analysis of its own, and it is
  // fetched CONCURRENTLY rather than after: both endpoints take a couple of
  // seconds, so in series every load would pay for both. It also fails soft —
  // it is one panel of five, and losing it should not blank the view.
  const vq = new URLSearchParams({
    count: numOrDefault('s-count', 12),
    product: SCI_PRODUCT,
    chain: $('#s-chain').value,
    confidence_level: $('#s-ci').value,
  });

  let d, v;
  try {
    [d, v] = await Promise.all([
      api('/api/scientific?' + q),
      api('/api/variance?' + vq).catch(() => null),
    ]);
  } catch (err) {
    if (mine !== sciSeq) return;
    setError('sci-error', `Could not run the analysis: ${err.message}`);
    return;
  }
  if (mine !== sciSeq) return;      // superseded by a newer request
  setError('sci-error', '');
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

  renderSobol(v);

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
        text: `median ${a.required.toFixed(2)}`, font: { color: CH.ink } },
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
    `Mode path ends at ${modeEnd.toFixed(3)}; Monte Carlo median is ` +
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

// The Scientific view has no product control: it analyses the headline
// question, the same one the page opens on. Naming that here rather than
// leaving it to the endpoint's own default means the chain list and the
// request cannot disagree about which product is being asked about, which is
// the whole of the bug below.
const SCI_PRODUCT = HEADLINE_PRODUCT;

function initSci() {
  // Scoped by this page rather than by its endpoint -- /api/scientific will
  // analyse any product, and this view chooses not to offer the choice. So
  // the marker is derived from the pinned product's species, which is still
  // the corpus talking rather than a species name typed here.
  VIEW_SCOPE.sci = productScope(SCI_PRODUCT);
  // The chain list belongs to the analysed product's SPECIES. `is_default` is
  // per-species -- the schema's unique index enforces exactly that -- so
  // rendering all 15 chains flat and marking each default `selected` left
  // whichever sorted last in charge. Chains order by `is_default DESC, slug`,
  // so the Scientific tab opened a chicken-wing question on "Commodity syrup"
  // and offered "Commodity silk trade" and "Home garden" beside it. Picking
  // one moved the wing answer by up to six chickens.
  //
  // This is the same fix the calculator got in syncChains(); Scientific never
  // received it. The two now agree on the default for the same question,
  // which they did not.
  const p = META.products.find(x => x.slug === SCI_PRODUCT);
  const mine = META.chains.filter(c =>
    !c.species_slug || !p || c.species_slug === p.species_slug);
  const pick = (mine.find(c => c.is_default) || mine[0] || {}).slug;
  $('#s-chain').innerHTML = mine.map(c =>
    `<option value="${c.slug}"${c.slug === pick ? ' selected' : ''}>${
      c.label}</option>`).join('');
  // Assigned, not added. Every init here can run more than once -- a theme
  // toggle clears `loaded` so the visible view rebuilds -- and
  // `addEventListener` has no idea it has been called before. Three toggles
  // left four `change` handlers on each control, so one dropdown change fired
  // four concurrent Monte Carlo runs at up to 100,000 iterations apiece.
  // `.onchange =` replaces; it is the pattern initCountry already uses.
  ['s-count','s-chain','s-ci','s-conf','s-iter'].forEach(id => {
    $('#' + id).onchange = sci;
  });
  sci();
}

// ---- mixing simulator
let CURVE = null;
async function initMix() {
  // The curve is drawn at the endpoint's default units_per_individual, which
  // is two -- the headline product's anatomy. Same situation as Scientific:
  // pinned by this page, so the marker comes from that product's species.
  VIEW_SCOPE.mix = productScope(HEADLINE_PRODUCT);
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
        range: [5.5, 12.5], tickformat: '.2f' }),
      showlegend: false,
    }), CFG);
  $('#mixnote').textContent = CURVE.note;
  $('#pool').max = CURVE.points.length - 1;
  $('#pool').disabled = false;   // was disabled until CURVE resolved
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
  VIEW_SCOPE.states = d.scope;
  // The server names the empty case explicitly (no year had data, or the
  // requested year had none) rather than leaving an empty map and a
  // header-only table to speak for themselves.
  const msg = $('#states-message');
  msg.hidden = !d.message;
  msg.textContent = d.message || '';
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
  const meta = await api('/api/countries');
  // Scope comes from the country LIST, not from /api/output: that endpoint
  // 404s for a country with no output series (the US, which answers through
  // "By state" instead) and showCountry deliberately swallows it, so a scope
  // read from there would vanish on exactly the country the page opens on.
  VIEW_SCOPE.country = meta.scope;
  COUNTRIES = meta.countries;
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
  VIEW_SCOPE.trends = d.scope;
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
  VIEW_SCOPE.season = d.scope;
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
  // EVERY active species, including the three the corpus has no size question
  // for yet. They used to be absent: the endpoint inner-joined quality_axis,
  // so a silkworm, a beef cow and a sugar maple never reached the picker and
  // a view introducing itself with "every species is graded on something"
  // offered three chips out of six with no hint the other three existed.
  //
  // Three states, not two, and the distinction is the whole point of this
  // project: an answered axis, an axis with no figures behind it yet
  // (`data-thin`), and a question nobody has asked yet (`data-unasked`).
  const first = axes.find(a => a.has_axis) || axes[0];
  box.innerHTML = axes.map(a =>
    `<button data-sp="${a.slug}" class="${a === first ? 'on' : ''}"${
      !a.has_axis ? ' data-unasked="1"'
                  : a.has_figures ? '' : ' data-thin="1"'}>${
      a.common_name}</button>`
  ).join('');
  box.querySelectorAll('button').forEach(b => {
    b.onclick = () => {
      box.querySelectorAll('button').forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      showSize(b.dataset.sp);
    };
  });
  // Open on a species that has an answer. Opening on an unasked question
  // would make the view's first impression a blank, which is a fact about
  // one species being read as a fact about the corpus.
  if (first) await showSize(first.slug);
}

// The species the corpus has never been asked a size question about. A 404,
// because there is no size question to serve -- but a renderable one: the
// error names the species and says so in a sentence, and this draws that
// rather than leaving the panel on whichever species was showing before.
//
// Handling the failure is the point. An unhandled rejection here is what the
// picker used to avoid by not offering these species at all, which is how a
// view claiming to grade "every species" came to show three of six.
function renderUnaskedSize(detail) {
  const sp = detail.species;
  $('#size-question').textContent = detail.message;
  $('#size-intro').textContent =
    'The axis has to be sourced before it can be shown, and no other ' +
    'species’ axis can stand in for it — the question is different for ' +
    'each one, and so is what a bigger individual costs. This is a gap in ' +
    'the corpus, stated rather than filled in.';

  // Three open questions, drawn by the same cell the answered legs use, so
  // "nobody has asked" looks like every other unsourced thing on this page.
  $('#size-verdict').innerHTML = [
    [`Yield per ${sp.individual_noun}`, null],
    ['Quality', null],
    [`${sp.individual_plural} on the plate`, null],
  ].map(([k, v]) => verdictCell(k, v)).join('');

  $('#size-bands-panel').hidden = true;
  $('#size-chart').hidden = true;
  $('#size-defects-panel').hidden = false;
  $('#size-defects-title').textContent = 'What more of it costs you';
  $('#size-defects-note').textContent =
    `No quality figures for ${sp.common_name.toLowerCase()} are in the ` +
    'corpus either. That is a gap in the sourcing, not a finding that ' +
    'nothing goes wrong.';
  $('#size-defects').innerHTML = '';
  $('#size-defects').hidden = true;
  $('#size-defect-notes').innerHTML = '';
}

async function showSize(species) {
  let d;
  try {
    d = await api('/api/bird-size?species=' + encodeURIComponent(species));
  } catch (err) {
    // Only the one failure this view can say something useful about. Anything
    // else -- an unknown slug, the API being down -- is a real error and
    // belongs on the floor, where load() logs it and lets the view retry.
    if (err.detail && err.detail.error === 'no_size_question') {
      renderUnaskedSize(err.detail);
      return;
    }
    throw err;
  }
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
// Same pattern as calcSeq/sciSeq above: requests are not guaranteed to
// resolve in the order they were sent, so a stamp per call and a check on
// return is what stops a partially-typed count from winning a race against
// the finished one -- otherwise the footprint chart and the farmer's-share
// paragraph could settle on numbers for "1" while "120" was still mid-type.
let impactSeq = 0;

async function impact() {
  const mine = ++impactSeq;
  const count = numOrDefault('i-count', 12);
  const product = $('#i-product').value || PRODUCT;

  let n, f;
  try {
    [n, f] = await Promise.all([
      api(`/api/nutrition?product=${product}`),
      api(`/api/footprint?count=${count}&product=${product}`),
    ]);
  } catch (err) {
    // A superseded request must not report its failure either: the newer
    // one owns the panel now, and a stale error would sit over live numbers.
    if (mine !== impactSeq) return;
    setError('impact-error', `Could not load: ${err.message}`);
    return;
  }
  if (mine !== impactSeq) return;   // superseded by a newer request
  setError('impact-error', '');

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

  // Everything below is conditional on `f.coverage`, because for most
  // products the honest render is an empty one. The endpoint used to hand
  // back broiler figures whatever was asked for, so a silk dress arrived as
  // 22,200 birds of feed and water and this code drew it without hesitating.
  //
  // The individual's noun comes from the corpus too. "birds" was written into
  // the headings here, so even a correct egg answer read as poultry
  // regardless -- the same bug as the hardcoded floor prose, one screen over.
  const one = f.individual_noun, many = f.individual_plural;

  const m = f.metrics.filter(x => x.allocated_total != null);
  if (m.length) {
    Plotly.newPlot('i-footprint', [
      { type: 'bar', name: `charged to whole ${many}`,
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
  } else {
    // A chart of nothing is worse than no chart: an empty pair of axes still
    // asserts that the comparison exists and happens to be zero.
    $('#i-footprint').innerHTML = '';
    $('#i-footprint').style.height = 'auto';
  }

  $('#i-footprint-table').innerHTML = f.metrics.length
    ? `<table><tr><th>Metric</th>
       <th class="num">Per ${one}</th>
       <th class="num">Allocated to your order</th>
       <th class="num">Since 2010</th><th>Unit</th></tr>` +
      f.metrics.map(x => `<tr><td>${x.label}</td>
        <td class="num">${x.per_individual ?? '—'}</td>
        <td class="num">${x.allocated_total != null
            ? x.allocated_total.toFixed(2) : '—'}</td>
        <td class="num">${x.pct_change_decade != null
            ? x.pct_change_decade + '%' : '—'}</td>
        <td>${x.unit}</td></tr>`).join('') + '</table>'
    // Which species the figures DO belong to is not named here: the panel
    // above prints /api/footprint's own allocation_note, which says it from
    // the corpus. This copy said "measured on broiler chickens" and would
    // have gone on saying it after a second species gained a footprint.
    : `<p class="note">No resource footprint has been sourced for the
       ${one} yet.</p>`;

  const g = f.grower_pay;
  $('#i-econ').innerHTML = (g ? `<div class="step count">
      <h4>The farmer's share</h4>
      <p>${f.individuals.toFixed(2)} ${many} at
      ${g.avg_live_weight_lb.toFixed(2)} lb each is
      ${g.live_weight_lb.toFixed(1)} lb of live weight. At
      ${(g.rate * 100).toFixed(1)}¢ per lb the grower was paid
      <b>$${g.paid_for_individuals.toFixed(2)}</b> for raising them — of which
      <b>$${g.allocated_to_product.toFixed(2)}</b> is this product's share.</p>
    </div>` : '') +
    (f.economics.length
      ? `<table><tr><th>Measure</th><th class="num">Value</th><th>Unit</th>
         <th>Basis</th></tr>` +
        f.economics.map(e => `<tr><td><b>${e.label}</b></td>
          <td class="num">${(e.value_mode ?? 0).toLocaleString()}</td>
          <td>${e.unit}</td><td>${badge(e.confidence)}</td></tr>`).join('') +
        '</table>'
      : `<p class="note">No payment or employment figures are in the corpus
         for this industry yet.</p>`);
}

// Trailing-edge debounce, used below to stop every keystroke in the count
// field from firing its own request -- typing "120" fired six requests
// (two listeners × three digits) before the seq guard above was even
// reached.
function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

async function initImpact() {
  // Opens on the page's CURRENT product, not on the headline one. This view is
  // built lazily, so arriving here after picking maple syrup on the calculator
  // used to reset the question to wings -- one half of the two-selections bug,
  // the other half being that changing it here never reached the calculator.
  // (The default still matters: products come back ordered by slug, which puts
  // "boneless_wing" first alphabetically, and boneless has no nutrition rows
  // yet, so an implicit default would open on an empty panel.)
  $('#i-product').innerHTML = META.products
    .filter(p => p.active)
    .map(p => `<option value="${p.slug}"${
      p.slug === PRODUCT ? ' selected' : ''}>${p.label}</option>`)
    .join('');
  // Assignment, not addEventListener: redrawTheme() re-runs initImpact on
  // every theme toggle, and addEventListener would leave the previous
  // toggle's listener in place instead of replacing it -- each theme switch
  // would then fire one more impact() per keystroke than the last.
  const debouncedImpact = debounce(impact, 250);
  const onProduct = () => { impact(); adoptProduct($('#i-product').value); };
  $('#i-count').onchange = impact;
  $('#i-count').oninput = debouncedImpact;
  $('#i-product').onchange = onProduct;
  $('#i-product').oninput = onProduct;
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
  VIEW_SCOPE.facts = d.scope;
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

  // Everything below binds to `document` and to the card element, and both
  // outlive this function. `.onkeydown =` is not an option on `document`
  // (one slot, shared with anything else that ever wants it) and the touch
  // handlers want `{ passive: true }`, which the property form cannot carry.
  // So bind once and say so, rather than adding another copy of all three
  // every time a theme toggle rebuilds this view. Three toggles was three
  // extra keydown handlers, and one right-arrow press moved the deck four
  // cards -- the reported "the deck skips".
  if (!factsBound) { factsBound = true; bindFactsGestures(); }

  filterDeck();
}

let factsBound = false;

function bindFactsGestures() {
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

  // The anchor sentence under the strapline. The species is never named in
  // this file: /api/scope computes it from v_species_coverage as the active
  // species present in the most dimensions of the corpus, and returns null on
  // a tie -- so the day a second species reaches parity this paragraph
  // disappears instead of making a claim the data stopped supporting.
  //
  // Non-blocking, like the logo and the build stamp: the page is entirely
  // usable without it, so it must not be able to take boot down.
  api('/api/scope').then(s => {
    const a = s.anchor, el = $('#anchor-note');
    if (!a || !el) return;
    el.innerHTML = `<b>${a.common_name}</b> is the anchor dataset — the
      species this corpus measures in the most ways. Everything else extends
      it rather than matches it, and any view answering for one species says
      which at the top.`;
    el.hidden = false;
  }).catch(() => {});

  // Everything downstream reads META, so its failure is not survivable the
  // way the logo's or the build stamp's is -- but it used to fail exactly
  // as quietly: every dropdown stayed empty and the headline sat on its
  // initial em-dash forever, with nothing on screen saying why.
  try {
    META = await api('/api/meta');
  } catch (err) {
    const el = document.getElementById('boot-error');
    if (el) {
      el.hidden = false;
      el.textContent = 'Could not load — the API may be unreachable. ' +
        `Reload to try again. (${err.message})`;
    }
    throw err;
  }

  const active = META.products.filter(p => p.active);
  $('#product').innerHTML = active.map(p =>
    `<option value="${p.slug}"${p.slug === HEADLINE_PRODUCT ? ' selected' : ''
      }>${p.label}</option>`).join('');

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
      !p || p.slug !== HEADLINE_PRODUCT;
  };

  // The calculator's controls, re-derivable from outside the calculator --
  // Nutrition & impact can now change the page's product, and the chain and
  // window belong to the product's species rather than to whichever control
  // was touched.
  syncCalcControls = () => { syncChains(); syncWindow(); };
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

  // Changing the product changes whether every OTHER view is answering the
  // question you just asked. Switching to a silk product and walking to
  // Trends is the exact path the page used to take in silence, and the
  // marker has to be right the moment you arrive, not one tab later.
  const fromCalc = () => adoptProduct($('#product').value);
  $('#product').addEventListener('change', fromCalc);
  $('#product').addEventListener('input', fromCalc);

  await Promise.all([calc(), refreshBorrowNotes()]);
})();
