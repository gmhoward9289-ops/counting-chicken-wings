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

-- ---------------------------------------------------------------------------
-- Countries
-- ---------------------------------------------------------------------------

-- Exists because "region" was a bare TEXT column with no notion of country,
-- so loading Israel beside Alabama would silently corrupt any total that
-- sums regions. Added when the project took on a second country rather than
-- retrofitted after the first bad total.
--
-- Population lives here because per-capita consumption is the whole point of
-- a cross-country comparison, and a per-capita figure computed against the
-- wrong year's population is wrong in a way nobody notices.
CREATE TABLE country (
    id                  INTEGER PRIMARY KEY,
    iso3                TEXT    NOT NULL UNIQUE,   -- 'USA', 'ISR'
    name                TEXT    NOT NULL,
    -- Reporting conventions differ by country and are the likeliest source
    -- of a silently wrong comparison: the US reports pounds, most of the
    -- world reports kilograms. Recorded so a loader can normalise
    -- deliberately rather than a query assuming.
    native_mass_unit    TEXT    NOT NULL DEFAULT 'lb',
    native_currency     TEXT,
    population          INTEGER,
    population_year     INTEGER,
    source_id           INTEGER REFERENCES source(id),
    notes               TEXT
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

    -- Picker name, 'Source: product' ('Chicken: Bone-in wing'). Only for
    -- lists that mix species; prose keeps using label, which has to read
    -- mid-sentence ("a boneless wing contains no wing meat"). NULL falls
    -- back to label.
    display_name        TEXT,

    yield_mode          TEXT    NOT NULL CHECK (yield_mode IN
                            ('countable','continuous','recurring')),

    -- countable  : discrete parts per individual (2 wings per chicken).
    -- continuous : quantity per individual in unit_name (gallons per cow).
    -- recurring  : produced repeatedly over time (eggs, milk, honey).
    --              units_per_individual is then a RATE, meaningless without
    --              yield_period_days below.
    -- lo/hi carry natural biological variation.
    units_per_individual_lo   REAL NOT NULL,
    units_per_individual_mode REAL NOT NULL,
    units_per_individual_hi   REAL NOT NULL,

    -- The window units_per_individual is measured over. NULL for countable
    -- and continuous products, where the figure is timeless: a chicken has
    -- two wings today, tomorrow, and always.
    --
    -- Required for 'recurring', because "288 eggs per hen" is not a fact
    -- until you say per what. 365 here means the rate is annual.
    yield_period_days   REAL,

    -- Hard physiological ceiling on units per individual per day. This is
    -- what makes a recurring product's floor a real floor rather than an
    -- average, and it is the direct analogue of "a chicken has two wings".
    --
    -- A hen's ovulation cycle runs slightly over 24 hours, so she lays at
    -- most about one egg a day. Consequence: twelve eggs collected on a
    -- single day came from twelve DIFFERENT hens, necessarily. Unlike wings,
    -- where mixing pushes the answer up from the floor, here the floor and
    -- the ceiling meet and there is no room for the supply chain to move it.
    max_units_per_day   REAL    CHECK (max_units_per_day IS NULL
                                       OR max_units_per_day > 0),

    -- The window to answer in when the question does not name one. NULL
    -- means "the product's own yield_period_days", which is the honest
    -- default for anything seasonal.
    --
    -- This column exists because a single global default was wrong the
    -- moment a second recurring product landed. One day is right for eggs --
    -- "a dozen eggs" means a carton gathered together -- and absurd for
    -- maple, whose sap runs for about six weeks a year: a one-day window
    -- asked how many trees could be tapped, boiled and bottled between
    -- breakfast and supper, and answered 194.
    default_window_days REAL    CHECK (default_window_days IS NULL
                                       OR default_window_days > 0),

    -- What to call this product's rate in prose: 'laying rate', 'sap flow'.
    -- The floor_note lesson again. The CLI and both front ends said "at the
    -- real LAYING rate" for every recurring product, so asking about maple
    -- syrup got a sentence about a tree's laying rate. Data cannot narrate
    -- the wrong species.
    rate_label          TEXT,

    -- Why the per-day ceiling is physiology rather than estimation, in this
    -- species' own words. Only meaningful where max_units_per_day is set,
    -- and the schema enforces that rather than trusting prose to notice.
    cap_note            TEXT,

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

    -- How many physically-indivisible mixing sub-units make up ONE of this
    -- product's units, when the product is a homogenate ground/blended at a
    -- grain finer than the unit itself. NULL (the default, and correct for
    -- every countable/atomic product) means the unit IS the atomic thing the
    -- mixing draw assumes -- true for a wing, an egg, a stigma: each is one
    -- indivisible piece traceable to exactly one individual, so "1 unit = 1
    -- draw" is physically correct.
    --
    -- Grinding breaks that assumption. A ground-beef patty is not one intact
    -- piece from one animal; it is a scoop of a slurry that was already
    -- shredded and blended from hundreds of animals' trim before it was ever
    -- formed. Drawing "1 unit = 1 draw" for a patty silently treats it like a
    -- wing -- one atomic thing that can trace to at most one individual --
    -- which is the exact category error a 2026-08 audit caught: the model
    -- reported "at least 1 animal" as the PATTY'S headline answer, when the
    -- only measured figure this corpus holds (Hu et al. 2012, DNA
    -- mark-recapture) puts a whole grind BATCH at 411-1,367 animals. A patty
    -- drawn from that batch at the batch's real mixing grain is not one
    -- draw; it is thousands, and the same pooling formula that gives "6
    -- chickens" for wings gives "most of the batch" once it is asked at the
    -- right granularity.
    --
    -- This is set once per product, in the finer unit (e.g. grind particles
    -- per patty), NOT re-derived from mass here -- the arithmetic belongs in
    -- the taxonomy file next to its citation, same as every other figure in
    -- this schema.
    mixing_subunits_per_unit REAL CHECK (mixing_subunits_per_unit IS NULL
                                          OR mixing_subunits_per_unit > 1),

    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT,

    CHECK (units_per_individual_lo <= units_per_individual_mode
       AND units_per_individual_mode <= units_per_individual_hi),
    CHECK (units_per_individual_lo > 0),

    -- A recurring rate without its period is the exact bug this mode exists
    -- to prevent, so the schema refuses it outright rather than letting a
    -- silent default decide what "288 eggs per hen" means.
    --
    -- The IS NOT NULL is load-bearing, not belt-and-braces. Written as just
    -- `yield_period_days > 0`, a NULL period makes the comparison NULL, the
    -- whole expression NULL, and SQLite passes any CHECK that is not
    -- explicitly FALSE -- so the constraint silently allowed exactly what it
    -- was added to forbid. Caught by testing the rejection rather than
    -- assuming it.
    CHECK (yield_mode != 'recurring'
           OR (yield_period_days IS NOT NULL AND yield_period_days > 0)),
    CHECK (yield_mode = 'recurring' OR max_units_per_day IS NULL),

    -- A window and a rate noun only mean anything for a product produced
    -- over time, and a recurring product must carry a rate noun or the
    -- prose falls back to somebody else's biology.
    CHECK (yield_mode = 'recurring' OR default_window_days IS NULL),
    CHECK (yield_mode != 'recurring' OR rate_label IS NOT NULL),
    CHECK (yield_mode = 'recurring' OR rate_label IS NULL),

    -- A cap_note explains a cap. Without one there is nothing to explain,
    -- and a note claiming a ceiling the data does not record would be the
    -- model stating what it cannot support.
    CHECK (cap_note IS NULL OR max_units_per_day IS NOT NULL)
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

-- What share of one individual's mass this product actually is.
--
-- The number every resource and economic figure has to be multiplied by before
-- it can be charged to a product. A dozen wings does not carry six birds'
-- worth of anything: the wings are ~7.3% of live weight and the rest of each
-- bird fed other people, so charging the whole bird overstates by ~14x.
--
-- IT LIVES IN THE CORPUS BECAUSE IT IS A STATISTIC. It used to be one line of
-- Python -- `0.073 if slug == 'whole_wing' else 0.23` -- which is to say the
-- chicken-BREAST share was applied to all eleven non-wing products, including
-- a gallon of maple syrup and a silk dress. That is the exact failure CLAUDE.md
-- names: a figure hardcoded in a module bypasses the citation audit, so nobody
-- could see that ten of those twelve values had no source because they were not
-- facts about anything.
--
-- A product with NO ROW HERE has no published mass share, and that is a state
-- the API has to render as "we do not have this" rather than fill in. Silk and
-- syrup are not mass-allocated fractions of an animal in the first place; the
-- honest answer for them is not a smaller number, it is no number.
CREATE TABLE product_mass_share (
    id                  INTEGER PRIMARY KEY,
    product_id          INTEGER NOT NULL UNIQUE REFERENCES product(id),
    -- Fraction of one individual, in the basis named below. Bounded above by
    -- 1: a product cannot be more of an animal than the animal.
    mass_share          REAL    NOT NULL
                            CHECK (mass_share > 0 AND mass_share <= 1),
    -- What the share is OF: 'live_weight', 'carcass_weight'. The eight-strain
    -- yield paper reports wings at 9.1-10.2% of CARCASS and 6.7-7.3% of LIVE
    -- weight, and quoting one as the other is a 40% error with no symptom.
    basis               TEXT    NOT NULL,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT
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
    country_id               INTEGER NOT NULL REFERENCES country(id),
    year                    INTEGER NOT NULL,
    head_slaughtered        INTEGER,
    live_weight_lb          INTEGER,
    certified_rtc_lb        INTEGER,
    avg_live_weight_lb      REAL,
    postmortem_condemn_pct  REAL,
    postmortem_condemn_lb   INTEGER,
    source_id               INTEGER NOT NULL REFERENCES source(id),
    -- country_id belongs in the key. Without it a second country's broiler
    -- row for a year the US already has is rejected outright, so the table
    -- could hold exactly one country no matter what country_id said.
    UNIQUE (species_id, country_id, year)
);

-- Regional size variation. For broilers this is where production programs
-- become visible in public data: Ohio ~4.5 lb vs North Carolina ~8.6 lb.
CREATE TABLE regional_size_stat (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    country_id           INTEGER NOT NULL REFERENCES country(id),
    region              TEXT    NOT NULL,          -- state code or name
    year                INTEGER NOT NULL,
    month               INTEGER,                   -- NULL = annual
    avg_size            REAL    NOT NULL,
    size_unit           TEXT    NOT NULL,
    volume              INTEGER,
    volume_unit         TEXT,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    -- Region names are not globally unique, so country_id is part of identity
    -- here, not just an attribute hanging off it.
    UNIQUE (species_id, country_id, region, year, month)
);

-- Broilers PRODUCED by region, from the NASS Production and Value summary.
--
-- Deliberately separate from regional_size_stat, which holds SLAUGHTER data.
-- The two publications count different populations over different periods
-- (produced Dec 1 - Nov 30 vs young chickens slaughtered per calendar year,
-- the latter also covering roasters and capons), so merging them into one
-- table would invite exactly the wrong query -- summing two overlapping
-- measures of the same birds.
--
-- Carrying both is what lets the project cross-check itself: dividing
-- live_weight_klb by head_thousands reproduces the slaughter report's state
-- average live weight from an independent survey.
--
-- region = 'United States' holds the national row, as the source presents it.
CREATE TABLE regional_production_year (
    id                      INTEGER PRIMARY KEY,
    species_id              INTEGER NOT NULL REFERENCES species(id),
    country_id               INTEGER NOT NULL REFERENCES country(id),
    region                  TEXT    NOT NULL,
    year                    INTEGER NOT NULL,
    head_thousands          INTEGER,
    live_weight_klb         INTEGER,
    value_kusd              INTEGER,
    -- Stored rather than derived in a view because it is the cross-check
    -- itself: a test asserts it matches regional_size_stat.
    derived_live_weight_lb  REAL,
    source_id               INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, country_id, region, year)
);

