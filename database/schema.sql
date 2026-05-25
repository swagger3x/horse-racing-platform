-- ============================================================
-- Horse Racing Platform — PostgreSQL Schema
-- Supabase hosted | Schema v1.0
-- Based on Medialityracing XML Feed v2.0.13
-- ============================================================
-- Table creation order respects FK dependencies:
--   tracks → meetings
--   meetings → races
--   people → runners
--   horses → runners
--   races → runners
--   runners → past_runs
--   runners → runners_statistics
--   runners → runners_ratings
-- ============================================================


-- ─────────────────────────────────────────────
-- EXTENSIONS
-- ─────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ─────────────────────────────────────────────
-- 1. TRACKS
-- Static venue information
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tracks (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    xml_track_id        INTEGER     NOT NULL UNIQUE,   -- track[@id]
    name                TEXT        NOT NULL,           -- track[@name]
    country             CHAR(3),                        -- track[@country]
    state               VARCHAR(10),                    -- track[@state]
    location            VARCHAR(5),                     -- track[@location] M=Metro R=Regional C=Country
    club                TEXT,                           -- track[@club]
    track_3char_abbrev  VARCHAR(3),                    -- track[@track_3char_abbrev]
    track_4char_abbrev  VARCHAR(4),                    -- track[@track_4char_abbrev]
    track_6char_abbrev  VARCHAR(6),                    -- track[@track_6char_abbrev]
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE tracks IS 'Static venue/track information. One row per racecourse.';


-- ─────────────────────────────────────────────
-- 2. MEETINGS
-- One row per race day per venue
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS meetings (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    track_id            UUID        NOT NULL REFERENCES tracks(id),
    meeting_date        DATE        NOT NULL,
    ra_meeting_id       BIGINT      UNIQUE,             -- ra_meeting_id
    stage               VARCHAR(1),                     -- stage (A/B/C/D/E)
    tab_indicator       VARCHAR(2),                     -- tab_indicator
    dual_track          BOOLEAN     DEFAULT FALSE,       -- dual_track
    rail_position       TEXT,                           -- rail_position
    -- Track conditions on the day
    track_surface       VARCHAR(2),                     -- track[@track_surface] G=Good S=Soft H=Heavy
    expected_condition  VARCHAR(5),                     -- track[@expected_condition] e.g. G4
    weather             TEXT,                           -- track/weather
    penetrometer        NUMERIC(5,2),                   -- track/penetrometer
    irrigation          TEXT,                           -- track/irrigation
    rainfall            TEXT,                           -- track/rainfall
    track_info          TEXT,                           -- track/track_info (going stick readings)
    -- Feed file info
    feed_directory      VARCHAR(20),                    -- product[@directory]
    feed_file           VARCHAR(50),                    -- product[@file]
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (track_id, meeting_date)
);

COMMENT ON TABLE meetings IS 'One row per race day per venue. Conditions reflect the day of racing.';


-- ─────────────────────────────────────────────
-- 3. RACES
-- Individual races within a meeting
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS races (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id          UUID        NOT NULL REFERENCES meetings(id),
    xml_race_id         BIGINT      NOT NULL UNIQUE,    -- race[@id]
    race_number         SMALLINT    NOT NULL,           -- race[@number]
    race_name           TEXT,                           -- race[@name]
    nominations_number  SMALLINT,                       -- race[@nominations_number]
    -- Race conditions
    distance_m          INTEGER,                        -- distance[@metres]
    race_type           VARCHAR(20),                    -- race_type (Flat/Jump)
    weight_type         TEXT,                           -- weight_type
    min_hcp_weight      NUMERIC(5,2),                  -- min_hcp_weight
    class               TEXT,                           -- classes/class
    class_id            INTEGER,                        -- classes/class_id
    group_level         SMALLINT,                       -- group (1/2/3)
    restrictions_age    TEXT,                           -- restrictions[@age]
    restrictions_sex    TEXT,                           -- restrictions[@sex]
    restrictions_jockey TEXT,                           -- restrictions[@jockey]
    size_field          SMALLINT,                       -- size_field
    size_emergencies    SMALLINT,                       -- size_emergencies
    start_time          VARCHAR(20),                    -- start_time
    -- Prize money breakdown
    prize_1st           INTEGER,
    prize_2nd           INTEGER,
    prize_3rd           INTEGER,
    prize_4th           INTEGER,
    prize_5th           INTEGER,
    prize_total         INTEGER,                        -- prizes/prize[@type='total_value']
    prize_trophy_total  INTEGER,                        -- prizes/prize[@type='trophy_total_value']
    -- Track record for this distance
    track_record_horse  TEXT,                           -- records/track_record/horse[@name]
    track_record_date   DATE,                           -- records/track_record/meeting_date
    track_record_time   VARCHAR(20),                    -- records/track_record/duration
    -- AI placeholders
    ai_race_summary     TEXT,
    ai_race_audio_url   TEXT,
    is_feature_race     BOOLEAN     DEFAULT FALSE,
    glide_hero_image_url TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE races IS 'Individual races within a meeting. One row per race.';


-- ─────────────────────────────────────────────
-- 4. HORSES
-- Permanent horse profiles (not race-specific)
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS horses (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    xml_horse_id        BIGINT      NOT NULL UNIQUE,    -- horse[@id]
    ra_horse_id         BIGINT,                         -- horse[@horse_RA_Id]
    name                TEXT        NOT NULL,           -- horse[@name]
    previous_name       TEXT,                           -- horse[@previous_name]
    country             CHAR(3),                        -- horse[@country]
    sex                 VARCHAR(2),                     -- horse[@sex] G=Gelding M=Mare F=Filly C=Colt H=Horse
    colour              VARCHAR(10),                    -- horse[@colour]
    foaling_date        DATE,                           -- horse[@foaling_date]
    -- Breeding
    sire_name           TEXT,                           -- sire[@name]
    sire_country        CHAR(3),                        -- sire[@country]
    sire_xml_id         BIGINT,                         -- sire[@id]
    dam_name            TEXT,                           -- dam[@name]
    dam_country         CHAR(3),                        -- dam[@country]
    dam_xml_id          BIGINT,                         -- dam[@id]
    sire_of_dam_name    TEXT,                           -- sire_of_dam[@name]
    sire_of_dam_country CHAR(3),                        -- sire_of_dam[@country]
    sire_of_dam_xml_id  BIGINT,                         -- sire_of_dam[@id]
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE horses IS 'Permanent horse profiles. Independent of any specific race.';


-- ─────────────────────────────────────────────
-- 5. PEOPLE
-- Trainers and jockeys (shared table, role column)
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS people (
    id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    xml_person_id           INTEGER     NOT NULL,
    role                    VARCHAR(10) NOT NULL,       -- 'trainer' or 'jockey'
    full_name               TEXT        NOT NULL,       -- trainer[@name] / jockey[@name]
    firstname               TEXT,                       -- trainer[@firstname] / jockey[@firstname]
    surname                 TEXT,                       -- trainer[@surname] / jockey[@surname]
    ra_id                   BIGINT,                     -- trainer[@trainer_RA_Id] / jockey[@jockey_RA_Id]
    -- Jockey specific
    apprentice_indicator    BOOLEAN     DEFAULT FALSE,  -- jockey[@apprentice_indicator]
    allowance_weight        NUMERIC(4,1),               -- jockey[@allowance_weight]
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (xml_person_id, role)
);

COMMENT ON TABLE people IS 'Trainers and jockeys. Role column distinguishes between them.';


-- ─────────────────────────────────────────────
-- 6. RUNNERS
-- A horse's entry in a specific race
-- Central linking table with race-day specific data
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS runners (
    id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    race_id                 UUID        NOT NULL REFERENCES races(id),
    horse_id                UUID        NOT NULL REFERENCES horses(id),
    trainer_id              UUID        REFERENCES people(id),
    jockey_id               UUID        REFERENCES people(id),
    -- Race day assignment
    tab_no                  SMALLINT,                   -- tab_no
    barrier                 SMALLINT,                   -- barrier
    selection               SMALLINT,                   -- selection
    weight_allocated        NUMERIC(5,2),               -- weight[@allocated]
    weight_total            NUMERIC(5,2),               -- weight[@total]
    -- Market
    market_price_frac       VARCHAR(10),                -- market[@price]
    market_price_decimal    NUMERIC(8,2),               -- market[@price_decimal]
    -- Horse info on the day
    training_location       TEXT,                       -- training_location
    owners                  TEXT,                       -- owners
    colours                 TEXT,                       -- colours (silks description)
    prizemoney_won          INTEGER,                    -- prizemoney_won (career total)
    -- Silks images
    silks_url_jpg           TEXT,                       -- horse_colours_image
    silks_url_png           TEXT,                       -- horse_colours_image_png
    silks_url_svg           TEXT,                       -- horse_colours_image_svg
    -- Form summary
    last_four_starts        VARCHAR(20),                -- last_four_starts
    last_ten_starts         VARCHAR(30),                -- last_ten_starts
    last_fifteen_starts     VARCHAR(40),                -- last_fifteen_starts
    last_twenty_starts      VARCHAR(50),                -- last_twenty_starts
    form_comments           TEXT,                       -- form_comments
    comments                TEXT,                       -- comments (analyst)
    -- Ratings & form figures
    rating                  NUMERIC(6,2),               -- rating
    ff5_dry                 NUMERIC(6,2),               -- FF5_dry
    ff5_wet                 NUMERIC(6,2),               -- FF5_wet
    ff_dry_rating_100       NUMERIC(6,2),               -- FF_Dry_Rating_100
    ff_wet_rating_100       NUMERIC(6,2),               -- FF_Wet_Rating_100
    -- Pace
    pace                    TEXT,                       -- pace (Lead/Handy/Midfield/Back)
    pace_value              SMALLINT,                   -- pace_value
    -- Percentages
    win_percentage          NUMERIC(5,2),               -- win_percentage
    place_percentage        NUMERIC(5,2),               -- place_percentage
    -- Gear
    current_blinker_ind     CHAR(1),                    -- current_blinker_ind
    running_gear            TEXT[],                     -- running_gear/gear_item (array)
    gear_changes            JSONB,                      -- gear_changes (array with id/gear/option)
    -- Trainer extra info
    trainer_firststart      BOOLEAN,                    -- trainer[@firststart]
    trainer_previous        TEXT,                       -- trainer[@previous_trainer]
    trainer_previous_id     INTEGER,                    -- trainer[@previous_trainer_id]
    -- Horse extra info
    scratched               BOOLEAN     DEFAULT FALSE,  -- scratched
    -- Catch-all for any unrecognised fields
    extra_data              JSONB,
    -- ── AI / Voice-to-text placeholders (Phase 2) ──────────
    ai_voice_note_url       TEXT,                       -- URL to recorded audio note
    ai_transcript_raw       TEXT,                       -- raw voice transcript
    ai_transcript_structured JSONB,                     -- structured OpenAI output
    ai_insight              TEXT,                       -- AI generated commentary
    ai_tip_flag             BOOLEAN     DEFAULT FALSE,  -- AI selected as tip
    ai_confidence_score     NUMERIC(5,2),               -- AI confidence 0-100
    ai_processed_at         TIMESTAMPTZ,                -- when AI last processed
    -- ── Custom / Glide placeholders (Phase 2) ───────────────
    custom_notes            TEXT,                       -- manual analyst notes
    custom_tags             TEXT[],                     -- custom tag array
    is_highlighted          BOOLEAN     DEFAULT FALSE,  -- featured in Glide UI
    glide_display_override  JSONB,                      -- Glide display config
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (race_id, horse_id)
);

COMMENT ON TABLE runners IS 'A horse entry in a specific race. Central linking table. Contains all race-day specific data.';


-- ─────────────────────────────────────────────
-- 7. PAST_RUNS
-- Historical race results per horse (from FORM feed)
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS past_runs (
    id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    runner_id               UUID        NOT NULL REFERENCES runners(id),
    event_id                BIGINT      NOT NULL UNIQUE,  -- form/event_id
    -- Race details
    meeting_date            DATE,                         -- form/meeting_date
    rail_position           TEXT,                         -- form/rail_position
    track_name              TEXT,                         -- form/track[@name]
    track_xml_id            INTEGER,                      -- form/track[@id]
    track_country           CHAR(3),                      -- form/track[@country]
    track_condition         TEXT,                         -- form/track[@condition]
    track_grading           SMALLINT,                     -- form/track[@grading]
    track_surface           VARCHAR(2),                   -- form/track[@track_surface]
    track_location          VARCHAR(5),                   -- form/track[@location]
    track_state_no          INTEGER,                      -- form/track[@state_no]
    track_3char_abbrev      VARCHAR(3),                   -- form/track[@track_3char_abbrev]
    weight_type             TEXT,                         -- form/weight_type
    race_number             SMALLINT,                     -- form/race[@number]
    race_name               TEXT,                         -- form/race[@name]
    distance_m              INTEGER,                      -- form/distance[@metres]
    event_duration          VARCHAR(20),                  -- form/event_duration e.g. 1:08.10
    group_level             SMALLINT,                     -- form/group
    night_meeting           BOOLEAN,                      -- form/night_meeting
    -- Restrictions
    restrictions_age        TEXT,                         -- form/restrictions[@age]
    restrictions_sex        TEXT,                         -- form/restrictions[@sex]
    restrictions_jockey     TEXT,                         -- form/restrictions[@jockey]
    -- Class
    class                   TEXT,                         -- form/classes/class
    class_id                INTEGER,                      -- form/classes/class_id
    second_class            TEXT,                         -- form/classes/second_class
    second_class_id         INTEGER,                      -- form/classes/second_class_id
    -- Prize
    event_prizemoney        INTEGER,                      -- form/event_prizemoney
    horse_prizemoney        INTEGER,                      -- form/horse_prizemoney
    horse_prizemoney_bonus  INTEGER,                      -- form/horse_prizemoney_bonus
    -- Runner details on the day
    barrier                 SMALLINT,                     -- form/barrier
    weight_carried          NUMERIC(5,2),                 -- form/weight_carried
    weight_adj              NUMERIC(5,2),                 -- form/weight_adj
    limit_weight            NUMERIC(5,2),                 -- form/limit_weight
    jockey_name             TEXT,                         -- form/jockey[@name]
    jockey_xml_id           INTEGER,                      -- form/jockey[@id]
    jockey_apprentice       BOOLEAN,                      -- form/jockey[@apprentice_indicator]
    -- Prices
    price_opening_frac      VARCHAR(10),                  -- form/prices[@opening]
    price_mid_frac          VARCHAR(10),                  -- form/prices[@mid]
    price_sp_frac           VARCHAR(10),                  -- form/prices[@starting]
    price_opening_dec       NUMERIC(8,2),                 -- form/decimalprices[@opening]
    price_mid_dec           NUMERIC(8,2),                 -- form/decimalprices[@mid]
    price_sp_dec            NUMERIC(8,2),                 -- form/decimalprices[@starting]
    favourite_indicator     BOOLEAN,                      -- form/favourite_indicator
    -- In-running positions
    pos_settling            SMALLINT,                     -- form/positions[@settling_down]
    pos_m400                SMALLINT,                     -- form/positions[@m400]
    pos_m800                SMALLINT,                     -- form/positions[@m800]
    pos_m1200               SMALLINT,                     -- form/positions[@m1200]
    pos_finish              SMALLINT,                     -- form/positions[@finish]
    finish_position         VARCHAR(10),                  -- form/finish_position (can be text e.g. 'WO')
    -- Margins
    margin                  NUMERIC(6,2),                 -- form/margin
    beaten_margin           NUMERIC(6,2),                 -- form/beaten_margin
    official_margin_1       TEXT,                         -- form/official_margin_1
    official_margin_2       TEXT,                         -- form/official_margin_2
    starters                SMALLINT,                     -- form/starters
    -- Sectionals
    sectional_distance      INTEGER,                      -- form/sectional[@distance]
    sectional_time          VARCHAR(20),                  -- form/sectional[@time]
    sectional_location      VARCHAR(20),                  -- form/sectional[@location]
    -- Ratings
    rating_unadjusted       NUMERIC(6,2),                 -- form/rating[@unadjusted]
    rating_adjusted         NUMERIC(6,2),                 -- form/rating[@adjusted]
    rating_handicap         NUMERIC(6,2),                 -- form/rating[@handicap]
    rating_post_handicap    NUMERIC(6,2),                 -- form/rating[@post_handicap]
    -- Other
    days_since_last_run     SMALLINT,                     -- form/days_since_last_run
    barrier_trial_indicator BOOLEAN,                      -- form/barrier_trial_indicator
    blinker_indicator       VARCHAR(5),                   -- form/blinker_indicator
    stewards_report         TEXT,                         -- form/stewards_reports/stewards_report
    running_gear            TEXT[],                       -- form/running_gear/gear_item
    gear_changes            JSONB,                        -- form/gear_changes
    other_runners           JSONB,                        -- form/other_runners/other_runner (array)
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE past_runs IS 'Historical race results per horse. One row per past run. Source: FORM feed only.';


-- ─────────────────────────────────────────────
-- 8. RUNNERS_STATISTICS
-- Win/place stats by condition type
-- 28 types per entity (horse, trainer, jockey)
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS runners_statistics (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    runner_id   UUID        NOT NULL REFERENCES runners(id),
    entity      VARCHAR(10) NOT NULL,   -- 'horse', 'trainer', 'jockey'
    stat_type   VARCHAR(40) NOT NULL,   -- e.g. 'all', 'good', 'first_up', 'group_1'
    total       SMALLINT    DEFAULT 0,
    firsts      SMALLINT    DEFAULT 0,
    seconds     SMALLINT    DEFAULT 0,
    thirds      SMALLINT    DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (runner_id, entity, stat_type)
);

COMMENT ON TABLE runners_statistics IS 'Win/place stats per runner by condition type. 28 types x 3 entities = up to 84 rows per runner.';


-- ─────────────────────────────────────────────
-- 9. RUNNERS_RATINGS
-- Performance ratings by condition type
-- 25 types per runner
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS runners_ratings (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    runner_id   UUID        NOT NULL REFERENCES runners(id),
    rating_type VARCHAR(30) NOT NULL,   -- e.g. 'career', 'good', 'first_up', 'distance_track'
    value       NUMERIC(7,2),
    rating_date DATE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (runner_id, rating_type)
);

COMMENT ON TABLE runners_ratings IS 'Performance ratings per runner by condition type. Up to 25 rows per runner.';


-- ─────────────────────────────────────────────
-- INDEXES
-- Speed up common queries
-- ─────────────────────────────────────────────

-- Meetings
CREATE INDEX IF NOT EXISTS idx_meetings_date         ON meetings (meeting_date);
CREATE INDEX IF NOT EXISTS idx_meetings_track        ON meetings (track_id);

-- Races
CREATE INDEX IF NOT EXISTS idx_races_meeting         ON races (meeting_id);
CREATE INDEX IF NOT EXISTS idx_races_xml_id          ON races (xml_race_id);

-- Horses
CREATE INDEX IF NOT EXISTS idx_horses_xml_id         ON horses (xml_horse_id);
CREATE INDEX IF NOT EXISTS idx_horses_name           ON horses (name);

-- People
CREATE INDEX IF NOT EXISTS idx_people_xml_role       ON people (xml_person_id, role);

-- Runners
CREATE INDEX IF NOT EXISTS idx_runners_race          ON runners (race_id);
CREATE INDEX IF NOT EXISTS idx_runners_horse         ON runners (horse_id);
CREATE INDEX IF NOT EXISTS idx_runners_trainer       ON runners (trainer_id);
CREATE INDEX IF NOT EXISTS idx_runners_jockey        ON runners (jockey_id);
CREATE INDEX IF NOT EXISTS idx_runners_tab_no        ON runners (race_id, tab_no);
CREATE INDEX IF NOT EXISTS idx_runners_scratched     ON runners (scratched);
CREATE INDEX IF NOT EXISTS idx_runners_ai_tip        ON runners (ai_tip_flag);

-- Past runs
CREATE INDEX IF NOT EXISTS idx_past_runs_runner      ON past_runs (runner_id);
CREATE INDEX IF NOT EXISTS idx_past_runs_event_id    ON past_runs (event_id);
CREATE INDEX IF NOT EXISTS idx_past_runs_date        ON past_runs (meeting_date);

-- Statistics & ratings
CREATE INDEX IF NOT EXISTS idx_stats_runner_entity   ON runners_statistics (runner_id, entity);
CREATE INDEX IF NOT EXISTS idx_ratings_runner        ON runners_ratings (runner_id);


-- ─────────────────────────────────────────────
-- AUTO-UPDATE updated_at TRIGGER
-- ─────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_tracks_updated_at
    BEFORE UPDATE ON tracks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_meetings_updated_at
    BEFORE UPDATE ON meetings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_races_updated_at
    BEFORE UPDATE ON races
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_horses_updated_at
    BEFORE UPDATE ON horses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_people_updated_at
    BEFORE UPDATE ON people
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_runners_updated_at
    BEFORE UPDATE ON runners
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_past_runs_updated_at
    BEFORE UPDATE ON past_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_runners_statistics_updated_at
    BEFORE UPDATE ON runners_statistics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER trg_runners_ratings_updated_at
    BEFORE UPDATE ON runners_ratings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();