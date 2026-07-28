-- counting-chicken-wings : "How many X does it take to produce Y?"
--
-- v1 answers this for broiler chickens and wings. The schema is deliberately
-- general so turkey, then other food domains, drop in as DATA rather than as
-- migrations. Nothing below hardcodes "chicken" or "wing".
--
-- Design rules, enforced by structure rather than convention:
--   1. Every numeric fact carries a source_id, NOT NULL. There is no way to
--      insert a statistic without saying where it came from.
--   2. Every estimated fact carries lo/mode/hi, never a bare point value.
--      Measured facts set all three equal and mark confidence='measured'.
--   3. Nothing is deleted. Superseded figures get valid_to set and stay
--      queryable, so an old run reproduces exactly.
--
-- The three-part model, identical across every domain:
--   FLOOR    - the hard arithmetic minimum of individuals
--   LOSS     - a chain of stages that raises the individuals required
--   MIXING   - a cascade of pooling that raises the DISTINCT individuals
--              actually represented in the portion you receive
--
-- Two yield modes:
--   countable  - discrete parts (wings, eggs). floor = ceil(n / units_per_ind)
--   continuous - mass or volume (milk, honey). floor = qty / yield_per_ind
-- Mixing applies identically to both.

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
                        'peer_reviewed',
                        'trade_body',     -- National Chicken Council
                        'trade_press',
                        'industry_spec',  -- equipment / packaging specs
                        'derived',        -- computed from other sources
                        'estimate'        -- our own reasoned estimate
                    )),
    notes           TEXT
);

-- Derived figures record their parents, so the audit trail can recurse
-- (e.g. dressing yield <- two NASS totals).
CREATE TABLE source_derivation (
    derived_source_id  INTEGER NOT NULL REFERENCES source(id),
    parent_source_id   INTEGER NOT NULL REFERENCES source(id),
    PRIMARY KEY (derived_source_id, parent_source_id)
);


-- ---------------------------------------------------------------------------
-- Domain taxonomy -- how the project grows
-- ---------------------------------------------------------------------------

-- 'poultry', later 'red_meat', 'dairy', 'produce', 'apiculture'.
-- Grouping only: no logic branches on domain.
CREATE TABLE domain (
    id              INTEGER PRIMARY KEY,
    slug            TEXT    NOT NULL UNIQUE,
    label           TEXT    NOT NULL,
    description     TEXT,
    active          INTEGER NOT NULL DEFAULT 1
);

-- The "X" in "how many X". An individual organism: a broiler, a turkey,
-- a dairy cow, an almond tree, a honeybee.
CREATE TABLE species (
    id                  INTEGER PRIMARY KEY,
    domain_id           INTEGER NOT NULL REFERENCES domain(id),
    slug                TEXT    NOT NULL UNIQUE,   -- 'broiler'
    common_name         TEXT    NOT NULL,          -- 'Broiler chicken'
    scientific_name     TEXT,
    -- Noun for one individual, used verbatim in generated prose:
    -- 'chicken', 'turkey', 'cow', 'bee', 'tree'.
    individual_noun     TEXT    NOT NULL,
    individual_plural   TEXT    NOT NULL,
    -- How this species is counted in official statistics, if at all.
    stat_category       TEXT,                      -- NASS 'Young Chickens'
    active              INTEGER NOT NULL DEFAULT 1
);