CREATE INDEX idx_regional_production_region
    ON regional_production_year (region, year);

-- The Production and Value summary's own multi-state aggregates: the rows
-- NASS publishes for the states it will not name individually. In 2025 that
-- is "California, Tennessee, and West Virginia" as one combined line, and
-- "Other States" -- fourteen states, every one named in the footnote --
-- as another.
--
-- A separate table rather than rows in regional_production_year, because an
-- aggregate is a different claim from a state figure: it has members, its
-- membership CHANGES BY YEAR (Florida was published individually in 2024
-- and folded into Other States in 2025), and any query that joins regions
-- to states by name must never meet one. What makes these rows trustworthy
-- is arithmetic: states + aggregates reproduces the published United States
-- total exactly, for head, pounds and dollars in both years -- the parser
-- refuses to emit them otherwise, and a test asserts it again from here.
--
-- Splitting an aggregate across its members would be inventing data. These
-- rows exist to be shown AS aggregates -- a real cited figure for exactly
-- the states the map cannot colour -- never to be allocated.
CREATE TABLE regional_production_aggregate (
    id                      INTEGER PRIMARY KEY,
    species_id              INTEGER NOT NULL REFERENCES species(id),
    country_id              INTEGER NOT NULL REFERENCES country(id),
    label                   TEXT    NOT NULL,  -- as the source prints it
    year                    INTEGER NOT NULL,
    -- Comma-separated member state names, straight from the source's own
    -- footnote. Data, not presentation: the API splits it so the page can
    -- say WHICH states a figure covers.
    members                 TEXT    NOT NULL,
    head_thousands          INTEGER,
    live_weight_klb         INTEGER,
    value_kusd              INTEGER,
    -- Production pounds over head, same derivation regional_production_year
    -- stores. Grades `derived`: real arithmetic on measured figures, but a
    -- weight NASS never published -- the API says so wherever it is shown.
    derived_live_weight_lb  REAL,
    source_id               INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, country_id, label, year)
);


