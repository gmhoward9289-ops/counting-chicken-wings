-- counting-chicken-wings : chicken statistics database
--
-- Design rules, enforced by structure rather than convention:
--   1. Every numeric fact carries a source_id. There is no way to insert a
--      statistic without saying where it came from -- source_id is NOT NULL
--      on every table that holds a number.
--   2. Every estimated fact carries lo/mode/hi, not a bare point value. A
--      measured fact sets all three equal and marks confidence='measured'.
--   3. Species is a dimension from day one. v1 seeds broiler chicken only;
--      turkey drops in later with no migration.
--   4. Nothing is deleted. Superseded figures get valid_to set and stay
--      queryable, so a run from last year can be reproduced exactly.

PRAGMA foreign_keys = ON;


-- ---------------------------------------------------------------------------
-- Provenance
-- ---------------------------------------------------------------------------

CREATE TABLE source (
    id              INTEGER PRIMARY KEY,
    slug            TEXT    NOT NULL UNIQUE,
    title           TEXT    NOT NULL,
    publisher       TEXT    NOT NULL,
    url             TEXT,
    published_on    TEXT,            -- ISO date; NULL if undated
    retrieved_on    TEXT    NOT NULL,
    source_type     TEXT    NOT NULL CHECK (source_type IN (
                        'government',     -- USDA NASS, FSIS
                        'peer_reviewed',  -- journal article
                        'trade_body',     -- National Chicken Council
                        'trade_press',    -- WATTPoultry, Poultry Site
                        'industry_spec',  -- equipment/packaging specs
                        'derived',        -- computed from other sources
                        'estimate'        -- our own reasoned estimate
                    )),
    notes           TEXT
);

-- A derived figure records which sources it was computed from, so the
-- audit trail can recurse (e.g. dressing yield <- two NASS totals).
CREATE TABLE source_derivation (
    derived_source_id  INTEGER NOT NULL REFERENCES source(id),
    parent_source_id   INTEGER NOT NULL REFERENCES source(id),
    PRIMARY KEY (derived_source_id, parent_source_id)
);


-- ---------------------------------------------------------------------------
-- Taxonomy / dimensions
-- ---------------------------------------------------------------------------

CREATE TABLE species (
    id              INTEGER PRIMARY KEY,
    slug            TEXT    NOT NULL UNIQUE,   -- 'broiler'
    common_name     TEXT    NOT NULL,          -- 'Broiler chicken'
    nass_category   TEXT,                      -- 'Young Chickens'
    wings_per_bird  INTEGER NOT NULL DEFAULT 2,
    active          INTEGER NOT NULL DEFAULT 1
);

-- Small-bird / medium / big-bird programs. Drives wing size, and therefore
-- how many birds a given POUNDAGE of wings represents. Bird COUNT floor is
-- unaffected, which is a distinction the CLI should make explicit.
CREATE TABLE bird_program (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    slug                TEXT    NOT NULL UNIQUE,  -- 'small_bird','big_bird'
    label               TEXT    NOT NULL,
    live_weight_lo_lb   REAL    NOT NULL,
    live_weight_mode_lb REAL    NOT NULL,
    live_weight_hi_lb   REAL    NOT NULL,
    typical_market      TEXT,                     -- 'fast food','deboning'
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT
);


-- ---------------------------------------------------------------------------
-- Industry structure
-- ---------------------------------------------------------------------------

CREATE TABLE producer (
    id                  INTEGER PRIMARY KEY,
    slug                TEXT    NOT NULL UNIQUE,  -- 'tyson'
    name                TEXT    NOT NULL,
    headquarters        TEXT,
    market_share_pct    REAL,                     -- national broiler volume
    head_per_week       INTEGER,
    plant_count         INTEGER,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    as_of_year          INTEGER,
    notes               TEXT
);

CREATE TABLE establishment (
    id                  INTEGER PRIMARY KEY,
    fsis_est_number     TEXT    UNIQUE,           -- FSIS establishment no.
    producer_id         INTEGER REFERENCES producer(id),
    name                TEXT    NOT NULL,
    state               TEXT,
    city                TEXT,
    bird_program_id     INTEGER REFERENCES bird_program(id),
    head_per_day        INTEGER,
    does_cutup          INTEGER,                  -- 1 if wings separated here
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT
);


-- ---------------------------------------------------------------------------
-- Observed statistics (measured, from government data)
-- ---------------------------------------------------------------------------

-- National annual slaughter totals. These are the anchor of the whole model.
CREATE TABLE national_slaughter_year (
    id                      INTEGER PRIMARY KEY,
    species_id              INTEGER NOT NULL REFERENCES species(id),
    year                    INTEGER NOT NULL,
    head_slaughtered        INTEGER,
    live_weight_lb          INTEGER,
    certified_rtc_lb        INTEGER,
    avg_live_weight_lb      REAL,
    postmortem_condemn_pct  REAL,
    postmortem_condemn_lb   INTEGER,
    source_id               INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, year)
);