-- The "Y" in "produce Y". A wing, a breast, a gallon of milk, a jar of honey.
CREATE TABLE product (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    slug                TEXT    NOT NULL UNIQUE,   -- 'whole_wing'
    label               TEXT    NOT NULL,          -- 'Whole wing'
    label_plural        TEXT    NOT NULL,

    yield_mode          TEXT    NOT NULL CHECK (yield_mode IN
                            ('countable','continuous')),

    -- countable  : discrete parts per individual (2 wings per chicken).
    -- continuous : quantity per individual in unit_name (gallons per cow).
    -- lo/hi carry natural biological variation.
    units_per_individual_lo   REAL NOT NULL,
    units_per_individual_mode REAL NOT NULL,
    units_per_individual_hi   REAL NOT NULL,

    unit_name           TEXT    NOT NULL,          -- 'wing', 'gallon', 'lb'

    -- Which part of the individual this product actually comes from.
    -- Exists because product NAMES lie: a "boneless wing" is breast meat
    -- and contains no wing whatsoever. Storing the anatomical truth
    -- separately from the marketing name makes that queryable instead of
    -- leaving it as a footnote nobody reads.
    source_part         TEXT,                      -- 'wing', 'breast'
    -- The part the product's NAME claims it is, which is not always the
    -- part it comes from. A "boneless wing" names the wing and is made of
    -- breast, so named_part='wing' while source_part='breast'.
    named_part          TEXT,
    -- How many actual units of the NAMED part the product contains.
    -- 1.0 for a real wing, 0.0 for a boneless wing.
    named_part_content  REAL    NOT NULL DEFAULT 1.0
                            CHECK (named_part_content >= 0),
    -- For countable products only: is units_per_individual a hard anatomical
    -- constant? A chicken has exactly 2 wings -- that is what makes the
    -- floor a genuine floor rather than an average.
    is_anatomical_constant INTEGER NOT NULL DEFAULT 0,

    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT,

    CHECK (units_per_individual_lo <= units_per_individual_mode
       AND units_per_individual_mode <= units_per_individual_hi),
    CHECK (units_per_individual_lo > 0)
);

-- Sub-parts of a countable product: drumette / flat / tip of a wing.
-- Matters because a restaurant "wing" often means a SEGMENT, not a whole
-- wing, and that single ambiguity halves or doubles the answer.
CREATE TABLE product_segment (
    id                  INTEGER PRIMARY KEY,
    product_id          INTEGER NOT NULL REFERENCES product(id),
    slug                TEXT    NOT NULL,          -- 'drumette','flat','tip'
    label               TEXT    NOT NULL,
    per_product_count   REAL    NOT NULL DEFAULT 1,
    mass_grams          REAL,
    edible_yield_pct    REAL,
    -- Tips are usually diverted to stock/export/rendering, not sold as wings.
    sold_as_product     INTEGER NOT NULL DEFAULT 1,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT,
    UNIQUE (product_id, slug)
);

-- Production programs: small-bird vs big-bird broilers, dairy breeds, etc.
-- Drives product SIZE, and therefore how many individuals a given POUNDAGE
-- represents. Does not change a countable floor -- a distinction the UI
-- should state plainly.
CREATE TABLE production_program (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    slug                TEXT    NOT NULL UNIQUE,   -- 'small_bird','big_bird'
    label               TEXT    NOT NULL,
    -- Generic size measure; for broilers this is live weight in lb.
    size_lo             REAL,
    size_mode           REAL,
    size_hi             REAL,
    size_unit           TEXT,
    typical_market      TEXT,                      -- 'fast food','deboning'
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT
);


-- ---------------------------------------------------------------------------
-- Industry structure
-- ---------------------------------------------------------------------------

CREATE TABLE producer (
    id                  INTEGER PRIMARY KEY,
    domain_id           INTEGER NOT NULL REFERENCES domain(id),
    slug                TEXT    NOT NULL UNIQUE,   -- 'tyson'
    name                TEXT    NOT NULL,
    headquarters        TEXT,
    market_share_pct    REAL,
    throughput_per_week INTEGER,                   -- individuals processed
    facility_count      INTEGER,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    as_of_year          INTEGER,
    notes               TEXT
);

-- A processing facility: slaughter plant, dairy, creamery, mill.
CREATE TABLE facility (
    id                  INTEGER PRIMARY KEY,
    producer_id         INTEGER REFERENCES producer(id),
    regulator_id        TEXT    UNIQUE,            -- FSIS establishment no.
    name                TEXT    NOT NULL,
    state               TEXT,
    city                TEXT,
    program_id          INTEGER REFERENCES production_program(id),
    throughput_per_day  INTEGER,
    -- Does the first mixing point happen here? For wings this is the
    -- cut-up line -- the moment the product separates from the individual.
    does_separation     INTEGER,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT
);


