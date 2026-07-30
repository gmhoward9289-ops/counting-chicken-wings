"""Seasonality: the statistics, and the three failure modes they must survive.

The classifier here is OURS -- no source says a swing must clear a threshold
to be a season -- so it is tested against synthetic series whose right answer
is known by construction, not only against the corpus. Each synthetic case is
a shape that is not a season but scores like one on a weaker test:

  * **A single anomalous month** scores exactly the ideal-cycle score on
    amplitude over jitter. Texas shipped as "the one seasonal state" on the
    strength of one June until `persistence` was added.
  * **A trend with a January reset** passes amplitude AND persistence. It fails
    only on `wrap_share`, because a cycle returns to where it started and a
    trend jumps back.
  * **Twelve independent random draws** produce a range of about 3.3 standard
    deviations, which looks impressive stated as a percentage of the mean.
"""

import math
import random

import pytest
from fastapi.testclient import TestClient

from counting_chicken_wings import db as dbm
from counting_chicken_wings import seasonality as seas
from counting_chicken_wings.api import app


# ---------------------------------------------------------------------------
# Synthetic series: the answer is known by construction
# ---------------------------------------------------------------------------

def sine_year(amplitude: float = 1.0, mean: float = 10.0) -> list[float]:
    return [
        mean + amplitude / 2 * math.sin(2 * math.pi * t / 12) for t in range(12)
    ]


def test_clean_annual_cycle_is_a_cycle():
    s = seas.analyse("Sineland", 2025, sine_year())
    assert s.verdict == "cycle"
    assert s.signal_ratio == pytest.approx(seas.IDEAL_CYCLE_RATIO, abs=0.01)
    assert s.persistence == pytest.approx(
        seas.IDEAL_CYCLE_PERSISTENCE, abs=0.01)


def test_single_odd_month_is_not_a_cycle():
    """The one that shipped wrong. Flat year, one dip, ideal-cycle score."""
    values = [10.0] * 12
    values[5] = 9.0
    s = seas.analyse("Spikeland", 2025, values)

    # It passes the amplitude test outright -- that is the trap.
    assert s.signal_ratio >= seas.CYCLE_FLOOR
    assert s.persistence == pytest.approx(seas.SPIKE_PERSISTENCE, abs=0.01)
    assert s.verdict == "spike"
    assert not s.is_seasonal
    assert "not" in s.explanation
    assert any("June" in n for n in s.notes)


def test_random_months_are_noise():
    rng = random.Random(7)
    verdicts = []
    for _ in range(200):
        values = [rng.gauss(10.0, 0.3) for _ in range(12)]
        verdicts.append(seas.analyse("Noiseland", 2025, values).verdict)
    # A handful of false positives is expected from 200 random years; a
    # majority would mean the thresholds are useless.
    assert verdicts.count("noise") > 150
    assert verdicts.count("cycle") < 20


def test_a_trend_with_a_new_year_reset_is_not_a_cycle():
    """Rising all year then starting over is a trend, not a season.

    The December-to-January wrap in `mean_absolute_step` is what makes the
    reset count against it.
    """
    values = [10.0 + 0.1 * t for t in range(12)]
    s = seas.analyse("Trendland", 2025, values)
    assert s.verdict == "trend"
    assert "January reset" in s.explanation


def test_suppressed_months_are_not_interpolated():
    values = sine_year()
    values[3] = None
    values[4] = None
    s = seas.analyse("Gapland", 2025, values)
    assert s.months_present == 10
    assert s.verdict == "insufficient"
    # No statistic pretends to a shape it cannot see.
    assert s.signal_ratio == 0.0
    assert s.persistence == 0.0
    # The figures that DO exist are still reported.
    assert s.hi > s.lo
    assert "10 of 12" in s.explanation


def test_sparkline_shows_a_gap_as_a_gap():
    values = sine_year()
    values[0] = None
    line = seas.sparkline(values)
    assert len(line) == 12
    assert line[0] == " ", "a suppressed month must not render as a low bar"


def test_analyse_rejects_a_year_that_is_not_twelve_months():
    with pytest.raises(ValueError):
        seas.analyse("Shortland", 2025, [1.0] * 11)


# ---------------------------------------------------------------------------
# Concordance: agreement between series
# ---------------------------------------------------------------------------

def _fake(region: str, peak: int) -> seas.Seasonality:
    values = [10.0] * 12
    values[peak - 1] = 11.0
    return seas.analyse(region, 2025, values)


def test_concordance_finds_agreement_that_no_single_series_shows():
    series = [_fake(f"S{i}", 9) for i in range(12)]
    c = seas.concordance(series, "peak")
    assert c.in_window == 12
    assert c.verdict == "strong agreement"
    assert c.p_corrected < 0.01
    # Not one of those series is itself a cycle. That is the whole point.
    assert all(not s.is_seasonal for s in series)