-- State-level average live weight. This is where bird-size programs become
-- visible in public data (Ohio ~4.5 lb vs North Carolina ~8.6 lb).
CREATE TABLE state_live_weight (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    state               TEXT    NOT NULL,
    year                INTEGER NOT NULL,
    month               INTEGER,                  -- NULL = annual figure
    avg_live_weight_lb  REAL    NOT NULL,
    certified_lb        INTEGER,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, state, year, month)
);

-- Annual grow-out performance (NCC series): market age, weight, mortality.
CREATE TABLE flock_performance_year (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    year                INTEGER NOT NULL,
    market_age_days     REAL,
    market_weight_lb    REAL,
    feed_conversion     REAL,
    mortality_pct       REAL,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, year)
);


-- ---------------------------------------------------------------------------
-- The loss / yield chain
-- ---------------------------------------------------------------------------

-- An ordered chain of stages between a placed chick and a wing on a plate.
-- Each stage multiplies the surviving fraction. Walking the chain backwards
-- from "12 wings on a plate" gives the birds required.
CREATE TABLE loss_stage (
    id              INTEGER PRIMARY KEY,
    slug            TEXT    NOT NULL UNIQUE,
    label           TEXT    NOT NULL,
    sequence        INTEGER NOT NULL UNIQUE,  -- farm -> plate ordering
    phase           TEXT    NOT NULL CHECK (phase IN (
                        'farm','transport','slaughter','cutup',
                        'grading','further_processing','distribution','kitchen'
                    )),
    applies_to      TEXT    NOT NULL CHECK (applies_to IN (
                        'bird',      -- removes whole birds from the population
                        'wing',      -- removes/downgrades individual wings
                        'mass'       -- scales weight, not counts
                    )),
    -- Whether this stage counts toward the answer depends on the question
    -- being asked. Farm mortality is the clearest case: it matters for
    -- "how many chicks were placed" but not for "whose wings are on my plate".
    optional        INTEGER NOT NULL DEFAULT 0,
    default_enabled INTEGER NOT NULL DEFAULT 1,
    description     TEXT    NOT NULL,
    notes           TEXT
);

-- The actual numbers. Triangular lo/mode/hi drives Monte Carlo directly.
-- A stage can have several competing values (different producers, bird
-- programs, years, or sources) -- resolution is by specificity at query time.
CREATE TABLE loss_factor (
    id                  INTEGER PRIMARY KEY,
    loss_stage_id       INTEGER NOT NULL REFERENCES loss_stage(id),
    species_id          INTEGER NOT NULL REFERENCES species(id),
    -- Optional narrowing. NULL means "applies generally".
    producer_id         INTEGER REFERENCES producer(id),
    bird_program_id     INTEGER REFERENCES bird_program(id),
    state               TEXT,
    year                INTEGER,

    -- Surviving fraction, not loss fraction: 0.9955 means 0.45% lost.
    -- Values > 1.0 are legal and meaningful (marinade pickup adds mass).
    survive_lo          REAL    NOT NULL,
    survive_mode        REAL    NOT NULL,
    survive_hi          REAL    NOT NULL,

    confidence          TEXT    NOT NULL CHECK (confidence IN (
                            'measured',   -- directly reported by government
                            'derived',    -- computed from measured figures
                            'study',      -- peer-reviewed, may not generalize
                            'industry',   -- trade rule of thumb
                            'estimate'    -- our reasoning, flagged as such
                        )),
    source_id           INTEGER NOT NULL REFERENCES source(id),
    valid_from          TEXT,
    valid_to            TEXT,           -- NULL = current
    notes               TEXT,

    CHECK (survive_lo <= survive_mode AND survive_mode <= survive_hi),
    CHECK (survive_lo > 0)
);

CREATE INDEX idx_loss_factor_lookup
    ON loss_factor (loss_stage_id, species_id, producer_id, bird_program_id);


-- ---------------------------------------------------------------------------
-- Wing anatomy and grading
-- ---------------------------------------------------------------------------

CREATE TABLE wing_segment (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    slug                TEXT    NOT NULL,      -- 'drumette','flat','tip'
    label               TEXT    NOT NULL,
    per_wing_count      INTEGER NOT NULL DEFAULT 1,
    bone_in_grams       REAL,
    boneless_yield_pct  REAL,
    usually_sold_as_wing INTEGER NOT NULL DEFAULT 1,  -- tips: 0
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT,
    UNIQUE (species_id, slug)
);

-- Size grading is a mixing stage in disguise: it does not shuffle a bird's
-- two wings, it deliberately SEPARATES them when they differ in weight.
CREATE TABLE wing_grade (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    slug                TEXT    NOT NULL,      -- 'jumbo','large','medium'
    label               TEXT    NOT NULL,
    pieces_per_lb_lo    REAL,
    pieces_per_lb_hi    REAL,
    typical_program_id  INTEGER REFERENCES bird_program(id),
    source_id           INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, slug)
);


-- ---------------------------------------------------------------------------
-- The mixing cascade
-- ---------------------------------------------------------------------------