-- ---------------------------------------------------------------------------
-- Observed statistics
--
-- These tables are intentionally domain-shaped. Slaughter statistics have
-- genuinely different columns from milk production statistics, and forcing
-- them into one generic key/value table would destroy queryability for no
-- benefit. New domains add their own observation tables; the MODEL tables
-- above and below stay generic.
-- ---------------------------------------------------------------------------

CREATE TABLE slaughter_stat_year (
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

-- Regional size variation. For broilers this is where production programs
-- become visible in public data: Ohio ~4.5 lb vs North Carolina ~8.6 lb.
CREATE TABLE regional_size_stat (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    region              TEXT    NOT NULL,          -- state code or name
    year                INTEGER NOT NULL,
    month               INTEGER,                   -- NULL = annual
    avg_size            REAL    NOT NULL,
    size_unit           TEXT    NOT NULL,
    volume              INTEGER,
    volume_unit         TEXT,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, region, year, month)
);

-- Grow-out / husbandry performance by year.
CREATE TABLE husbandry_stat_year (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    year                INTEGER NOT NULL,
    cycle_days          REAL,                      -- market age
    end_size            REAL,                      -- market weight
    size_unit           TEXT,
    feed_conversion     REAL,
    mortality_pct       REAL,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, year)
);


-- ---------------------------------------------------------------------------
-- The loss chain -- raises INDIVIDUALS REQUIRED
-- ---------------------------------------------------------------------------

CREATE TABLE loss_stage (
    id              INTEGER PRIMARY KEY,
    domain_id       INTEGER NOT NULL REFERENCES domain(id),
    slug            TEXT    NOT NULL UNIQUE,
    label           TEXT    NOT NULL,
    sequence        INTEGER NOT NULL,        -- origin -> plate ordering
    -- Free text rather than CHECK: phases differ across domains and we do
    -- not want a schema migration to add a dairy pipeline.
    phase           TEXT    NOT NULL,

    applies_to      TEXT    NOT NULL CHECK (applies_to IN (
                        'individual',  -- removes whole individuals
                        'product',     -- removes/downgrades product units
                        'mass'         -- scales weight only, not counts
                    )),
    -- Whether a stage counts depends on the question. Farm mortality is the
    -- clearest case: it matters for "how many chicks were placed" but not
    -- for "whose wings are on my plate".
    optional        INTEGER NOT NULL DEFAULT 0,
    default_enabled INTEGER NOT NULL DEFAULT 1,
    description     TEXT    NOT NULL,
    notes           TEXT,
    UNIQUE (domain_id, sequence)
);

-- Survival fractions, triangular lo/mode/hi so Monte Carlo needs no extra
-- config. A stage may hold several competing values (by producer, program,
-- region, year); resolution is by specificity at query time.
CREATE TABLE loss_factor (
    id                  INTEGER PRIMARY KEY,
    loss_stage_id       INTEGER NOT NULL REFERENCES loss_stage(id),
    species_id          INTEGER NOT NULL REFERENCES species(id),
    product_id          INTEGER REFERENCES product(id),
    producer_id         INTEGER REFERENCES producer(id),
    program_id          INTEGER REFERENCES production_program(id),
    region              TEXT,
    year                INTEGER,

    -- SURVIVING fraction, not loss fraction: 0.9955 means 0.45% lost.
    -- Values > 1.0 are legal and meaningful (marinade pickup adds mass).
    survive_lo          REAL    NOT NULL,
    survive_mode        REAL    NOT NULL,
    survive_hi          REAL    NOT NULL,

    confidence          TEXT    NOT NULL CHECK (confidence IN (
                            'measured',   -- reported directly by government
                            'derived',    -- computed from measured figures
                            'study',      -- peer-reviewed, may not generalize
                            'industry',   -- trade rule of thumb
                            'estimate'    -- our reasoning, flagged as such
                        )),
    source_id           INTEGER NOT NULL REFERENCES source(id),
    valid_from          TEXT,
    valid_to            TEXT,            -- NULL = current
    notes               TEXT,

    CHECK (survive_lo <= survive_mode AND survive_mode <= survive_hi),
    CHECK (survive_lo > 0)
);