def test_concordance_reports_no_agreement_when_peaks_scatter():
    series = [_fake(f"S{i}", (i % 12) + 1) for i in range(12)]
    c = seas.concordance(series, "peak")
    assert c.verdict == "no agreement"
    assert c.p_corrected > 0.05


def test_concordance_p_value_is_corrected_for_choosing_the_window():
    series = [_fake(f"S{i}", 9) for i in range(8)]
    c = seas.concordance(series, "peak")
    assert c.p_corrected > c.p_value
    assert c.p_corrected == pytest.approx(min(1.0, c.p_value * 12))
    assert any("chosen from the data" in cav for cav in c.caveats)


def test_concordance_states_that_regions_are_not_independent():
    series = [_fake(f"S{i}", 9) for i in range(12)]
    c = seas.concordance(series, "peak")
    assert any("independent" in cav for cav in c.caveats)


def test_concordance_needs_enough_regions():
    c = seas.concordance([_fake("A", 9), _fake("B", 9)], "peak")
    assert c.verdict == "no agreement"
    assert "too few" in c.explanation


def test_concordance_rejects_an_unknown_kind():
    with pytest.raises(ValueError):
        seas.concordance([_fake("A", 9)], "middle")


# ---------------------------------------------------------------------------
# Against the corpus
# ---------------------------------------------------------------------------

def test_every_named_state_has_all_twelve_months():
    conn = dbm.connect()
    try:
        series = dbm.monthly_size_series(conn, year=2025)
    finally:
        conn.close()
    assert len(series) >= 23
    for region, entry in series.items():
        assert len(entry["values"]) == 12
        assert entry["source_slug"], f"{region} has no citation"


def test_the_states_agree_on_the_season_even_though_none_is_seasonal():
    """The finding v1.5.0 exists to carry. Fails if NASS revises the series.

    Two claims, and the second is not a weaker version of the first: no single
    state's twelve months are a clean cycle, and the states nonetheless peak
    together far more than chance allows.
    """
    conn = dbm.connect()
    try:
        raw = dbm.monthly_size_series(conn, year=2025)
    finally:
        conn.close()
    national = seas.analyse("United States", 2025,
                            raw.pop("United States")["values"])
    states = [seas.analyse(n, 2025, v["values"]) for n, v in raw.items()]

    assert not national.is_seasonal
    assert not any(s.is_seasonal for s in states)
    assert national.swing_pct < 3.0

    peak = seas.concordance(states, "peak")
    assert peak.verdict == "strong agreement"
    assert peak.window == (8, 9, 10)
    assert peak.p_corrected < 0.01


def test_texas_is_a_spike_and_says_so():
    """Regression: Texas was published as the one seasonal state."""
    conn = dbm.connect()
    try:
        raw = dbm.monthly_size_series(conn, year=2025)
    finally:
        conn.close()
    tx = seas.analyse("Texas", 2025, raw["Texas"]["values"])
    assert tx.signal_ratio >= seas.CYCLE_FLOOR, "still passes the first test"
    assert tx.verdict == "spike"
    assert any("Do not quote" in n for n in tx.notes)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def test_seasonality_endpoint_carries_its_citation():
    d = TestClient(app).get("/api/seasonality").json()
    assert d["sources"], "a statistic without its source cannot be rendered"
    for region in d["regions"]:
        assert region["source_slug"]


def test_seasonality_endpoint_states_what_it_does_not_model():
    d = TestClient(app).get("/api/seasonality").json()
    assert d["verdict"]["affects_count"] is False
    reasons = " ".join(d["not_modelled"]).lower()
    assert "condemnation" in reasons
    assert "head slaughtered" in reasons


def test_seasonality_summary_matches_the_rows_it_describes():
    """The generated summary must not outrun the data.

    The first draft was hardcoded and claimed no state was seasonal while one
    was being reported as seasonal in the same payload.
    """
    d = TestClient(app).get("/api/seasonality").json()
    cycles = [r["region"] for r in d["regions"] if r["verdict"] == "cycle"]
    assert d["verdict"]["cycles"] == cycles
    if cycles:
        for region in cycles:
            assert region in d["verdict"]["summary"]
    else:
        assert "Not one" in d["verdict"]["summary"]


def test_seasonality_classification_is_graded_as_our_judgement():
    d = TestClient(app).get("/api/seasonality").json()
    # The weights are surveyed; the verdict about their shape is not.
    assert d["national"]["confidence"] == "estimate"
    assert d["concordance"]["peak"]["confidence"] == "estimate"


def test_seasonality_404s_for_a_year_with_no_monthly_data():
    r = TestClient(app).get("/api/seasonality", params={"year": 1899})
    assert r.status_code == 404