-- Ordered stages at which wings from different birds commingle. Mixing
-- starts at wing separation and only ever increases the pool. The pool size
-- at the point of draw determines expected distinct birds.
CREATE TABLE mixing_stage (
    id                  INTEGER PRIMARY KEY,
    slug                TEXT    NOT NULL UNIQUE,
    label               TEXT    NOT NULL,
    sequence            INTEGER NOT NULL UNIQUE,

    -- Pool size expressed in BIRDS represented at this stage.
    pool_birds_lo       INTEGER NOT NULL,
    pool_birds_mode     INTEGER NOT NULL,
    pool_birds_hi       INTEGER NOT NULL,

    -- 'random'    : passive commingling, wings shuffle
    -- 'separating': actively splits a bird's two wings (size grading)
    -- 'none'      : passthrough, preserves whatever pool arrived
    mixing_kind         TEXT    NOT NULL CHECK (mixing_kind IN
                            ('random','separating','none')),

    source_id           INTEGER NOT NULL REFERENCES source(id),
    confidence          TEXT    NOT NULL,
    description         TEXT    NOT NULL,

    CHECK (pool_birds_lo <= pool_birds_mode AND pool_birds_mode <= pool_birds_hi)
);

-- Named end-to-end supply chains: 'commodity_foodservice', 'local_butcher',
-- 'whole_bird_home'. Selecting one picks which mixing stages apply, which is
-- what moves the answer within the 6-12 band.
CREATE TABLE supply_chain (
    id              INTEGER PRIMARY KEY,
    slug            TEXT    NOT NULL UNIQUE,
    label           TEXT    NOT NULL,
    description     TEXT    NOT NULL,
    is_default      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE supply_chain_stage (
    supply_chain_id INTEGER NOT NULL REFERENCES supply_chain(id),
    mixing_stage_id INTEGER NOT NULL REFERENCES mixing_stage(id),
    -- Optional per-chain override of the stage's default pool size.
    pool_birds_override INTEGER,
    PRIMARY KEY (supply_chain_id, mixing_stage_id)
);


-- ---------------------------------------------------------------------------
-- Saved runs -- reproducibility
-- ---------------------------------------------------------------------------

CREATE TABLE run (
    id                  INTEGER PRIMARY KEY,
    created_at          TEXT    NOT NULL,
    wings_requested     INTEGER NOT NULL,
    wing_unit           TEXT    NOT NULL CHECK (wing_unit IN
                            ('whole_wing','segment')),
    species_id          INTEGER NOT NULL REFERENCES species(id),
    producer_id         INTEGER REFERENCES producer(id),
    bird_program_id     INTEGER REFERENCES bird_program(id),
    supply_chain_id     INTEGER REFERENCES supply_chain(id),
    include_farm_loss   INTEGER NOT NULL DEFAULT 0,

    -- Results
    birds_floor         REAL,   -- the hard minimum (wings / 2)
    birds_required      REAL,   -- after walking the loss chain backwards
    distinct_birds_mean REAL,   -- expected distinct birds actually represented
    distinct_birds_p05  REAL,
    distinct_birds_p95  REAL,
    iterations          INTEGER,
    db_version          TEXT
);

-- Per-stage audit trail. This is what the "show the reasoning?" prompt
-- unfolds -- one row per stage, in order, with the value used and its source.
CREATE TABLE run_step (
    id              INTEGER PRIMARY KEY,
    run_id          INTEGER NOT NULL REFERENCES run(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL,
    kind            TEXT    NOT NULL CHECK (kind IN ('loss','mixing')),
    stage_slug      TEXT    NOT NULL,
    stage_label     TEXT    NOT NULL,
    value_used      REAL    NOT NULL,
    running_total   REAL    NOT NULL,
    source_id       INTEGER REFERENCES source(id),
    confidence      TEXT,
    explanation     TEXT    NOT NULL
);

CREATE INDEX idx_run_step_run ON run_step (run_id, sequence);


-- ---------------------------------------------------------------------------
-- Convenience views
-- ---------------------------------------------------------------------------

-- National dressing yield, derived rather than stored, so it can never drift
-- out of sync with the NASS totals it comes from.
CREATE VIEW v_dressing_yield AS
SELECT
    s.slug              AS species,
    n.year,
    n.certified_rtc_lb,
    n.live_weight_lb,
    CAST(n.certified_rtc_lb AS REAL) / n.live_weight_lb AS dressing_yield,
    n.source_id
FROM national_slaughter_year n
JOIN species s ON s.id = n.species_id
WHERE n.live_weight_lb IS NOT NULL
  AND n.certified_rtc_lb IS NOT NULL;

-- Every statistic in the database with its citation attached, for the
-- "where did this number come from" drill-down.
CREATE VIEW v_cited_factors AS
SELECT
    ls.sequence,
    ls.slug         AS stage,
    ls.label        AS stage_label,
    ls.phase,
    ls.applies_to,
    lf.survive_lo,
    lf.survive_mode,
    lf.survive_hi,
    lf.confidence,
    src.title       AS source_title,
    src.publisher,
    src.url,
    src.published_on
FROM loss_factor lf
JOIN loss_stage ls  ON ls.id  = lf.loss_stage_id
JOIN source     src ON src.id = lf.source_id
WHERE lf.valid_to IS NULL
ORDER BY ls.sequence;