-- Broiler presence and scale for every state, from the Census of
-- Agriculture. Separate from both survey tables because it is a different
-- programme on a different cadence measuring a different thing.
--
-- Its reason for existing is coverage: the annual survey suppresses states
-- with too few operations and caps out at 22, while the census publishes all
-- 50 with nothing withheld. Anything that needs "does this state raise
-- broilers at all" should read here; anything that needs a yearly series
-- should not.
CREATE TABLE regional_census_stat (
    id              INTEGER PRIMARY KEY,
    species_id      INTEGER NOT NULL REFERENCES species(id),
    country_id       INTEGER NOT NULL REFERENCES country(id),
    region          TEXT    NOT NULL,
    census_year     INTEGER NOT NULL,
    sales_head      INTEGER,
    operations      INTEGER,
    inventory       INTEGER,
    source_id       INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, country_id, region, census_year)
);


-- Output, value and inventory as a country actually publishes them.
--
-- Exists because Israel does not fit the tables above, and forcing it in
-- would have produced a wrong answer that looked right. Every US table here
-- bakes American reporting into its column names -- live_weight_lb,
-- certified_rtc_lb, value_kusd -- and assumes head slaughtered is available,
-- because for NASS it always is. Israel's CBS publishes neither: chapter 21
-- reports broiler output in tonnes and NIS, and an end-of-year flock count,
-- and no table anywhere carries head slaughtered per year.
--
-- Two mappings were available and both are wrong:
--
--   slaughter_stat_year.certified_rtc_lb  -- would assert that CBS's
--       "agricultural output" is ready-to-cook weight. It may be live
--       weight; the publication does not say, and guessing decides an
--       answer for the reader.
--   regional_production_year.value_kusd   -- would need an exchange rate,
--       which is a figure, which needs a citation we do not have.
--
-- So the measure and the unit are stored as data instead of implied by a
-- column name. A query must read `unit` to interpret `value`, which is the
-- point: no cross-country arithmetic can happen by accident.
--
-- region NULL means the national figure. Non-NULL is subnational, and Israel
-- does have subnational poultry data -- districts and regional councils --
-- so a choropleth has a genuine counterpart rather than a blank panel.
CREATE TABLE output_stat_year (
    id              INTEGER PRIMARY KEY,
    species_id      INTEGER NOT NULL REFERENCES species(id),
    country_id      INTEGER NOT NULL REFERENCES country(id),
    region          TEXT,                      -- NULL = national total
    -- The hierarchy the publisher uses, so a caller can count leaves without
    -- string-matching prose. Israel's table nests regional councils inside
    -- districts inside a grand total, and counting all three levels as
    -- "regions" would claim 55 Israeli regions against 23 US states -- more
    -- granularity than exists, by double-counting the aggregates.
    --
    -- 'province' added for Canada: StatCan reports ten actual provinces,
    -- which are a different concept from Israel's regional councils and
    -- deserve their own word rather than being forced into 'council'.
    -- Canada's Atlantic region -- a StatCan-defined aggregate of four
    -- provinces, each individually suppressed for confidentiality -- reuses
    -- 'district' rather than adding a second new value, because it is the
    -- same shape as Israel's district-of-councils grouping: an aggregate
    -- that sits between the national total and the named leaves.
    region_level    TEXT CHECK (region_level IN
                        ('total','district','council','province')),
    year            INTEGER NOT NULL,
    measure         TEXT    NOT NULL CHECK (measure IN (
                        'meat_output',      -- output of meat, per the source
                        'output_value',     -- value of that output
                        'inventory_eoy',    -- standing flock, end of year
                        'marketed',         -- quantity marketed, not produced
                        'head_slaughtered', -- throughput. NOT inventory
                        -- Chicks supplied by breeding operations. A throughput
                        -- PROXY and not throughput itself: grow-out mortality
                        -- sits between a chick placed and a bird slaughtered,
                        -- and the model already carries a factor for it. Its
                        -- value is as an independent check on a head count
                        -- that has only one source.
                        'chicks_placed',
                        -- Operations, not animals. Counted here because it is
                        -- how two industry bodies corroborate each other.
                        'grower_count',
                        -- Production-to-supply ratio, a percentage. Added
                        -- for the UK, whose DEFRA-published annual figure
                        -- answers the "self-sufficiency / import share"
                        -- question ISRAEL-PLAN.md flagged as open (Israel is
                        -- an unusual net-surplus producer; the UK is the
                        -- more typical net-importer case). Stored as its own
                        -- measure rather than derived, because DEFRA
                        -- publishes it directly -- deriving one from
                        -- production and consumption we do not otherwise
                        -- hold would be inventing a step nobody asked for.
                        'self_sufficiency_ratio'
                    )),
    value           REAL,
    unit            TEXT    NOT NULL,          -- 'tonnes','ILS_million','thousand_head'
    -- Added when the table stopped being government-only. Israel's head count
    -- comes from a named industry official via the press, not from CBS, and a
    -- reader must be able to ask for the government-only picture and get it --
    -- so the grade is a column and "government figures only" is a WHERE
    -- clause rather than a promise in a comment. Same vocabulary as
    -- loss_factor.confidence, deliberately: one grade scale for the project.
    confidence      TEXT    NOT NULL DEFAULT 'measured' CHECK (confidence IN
                        ('measured','derived','study','industry','estimate')),
    -- The source's own asterisk. CBS marks 2024 provisional, and a figure
    -- that may be revised should not be quoted as final.
    provisional     INTEGER NOT NULL DEFAULT 0,
    -- Withheld by the publisher: CBS uses "-" and ". ." exactly as NASS
    -- does. A suppressed row is presence without volume, which the map
    -- already knows how to render -- so it is a row with no value, never a
    -- zero and never a missing row.
    suppressed      INTEGER NOT NULL DEFAULT 0,
    source_id       INTEGER NOT NULL REFERENCES source(id),
    notes           TEXT,
    CHECK (suppressed = 1 OR value IS NOT NULL)
);