CREATE INDEX idx_loss_factor_lookup
    ON loss_factor (loss_stage_id, species_id, producer_id, program_id);

-- Size/quality grading. Modeled separately from loss because grading is
-- also a MIXING event: it does not shuffle an individual's units, it
-- deliberately separates them when they differ in size.
CREATE TABLE product_grade (
    id                  INTEGER PRIMARY KEY,
    product_id          INTEGER NOT NULL REFERENCES product(id),
    slug                TEXT    NOT NULL,          -- 'jumbo','large','medium'
    label               TEXT    NOT NULL,
    units_per_lb_lo     REAL,
    units_per_lb_hi     REAL,
    typical_program_id  INTEGER REFERENCES production_program(id),
    source_id           INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (product_id, slug)
);


-- ---------------------------------------------------------------------------
-- The mixing cascade -- raises DISTINCT INDIVIDUALS REPRESENTED
-- ---------------------------------------------------------------------------

-- Ordered points at which product from different individuals commingles.
-- Mixing begins the instant the product separates from the individual and
-- only ever increases the pool.
CREATE TABLE mixing_stage (
    id                  INTEGER PRIMARY KEY,
    domain_id           INTEGER NOT NULL REFERENCES domain(id),
    slug                TEXT    NOT NULL UNIQUE,
    label               TEXT    NOT NULL,
    sequence            INTEGER NOT NULL,

    -- Pool size expressed in INDIVIDUALS represented at this stage.
    pool_lo             INTEGER NOT NULL,
    pool_mode           INTEGER NOT NULL,
    pool_hi             INTEGER NOT NULL,

    -- 'random'     : passive commingling
    -- 'separating' : actively splits one individual's units (size grading)
    -- 'none'       : passthrough, preserves the pool that arrived
    mixing_kind         TEXT    NOT NULL CHECK (mixing_kind IN
                            ('random','separating','none')),

    source_id           INTEGER NOT NULL REFERENCES source(id),
    confidence          TEXT    NOT NULL,
    description         TEXT    NOT NULL,

    CHECK (pool_lo <= pool_mode AND pool_mode <= pool_hi),
    UNIQUE (domain_id, sequence)
);

