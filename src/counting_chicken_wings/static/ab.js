/* Frontend A/B measurement. Shared verbatim by both variants.
 *
 * One file for both designs on purpose: an instrument that differs between
 * the two arms measures itself as much as the thing under test.
 *
 * It attaches from the outside -- a delegated click listener and a fetch
 * wrapper -- so neither page has to be edited to be measured, and the
 * redesign cannot forget to instrument something. Nothing here throws into
 * the page: every hook is wrapped, because a broken counter must not be able
 * to break the site it is counting.
 */
(function () {
  'use strict';

  var ENDPOINT = '/api/metrics';
  var cookie = function (name) {
    var m = document.cookie.match('(?:^|; )' + name + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : null;
  };

  // The server owns both cookies; if it did not set them, it does not want
  // this page measured, and we stay silent rather than inventing an id.
  var VARIANT = cookie('ccw_ui');
  var SESSION = cookie('ccw_sid');
  if (!VARIANT || !SESSION) return;

  var t0 = Date.now();
  var queue = [];
  var flushTimer = null;
  var interacted = false;

  function post(body, beacon) {
    try {
      var json = JSON.stringify(body);
      // pagehide cannot await a fetch; sendBeacon is the only send that
      // survives the page going away, which is exactly when dwell is known.
      if (beacon && navigator.sendBeacon) {
        navigator.sendBeacon(ENDPOINT, new Blob([json],
          { type: 'application/json' }));
        return;
      }
      fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: json,
        keepalive: true,
      }).catch(function () { /* measurement is never load-bearing */ });
    } catch (e) { /* ditto */ }
  }

  function flush(beacon) {
    if (!queue.length) return;
    var batch = queue.splice(0, 50);
    // VARIANT is read once, at load, and travels with every batch. The
    // server prefers it over the current cookie because the dwell beacon
    // arrives during unload -- by then a visitor who switched variants is
    // already carrying the *next* page's cookie, and the time would be
    // credited to the design that did not earn it.
    post({ session: SESSION, variant: VARIANT, events: batch }, beacon);
  }

  function track(name, value, meta) {
    try {
      queue.push({ name: name, value: value, meta: meta || undefined });
      if (queue.length >= 20) { flush(false); return; }
      // Batched rather than one request per event: the API-latency numbers
      // this collects would otherwise be measuring its own traffic.
      if (!flushTimer) {
        flushTimer = setTimeout(function () {
          flushTimer = null;
          flush(false);
        }, 2000);
      }
    } catch (e) { /* never */ }
  }

  // Exposed so a page can mark something this file cannot see from outside.
  window.ccwTrack = track;

  /* ---- page load ------------------------------------------------------ */

  function loadMs() {
    try {
      var nav = performance.getEntriesByType('navigation')[0];
      if (nav && nav.loadEventEnd > 0) return Math.round(nav.loadEventEnd);
      var t = performance.timing;
      if (t && t.loadEventEnd > 0) return t.loadEventEnd - t.navigationStart;
    } catch (e) { /* fall through */ }
    return null;
  }

  function firstPaint() {
    try {
      var e = performance.getEntriesByName('first-contentful-paint')[0];
      return e ? Math.round(e.startTime) : null;
    } catch (err) { return null; }
  }

  function sendPageview() {
    track('pageview', loadMs(), {
      fcp: firstPaint(),
      // Width, not a user agent string: the design question here is
      // phone-versus-desktop, and a UA string is a fingerprint.
      w: window.innerWidth,
      dpr: Math.round((window.devicePixelRatio || 1) * 10) / 10,
    });
  }

  if (document.readyState === 'complete') sendPageview();
  else window.addEventListener('load', function () {
    // A tick after `load` so loadEventEnd is actually populated.
    setTimeout(sendPageview, 0);
  });

  /* ---- which parts of the UI get found -------------------------------- */

  document.addEventListener('click', function (ev) {
    try {
      var el = ev.target.closest('[data-v]');
      if (el) track('view', null, { view: el.getAttribute('data-v') });
    } catch (e) { /* never */ }
  }, true);

  /* ---- did they actually use it, and how long did that take ----------- */

  function markInteraction(ev) {
    if (interacted) return;
    try {
      var t = ev.target;
      if (!t || !t.matches) return;
      if (!t.matches('input, select, textarea, .slider')) return;
      interacted = true;
      track('interact', Date.now() - t0, { tag: t.id || t.tagName });
    } catch (e) { /* never */ }
  }
  document.addEventListener('change', markInteraction, true);
  document.addEventListener('input', markInteraction, true);

  /* ---- API latency and failures --------------------------------------- */

  var nativeFetch = window.fetch;
  if (typeof nativeFetch === 'function') {
    window.fetch = function (input, init) {
      var url = '';
      try {
        url = typeof input === 'string' ? input : (input && input.url) || '';
      } catch (e) { url = ''; }

      // Never measure the measurement endpoint; that is a feedback loop.
      if (url.indexOf(ENDPOINT) !== -1) return nativeFetch(input, init);

      var start = (performance && performance.now) ? performance.now()
                                                   : Date.now();
      var done = function (status, ok) {
        var ms = ((performance && performance.now) ? performance.now()
                                                   : Date.now()) - start;
        // Path only. A full URL can carry a query string, and query strings
        // are where personal data ends up by accident.
        var path = url;
        try { path = new URL(url, location.origin).pathname; } catch (e) { }
        track('api', Math.round(ms), { path: path, status: status });
        if (!ok) track('error', null, { message: path + ' -> ' + status });
      };
      return nativeFetch(input, init).then(function (r) {
        done(r.status, r.ok);
        return r;
      }, function (err) {
        done(0, false);
        track('error', null, { message: 'network: ' + (err && err.message) });
        throw err;
      });
    };
  }

  window.addEventListener('error', function (ev) {
    try {
      track('error', null, {
        message: String(ev.message || 'error').slice(0, 200),
        // Where in the page, so a variant-specific break is locatable.
        at: (ev.filename || '') + ':' + (ev.lineno || 0),
      });
    } catch (e) { /* never */ }
  });

  window.addEventListener('unhandledrejection', function (ev) {
    try {
      var r = ev.reason;
      track('error', null, {
        message: String((r && r.message) || r || 'rejection').slice(0, 200),
      });
    } catch (e) { /* never */ }
  });

  /* ---- how long they stayed ------------------------------------------- */

  var dwellSent = false;
  function sendDwell() {
    if (dwellSent) return;
    dwellSent = true;
    track('dwell', Date.now() - t0, { interacted: interacted });
    flush(true);
  }
  // pagehide fires on mobile Safari where unload does not.
  window.addEventListener('pagehide', sendDwell);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') { flush(true); }
  });
})();