-- COALESCE because region is nullable and SQLite treats NULLs as distinct in
-- a UNIQUE constraint, which would let the national row load twice.
CREATE UNIQUE INDEX idx_output_stat_identity
    ON output_stat_year (
        species_id, country_id, COALESCE(region, ''), year, measure
    );


-- Average weight per bird, derived rather than stored, so it cannot drift
-- from the two figures it comes from -- the same reasoning as
-- v_dressing_yield.
--
-- This is the cross-check that makes Israel's industry head count believable.
-- CBS measured 600,072 tonnes of broiler output for 2024 and never published a
-- bird count; a named industry official put the flock's throughput at 260
-- million birds a year and never mentioned tonnage. Divide one by the other
-- and you get ~2.3 kg a bird, which is what a 40-day broiler weighs. Two
-- sources that were not derived from each other, agreeing.
--
-- confidence is the WEAKER of the two parents, never the better one. A figure
-- computed from an industry estimate is an industry-grade figure no matter how
-- well-measured its other half is.
--
-- THE YEARS DO NOT LINE UP, and the view says so rather than hiding it. CBS
-- publishes output for 2024, 2023, 2020, 2010 and 2000; the head figure is a
-- 2025 industry statement with no year of its own. So each head figure is
-- paired with the NEAREST output year and `year_gap` is returned alongside.
-- A same-year pairing would have been cleaner and would have required
-- pretending the interview was about a CBS reporting year.
CREATE VIEW v_output_derived_weight AS
SELECT
    c.iso3,
    sp.slug                                     AS species,
    o.year                                      AS head_year,
    t.year                                      AS output_year,
    ABS(t.year - o.year)                        AS year_gap,
    t.value                                     AS output_tonnes,
    o.value                                     AS head_thousands,
    (t.value * 1000.0) / (o.value * 1000.0)     AS kg_per_head,
    CASE WHEN t.confidence = 'measured' AND o.confidence = 'measured'
              AND t.year = o.year
         THEN 'derived' ELSE
        CASE WHEN (CASE t.confidence WHEN 'measured' THEN 1 WHEN 'derived'
                    THEN 2 WHEN 'study' THEN 3 WHEN 'industry' THEN 4
                    ELSE 5 END)
                 >= (CASE o.confidence WHEN 'measured' THEN 1 WHEN 'derived'
                      THEN 2 WHEN 'study' THEN 3 WHEN 'industry' THEN 4
                      ELSE 5 END)
             THEN t.confidence ELSE o.confidence END
    END                                         AS confidence,
    t.source_id                                 AS output_source_id,
    o.source_id                                 AS head_source_id