-- Named end-to-end routes: 'commodity_foodservice', 'local_butcher',
-- 'whole_bird_home'. Choosing one selects which mixing stages apply, and
-- that is what moves the answer within the floor..n band.
CREATE TABLE supply_chain (
    id              INTEGER PRIMARY KEY,
    domain_id       INTEGER NOT NULL REFERENCES domain(id),
    slug            TEXT    NOT NULL UNIQUE,
    label           TEXT    NOT NULL,
    description     TEXT    NOT NULL,
    is_default      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE supply_chain_stage (
    supply_chain_id INTEGER NOT NULL REFERENCES supply_chain(id),
    mixing_stage_id INTEGER NOT NULL REFERENCES mixing_stage(id),
    pool_override   INTEGER,                       -- per-chain pool size
    PRIMARY KEY (supply_chain_id, mixing_stage_id)
);


-- ---------------------------------------------------------------------------
-- Learning centre
-- ---------------------------------------------------------------------------

-- Points of fact, surfaced in the learning centre and alongside results as
-- the user works through a question. Like everything else here, a fact
-- cannot exist without a citation.
CREATE TABLE fact (
    id              INTEGER PRIMARY KEY,
    slug            TEXT    NOT NULL UNIQUE,
    domain_id       INTEGER REFERENCES domain(id),
    headline        TEXT    NOT NULL,
    body            TEXT    NOT NULL,
    -- 'result'   : shown next to an answer
    -- 'learning' : learning centre only
    -- 'both'     : eligible for either
    placement       TEXT    NOT NULL CHECK (placement IN
                        ('result','learning','both')),
    -- 1-5. The UI leads with high-surprise facts, because the
    -- counterintuitive ones are what keep people reading.
    surprise        INTEGER NOT NULL DEFAULT 3
                        CHECK (surprise BETWEEN 1 AND 5),
    source_id       INTEGER NOT NULL REFERENCES source(id),

    CHECK (length(headline) > 0 AND length(body) > 0)
);

CREATE INDEX idx_fact_placement ON fact (placement, surprise DESC);


-- ---------------------------------------------------------------------------
-- Saved runs -- reproducibility
-- ---------------------------------------------------------------------------

CREATE TABLE run (
    id                  INTEGER PRIMARY KEY,
    created_at          TEXT    NOT NULL,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    product_id          INTEGER NOT NULL REFERENCES product(id),
    quantity            REAL    NOT NULL,
    -- For countable products: 'unit' (whole wings) or 'segment' (pieces).
    quantity_basis      TEXT    NOT NULL,
    producer_id         INTEGER REFERENCES producer(id),
    program_id          INTEGER REFERENCES production_program(id),
    supply_chain_id     INTEGER REFERENCES supply_chain(id),
    include_optional_losses INTEGER NOT NULL DEFAULT 0,

    -- Results
    floor_individuals       REAL,   -- hard minimum
    required_individuals    REAL,   -- after walking the loss chain backwards
    distinct_mean           REAL,   -- expected distinct individuals
    distinct_p05            REAL,
    distinct_p95            REAL,
    iterations              INTEGER,
    db_version              TEXT
);

-- Per-stage audit trail. This is what the "show the reasoning" toggle
-- unfolds: one row per stage, in order, value used, and citation.
CREATE TABLE run_step (
    id              INTEGER PRIMARY KEY,
    run_id          INTEGER NOT NULL REFERENCES run(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL,
    kind            TEXT    NOT NULL CHECK (kind IN ('floor','loss','mixing')),
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
-- Views
-- ---------------------------------------------------------------------------

-- Dressing yield derived, never stored, so it cannot drift from the NASS
-- totals it comes from.
CREATE VIEW v_dressing_yield AS
SELECT
    sp.slug             AS species,
    s.year,
    s.certified_rtc_lb,
    s.live_weight_lb,
    CAST(s.certified_rtc_lb AS REAL) / s.live_weight_lb AS dressing_yield,
    s.source_id
FROM slaughter_stat_year s
JOIN species sp ON sp.id = s.species_id
WHERE s.live_weight_lb IS NOT NULL
  AND s.certified_rtc_lb IS NOT NULL;

-- Every current loss factor with its citation attached, for the
-- "where did this number come from" drill-down.
CREATE VIEW v_cited_factors AS
SELECT
    d.slug          AS domain,
    sp.slug         AS species,
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
JOIN species    sp  ON sp.id  = lf.species_id
JOIN domain     d   ON d.id   = ls.domain_id
JOIN source     src ON src.id = lf.source_id
WHERE lf.valid_to IS NULL
ORDER BY d.slug, ls.sequence;

-- Coverage dashboard: what is actually populated per domain. Drives the
-- "add to it every day" workflow -- shows at a glance where the gaps are.
CREATE VIEW v_domain_coverage AS
SELECT
    d.slug                          AS domain,
    COUNT(DISTINCT sp.id)           AS species_count,
    COUNT(DISTINCT p.id)            AS product_count,
    COUNT(DISTINCT ls.id)           AS loss_stage_count,
    COUNT(DISTINCT ms.id)           AS mixing_stage_count
FROM domain d
LEFT JOIN species      sp ON sp.domain_id = d.id
LEFT JOIN product      p  ON p.species_id = sp.id
LEFT JOIN loss_stage   ls ON ls.domain_id = d.id
LEFT JOIN mixing_stage ms ON ms.domain_id = d.id
GROUP BY d.slug;