FROM output_stat_year o
JOIN output_stat_year t
  ON t.country_id = o.country_id
 AND t.species_id = o.species_id
 AND t.measure    = 'meat_output'
 AND t.region IS NULL
 -- Nearest output year to this head figure, ties broken toward the later one.
 AND ABS(t.year - o.year) = (
        SELECT MIN(ABS(t2.year - o.year)) FROM output_stat_year t2
        WHERE t2.country_id = o.country_id AND t2.species_id = o.species_id
          AND t2.measure = 'meat_output' AND t2.region IS NULL
     )
JOIN country c  ON c.id  = o.country_id
JOIN species sp ON sp.id = o.species_id
WHERE o.measure = 'head_slaughtered'
  AND o.region IS NULL
  AND o.value > 0
  AND t.value > 0;


-- Grow-out / husbandry performance by year.
CREATE TABLE husbandry_stat_year (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    country_id           INTEGER NOT NULL REFERENCES country(id),
    year                INTEGER NOT NULL,
    cycle_days          REAL,                      -- market age
    end_size            REAL,                      -- market weight
    size_unit           TEXT,
    feed_conversion     REAL,
    mortality_pct       REAL,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    UNIQUE (species_id, country_id, year)
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

-- Loss stages are NOT independent of one another in reality -- rough
-- catching and loading raises wing damage, grading trim loss, AND
-- transport DOA together, because all three load on the same latent
-- handling-quality of that particular load. Sampling every stage
-- independently in the Monte Carlo (#77) let errors partially cancel at
-- roughly sqrt(n), understating the reported band. `rho` is itself an
-- estimate -- the point is to stop asserting zero correlation, not to
-- claim a calibrated figure -- so it carries a confidence grade and a
-- citation exactly like a loss_factor, rather than living as a bare
-- constant in Python.
CREATE TABLE loss_correlation_group (
    id              INTEGER PRIMARY KEY,
    slug            TEXT    NOT NULL UNIQUE,
    label           TEXT    NOT NULL,
    description     TEXT,
    rho             REAL    NOT NULL CHECK (rho >= 0 AND rho < 1),
    confidence      TEXT    NOT NULL CHECK (confidence IN (
                        'measured', 'derived', 'study', 'industry', 'estimate'
                    )),
    source_id       INTEGER NOT NULL REFERENCES source(id),
    notes           TEXT
);

CREATE TABLE loss_correlation_group_stage (
    group_id        INTEGER NOT NULL REFERENCES loss_correlation_group(id),
    loss_stage_id   INTEGER NOT NULL REFERENCES loss_stage(id),
    PRIMARY KEY (group_id, loss_stage_id)
);

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

-- Scalar parameters of the mixing model itself -- how thoroughly a grader
-- splits a pair, how many units come up in one scoop, how much of "these two
-- units travelled together" survives a stage.
--
-- These used to live as bare constants in model.py, which is a bug in this
-- project specifically: a figure hardcoded in a module bypasses the citation
-- audit, so nobody could ask "how much does this number matter?" without
-- writing a one-off sweep. SEPARATION_EFFICIENCY sat there at 0.90 for months
-- and turned out to be worth 0.0003 of a bird -- harmless, but nobody knew
-- that, which is the whole argument for the rule.
--
-- source_id is NOT NULL, so `audit.py` discovers this table from the schema
-- and demands a citation for every row exactly as it does for a loss factor.
CREATE TABLE model_parameter (
    id              INTEGER PRIMARY KEY,
    slug            TEXT    NOT NULL UNIQUE,
    label           TEXT    NOT NULL,

    -- Triangular band, same shape as a loss factor's survive_lo/mode/hi, so
    -- the Monte Carlo can resample these the same way it resamples pools.
    value_lo        REAL    NOT NULL,
    value_mode      REAL    NOT NULL,
    value_hi        REAL    NOT NULL,

    source_id       INTEGER NOT NULL REFERENCES source(id),
    confidence      TEXT    NOT NULL,
    description     TEXT    NOT NULL,

    CHECK (value_lo <= value_mode AND value_mode <= value_hi)
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

    -- Which species this route applies to. NULL means any.
    --
    -- Added because its absence was a live bug. Chain selection had no idea
    -- what product it was for, so an egg query took the single global default
    -- -- the WING chain -- and solemnly walked eggs through a cut-up line, a
    -- wing chiller, size grading and a fryer basket. The count came out right
    -- by luck, since a hen's one-egg-a-day cap dominates and any large pool
    -- yields twelve, but the audit trail was fiction. For a project whose
    -- claim is that every number is traceable, that is the worst kind of bug.
    species_id      INTEGER REFERENCES species(id),

    -- Default for its species, not globally. Enforced by the index below so
    -- two defaults for one species is impossible rather than merely unlikely.
    is_default      INTEGER NOT NULL DEFAULT 0,

    -- Prose for the "why is the answer not exactly the floor" explanation.
    -- Lives here rather than in the CLI and the HTML, where it was hardcoded
    -- as wing-specific text and therefore described deboning to anyone asking
    -- about eggs. Data cannot narrate the wrong species.
    floor_note      TEXT
);

-- At most one default per species, and at most one global default.
CREATE UNIQUE INDEX idx_supply_chain_one_default
    ON supply_chain (COALESCE(species_id, -1))
    WHERE is_default = 1;

-- Which LOSS stages a route applies, mirroring supply_chain_stage for mixing.
--
-- Its absence was the bug. A chain selected its mixing stages but had no say
-- over its losses, so the grocery path and the restaurant path could not be
-- told apart: `retail_shrink` had to be parked optional/default-off purely to
-- stop it double-counting `kitchen_loss`, since every chain otherwise got
-- every stage. That was a workaround standing in for a model.
--
-- Empty for a chain means "apply the species defaults", which keeps every
-- existing route working unchanged. A chain that lists stages gets exactly
-- those, so a grocery route can claim retail shrink and skip restaurant
-- losses without either being globally disabled.
CREATE TABLE supply_chain_loss_stage (
    supply_chain_id INTEGER NOT NULL REFERENCES supply_chain(id),
    loss_stage_id   INTEGER NOT NULL REFERENCES loss_stage(id),
    PRIMARY KEY (supply_chain_id, loss_stage_id)
);

CREATE TABLE supply_chain_stage (
    supply_chain_id INTEGER NOT NULL REFERENCES supply_chain(id),
    mixing_stage_id INTEGER NOT NULL REFERENCES mixing_stage(id),
    pool_override   INTEGER,                       -- per-chain pool size
    PRIMARY KEY (supply_chain_id, mixing_stage_id)
);


-- ---------------------------------------------------------------------------
-- Quality defects
-- ---------------------------------------------------------------------------

-- Conditions that degrade meat quality without necessarily removing product.
-- Modelled separately from loss_factor on purpose: a woody-breast fillet is
-- still a fillet and still gets sold, so it does not belong in a chain whose
-- factors reduce counts. Yet it is central to "is a fatter bird better?",
-- which is a quality question, not a yield question.
CREATE TABLE quality_defect (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    slug                TEXT    NOT NULL UNIQUE,
    label               TEXT    NOT NULL,
    -- Which part of the bird develops it. The asymmetry this captures is the
    -- point: breast myopathies are near-universal while wings are immune.
    affected_part       TEXT    NOT NULL,      -- 'breast','wing','leg'
    severity            TEXT    NOT NULL,      -- 'any','moderate','severe'
    prevalence_pct_lo   REAL,
    prevalence_pct_mode REAL    NOT NULL,
    prevalence_pct_hi   REAL,
    -- How prevalence moves with live weight. This is what makes bigger birds
    -- a trade rather than a free win.
    weight_association  TEXT    NOT NULL CHECK (weight_association IN
                            ('increases','none','decreases','unknown')),
    first_year          INTEGER,               -- earliest reported figure
    first_year_pct      REAL,                  -- for showing the trend
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT
);

-- Each species' own version of the size-vs-quality question. "Is a fatter
-- chicken a better chicken?" only makes sense for broilers -- eggs are
-- graded on size classes, saffron on ISO colouring categories -- so the
-- question and its x-axis are data, not prose in a handler. This is the
-- floor_note lesson applied again: the verdict text used to be hardcoded
-- in api.py, where no YAML change could ever fix it.
--
-- No source_id: every column here is editorial framing. The figures that
-- back a verdict live in quality_defect and product_grade rows, which are
-- statistics and cite sources individually. A species with an axis row but
-- no figure rows has a question and no answer -- the API reports that
-- honestly rather than this table pretending otherwise.
CREATE TABLE quality_axis (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL UNIQUE REFERENCES species(id),
    question            TEXT    NOT NULL,   -- 'Is a fatter chicken better?'
    x_label             TEXT    NOT NULL,   -- 'Live weight'
    x_unit              TEXT,               -- 'lb'; NULL for pure classes
    -- 'continuous': the axis is a measured quantity (live weight).
    -- 'classes'   : the axis is a graded ladder (egg sizes, ISO categories).
    x_kind              TEXT    NOT NULL CHECK (x_kind IN
                            ('continuous','classes')),
    -- The three-part verdict, each 'better'/'worse'/'unchanged'/NULL.
    -- NULL means the corpus cannot support a verdict yet, and the API
    -- passes that on as an open question rather than defaulting it.
    verdict_yield       TEXT,
    verdict_quality     TEXT,
    verdict_count       TEXT,
    summary             TEXT
);


-- ---------------------------------------------------------------------------
-- Nutrition
-- ---------------------------------------------------------------------------

-- Nutrition per product and preparation. Separate rows per preparation
-- because breading and frying change the numbers far more than the bird
-- does -- a fried breaded wing and a raw wing are not the same food.
CREATE TABLE nutrition (
    id                  INTEGER PRIMARY KEY,
    product_id          INTEGER NOT NULL REFERENCES product(id),
    preparation         TEXT    NOT NULL,   -- 'raw','fried_breaded'
    label               TEXT    NOT NULL,
    -- Everything per 100 g edible portion, the basis USDA publishes on.
    kcal                REAL,
    protein_g           REAL,
    fat_g               REAL,
    saturated_fat_g     REAL,
    carbohydrate_g      REAL,
    sodium_mg           REAL,
    cholesterol_mg      REAL,
    -- Typical edible mass of one unit, so per-piece values can be derived
    -- rather than stored and drifting out of sync.
    edible_g_per_unit   REAL,
    fdc_id              TEXT,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT,
    UNIQUE (product_id, preparation)
);


-- ---------------------------------------------------------------------------
-- Resource footprint and economic impact
-- ---------------------------------------------------------------------------

-- Lifecycle environmental cost, stored per individual AND per kg live
-- weight because allocating to a single cut requires the mass basis.
CREATE TABLE resource_footprint (
    id                  INTEGER PRIMARY KEY,
    species_id          INTEGER NOT NULL REFERENCES species(id),
    metric              TEXT    NOT NULL,   -- 'global_warming','water',...
    label               TEXT    NOT NULL,
    unit                TEXT    NOT NULL,
    per_individual      REAL,
    per_kg_liveweight   REAL,
    reference_lw_lb     REAL,               -- the LCA's reference flow
    year                INTEGER,
    pct_change_decade   REAL,               -- e.g. -18.1 for 2010->2020
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT,
    UNIQUE (species_id, metric, year)
);

-- Human and economic side: who got paid, how many people were involved.
CREATE TABLE economic_stat (
    id                  INTEGER PRIMARY KEY,
    domain_id           INTEGER NOT NULL REFERENCES domain(id),
    slug                TEXT    NOT NULL UNIQUE,
    label               TEXT    NOT NULL,
    value_lo            REAL,
    value_mode          REAL,
    value_hi            REAL,
    unit                TEXT    NOT NULL,
    -- 'per_lb_liveweight', 'per_year', 'national' -- what the value is per.
    basis               TEXT    NOT NULL,
    confidence          TEXT    NOT NULL,
    source_id           INTEGER NOT NULL REFERENCES source(id),
    notes               TEXT
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

-- regional_size_stat holds one row per species, and the species carry
-- INCOMPATIBLE UNITS -- broiler live weight in pounds alongside layer output
-- in eggs per year. Any query that forgets `WHERE species = ...` silently
-- compares 5.6 lb against 224 eggs and reports nonsense, which is exactly
-- what happened the moment egg data landed: the cross-validation suite
-- started comparing pounds to eggs.
--
-- These views exist so callers cannot make that mistake. Read a view, never
-- the table, and the species filter is not something anyone has to remember.
CREATE VIEW v_broiler_size_stat AS
SELECT r.*
FROM regional_size_stat r
JOIN species s ON s.id = r.species_id
WHERE s.slug = 'broiler';

CREATE VIEW v_layer_egg_stat AS
SELECT r.*
FROM regional_size_stat r
JOIN species s ON s.id = r.species_id
WHERE s.slug = 'layer_hen';

-- Same reasoning as the two views above, applied to regional_census_stat
-- instead of regional_size_stat: that table is a single species today, but
-- nothing stops a second one landing in it, and a caller that forgot
-- `WHERE species = ...` would silently blend two species' sales_head and
-- inventory into one map. Read this view, never the raw table.
CREATE VIEW v_broiler_census_stat AS
SELECT r.*
FROM regional_census_stat r
JOIN species s ON s.id = r.species_id
WHERE s.slug = 'broiler';

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

-- Coverage per SPECIES rather than per domain, one boolean per dimension of
-- the corpus.
--
-- This exists because the page needs to say which species it actually answers
-- in depth, and saying it in prose was the bug: twelve products sat in one
-- dropdown as equals while eight of the eleven views showed exactly one of
-- them, unlabelled. A sentence naming the deep species would have been true
-- the day it was typed and wrong the day a second species filled in.
--
-- So the anchor is derived from this view instead: the active species present
-- in the most dimensions. Add a dimension by adding a column here, never by
-- listing species anywhere -- there is deliberately no such list, so the claim
-- follows the data and retires itself when the data changes.
--
-- The raw `regional_size_stat` reads below are the one legitimate kind: the
-- question is "which species have rows at all", which is precisely what
-- v_broiler_size_stat and v_layer_egg_stat cannot answer without naming both
-- of them. Every row here is grouped by species, so the pounds-versus-eggs
-- confusion those views exist to prevent cannot occur.
CREATE VIEW v_species_coverage AS
SELECT
    sp.id,
    sp.slug,
    sp.common_name,
    sp.individual_noun,
    sp.individual_plural,
    d.slug AS domain,
    EXISTS(SELECT 1 FROM supply_chain c
            WHERE c.species_id = sp.id)              AS loss_chain,
    EXISTS(SELECT 1 FROM product p
            WHERE p.species_id = sp.id)              AS products,
    EXISTS(SELECT 1 FROM quality_axis a
            WHERE a.species_id = sp.id)              AS size_axis,
    EXISTS(SELECT 1 FROM regional_size_stat r
            WHERE r.species_id = sp.id
              AND r.month IS NULL)                   AS regional_weight,
    EXISTS(SELECT 1 FROM regional_size_stat r
            WHERE r.species_id = sp.id
              AND r.month IS NOT NULL)               AS seasonality,
    EXISTS(SELECT 1 FROM husbandry_stat_year h
            WHERE h.species_id = sp.id)
      OR EXISTS(SELECT 1 FROM slaughter_stat_year y
                 WHERE y.species_id = sp.id)         AS trends,
    EXISTS(SELECT 1 FROM resource_footprint rf
            WHERE rf.species_id = sp.id)             AS footprint,
    EXISTS(SELECT 1 FROM nutrition n
             JOIN product p ON p.id = n.product_id
            WHERE p.species_id = sp.id)              AS nutrition
FROM species sp
JOIN domain d ON d.id = sp.domain_id
WHERE sp.active = 1;

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
