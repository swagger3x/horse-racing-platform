"""
Database upsert operations for the horse racing pipeline.
All operations use ON CONFLICT DO UPDATE so it is safe
to re-run at any time without creating duplicate records.

Upsert order respects FK dependencies:
  tracks -> meetings -> races -> horses -> people -> runners
  -> runners_statistics -> runners_ratings -> past_runs
"""

import json
import os
import sys
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


# Connection
def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set in .env")
        sys.exit(1)
    return psycopg2.connect(db_url)


# Helpers
def to_json(value) -> str | None:
    """Serialize a list/dict to JSON string for JSONB columns."""
    if not value:
        return None
    return json.dumps(value)


def to_pg_array(value: list) -> list | None:
    """Return list as-is for psycopg2 text[] binding."""
    if not value:
        return None
    return value


# Upsert functions
def upsert_track(cursor, track: dict) -> str:
    """Upsert track. Returns the UUID id."""
    cursor.execute("""
        INSERT INTO tracks (
            xml_track_id, name, country, state, location, club,
            track_3char_abbrev, track_4char_abbrev, track_6char_abbrev
        ) VALUES (
            %(xml_track_id)s, %(name)s, %(country)s, %(state)s, %(location)s, %(club)s,
            %(track_3char_abbrev)s, %(track_4char_abbrev)s, %(track_6char_abbrev)s
        )
        ON CONFLICT (xml_track_id) DO UPDATE SET
            name              = EXCLUDED.name,
            country           = EXCLUDED.country,
            state             = EXCLUDED.state,
            location          = EXCLUDED.location,
            club              = EXCLUDED.club,
            track_3char_abbrev = EXCLUDED.track_3char_abbrev,
            updated_at        = NOW()
        RETURNING id
    """, track)
    return cursor.fetchone()[0]


def upsert_meeting(cursor, meeting: dict, track_id: str) -> str:
    """Upsert meeting. Returns the UUID id."""
    meeting["track_id"] = track_id
    cursor.execute("""
        INSERT INTO meetings (
            track_id, meeting_date, ra_meeting_id, stage, tab_indicator,
            dual_track, rail_position, track_surface, expected_condition,
            weather, penetrometer, irrigation, rainfall, track_info,
            feed_directory, feed_file
        ) VALUES (
            %(track_id)s, %(meeting_date)s, %(ra_meeting_id)s, %(stage)s, %(tab_indicator)s,
            %(dual_track)s, %(rail_position)s, %(track_surface)s, %(expected_condition)s,
            %(weather)s, %(penetrometer)s, %(irrigation)s, %(rainfall)s, %(track_info)s,
            %(feed_directory)s, %(feed_file)s
        )
        ON CONFLICT (track_id, meeting_date) DO UPDATE SET
            stage              = EXCLUDED.stage,
            rail_position      = EXCLUDED.rail_position,
            track_surface      = EXCLUDED.track_surface,
            expected_condition = EXCLUDED.expected_condition,
            weather            = EXCLUDED.weather,
            penetrometer       = EXCLUDED.penetrometer,
            feed_file          = EXCLUDED.feed_file,
            updated_at         = NOW()
        RETURNING id
    """, {**meeting, **{"track_surface": meeting.get("track_surface"),
                        "expected_condition": meeting.get("expected_condition"),
                        "weather": meeting.get("weather"),
                        "penetrometer": meeting.get("penetrometer"),
                        "irrigation": meeting.get("irrigation"),
                        "rainfall": meeting.get("rainfall"),
                        "track_info": meeting.get("track_info")}})
    return cursor.fetchone()[0]


def upsert_race(cursor, race: dict, meeting_id: str) -> str:
    """Upsert race. Returns the UUID id."""
    race["meeting_id"] = meeting_id
    cursor.execute("""
        INSERT INTO races (
            meeting_id, xml_race_id, race_number, race_name, nominations_number,
            distance_m, race_type, weight_type, min_hcp_weight,
            class, class_id, group_level,
            restrictions_age, restrictions_sex, restrictions_jockey,
            size_field, size_emergencies, start_time,
            prize_1st, prize_2nd, prize_3rd, prize_4th, prize_5th,
            prize_total, prize_trophy_total,
            track_record_horse, track_record_date, track_record_time
        ) VALUES (
            %(meeting_id)s, %(xml_race_id)s, %(race_number)s, %(race_name)s, %(nominations_number)s,
            %(distance_m)s, %(race_type)s, %(weight_type)s, %(min_hcp_weight)s,
            %(class)s, %(class_id)s, %(group_level)s,
            %(restrictions_age)s, %(restrictions_sex)s, %(restrictions_jockey)s,
            %(size_field)s, %(size_emergencies)s, %(start_time)s,
            %(prize_1st)s, %(prize_2nd)s, %(prize_3rd)s, %(prize_4th)s, %(prize_5th)s,
            %(prize_total)s, %(prize_trophy_total)s,
            %(track_record_horse)s, %(track_record_date)s, %(track_record_time)s
        )
        ON CONFLICT (xml_race_id) DO UPDATE SET
            race_name          = EXCLUDED.race_name,
            size_field         = EXCLUDED.size_field,
            start_time         = EXCLUDED.start_time,
            prize_total        = EXCLUDED.prize_total,
            updated_at         = NOW()
        RETURNING id
    """, {
        **race,
        "prize_1st"         : race.get("prize_1st"),
        "prize_2nd"         : race.get("prize_2nd"),
        "prize_3rd"         : race.get("prize_3rd"),
        "prize_4th"         : race.get("prize_4th"),
        "prize_5th"         : race.get("prize_5th"),
        "prize_total"       : race.get("prize_total"),
        "prize_trophy_total": race.get("prize_trophy_total"),
        "group_level"       : race.get("group_level"),
        "restrictions_age"  : race.get("restrictions_age"),
        "restrictions_sex"  : race.get("restrictions_sex"),
        "restrictions_jockey": race.get("restrictions_jockey"),
        "track_record_horse" : race.get("track_record_horse"),
        "track_record_date"  : race.get("track_record_date"),
        "track_record_time"  : race.get("track_record_time"),
    })
    return cursor.fetchone()[0]


def upsert_horse(cursor, horse: dict) -> str:
    """Upsert horse profile. Returns the UUID id."""
    cursor.execute("""
        INSERT INTO horses (
            xml_horse_id, ra_horse_id, name, previous_name, country,
            sex, colour, foaling_date,
            sire_name, sire_country, sire_xml_id,
            dam_name, dam_country, dam_xml_id,
            sire_of_dam_name, sire_of_dam_country, sire_of_dam_xml_id
        ) VALUES (
            %(xml_horse_id)s, %(ra_horse_id)s, %(name)s, %(previous_name)s, %(country)s,
            %(sex)s, %(colour)s, %(foaling_date)s,
            %(sire_name)s, %(sire_country)s, %(sire_xml_id)s,
            %(dam_name)s, %(dam_country)s, %(dam_xml_id)s,
            %(sire_of_dam_name)s, %(sire_of_dam_country)s, %(sire_of_dam_xml_id)s
        )
        ON CONFLICT (xml_horse_id) DO UPDATE SET
            name          = EXCLUDED.name,
            previous_name = EXCLUDED.previous_name,
            colour        = EXCLUDED.colour,
            updated_at    = NOW()
        RETURNING id
    """, horse)
    return cursor.fetchone()[0]


def upsert_person(cursor, person: dict) -> str:
    """Upsert trainer or jockey. Returns the UUID id."""
    if not person or not person.get("xml_person_id"):
        return None
    cursor.execute("""
        INSERT INTO people (
            xml_person_id, role, full_name, firstname, surname,
            ra_id, apprentice_indicator, allowance_weight
        ) VALUES (
            %(xml_person_id)s, %(role)s, %(full_name)s, %(firstname)s, %(surname)s,
            %(ra_id)s, %(apprentice_indicator)s, %(allowance_weight)s
        )
        ON CONFLICT (xml_person_id, role) DO UPDATE SET
            full_name           = EXCLUDED.full_name,
            apprentice_indicator = EXCLUDED.apprentice_indicator,
            allowance_weight    = EXCLUDED.allowance_weight,
            updated_at          = NOW()
        RETURNING id
    """, person)
    return cursor.fetchone()[0]


def upsert_runner(cursor, runner: dict, race_id: str,
                  horse_id: str, trainer_id: str, jockey_id: str) -> str:
    """Upsert runner. Returns the UUID id."""
    runner["race_id"]    = race_id
    runner["horse_id"]   = horse_id
    runner["trainer_id"] = trainer_id
    runner["jockey_id"]  = jockey_id
    runner["running_gear"] = to_pg_array(runner.get("running_gear"))
    runner["gear_changes"] = to_json(runner.get("gear_changes"))

    cursor.execute("""
        INSERT INTO runners (
            race_id, horse_id, trainer_id, jockey_id,
            tab_no, barrier, selection,
            weight_allocated, weight_total,
            market_price_frac, market_price_decimal,
            training_location, owners, colours, prizemoney_won,
            silks_url_jpg, silks_url_png, silks_url_svg,
            last_four_starts, last_ten_starts, last_fifteen_starts, last_twenty_starts,
            form_comments, comments,
            rating, ff5_dry, ff5_wet, ff_dry_rating_100, ff_wet_rating_100,
            pace, pace_value, win_percentage, place_percentage,
            current_blinker_ind, running_gear, gear_changes,
            trainer_firststart, trainer_previous, trainer_previous_id, scratched
        ) VALUES (
            %(race_id)s, %(horse_id)s, %(trainer_id)s, %(jockey_id)s,
            %(tab_no)s, %(barrier)s, %(selection)s,
            %(weight_allocated)s, %(weight_total)s,
            %(market_price_frac)s, %(market_price_decimal)s,
            %(training_location)s, %(owners)s, %(colours)s, %(prizemoney_won)s,
            %(silks_url_jpg)s, %(silks_url_png)s, %(silks_url_svg)s,
            %(last_four_starts)s, %(last_ten_starts)s, %(last_fifteen_starts)s, %(last_twenty_starts)s,
            %(form_comments)s, %(comments)s,
            %(rating)s, %(ff5_dry)s, %(ff5_wet)s, %(ff_dry_rating_100)s, %(ff_wet_rating_100)s,
            %(pace)s, %(pace_value)s, %(win_percentage)s, %(place_percentage)s,
            %(current_blinker_ind)s, %(running_gear)s, %(gear_changes)s,
            %(trainer_firststart)s, %(trainer_previous)s, %(trainer_previous_id)s, %(scratched)s
        )
        ON CONFLICT (race_id, horse_id) DO UPDATE SET
            tab_no               = EXCLUDED.tab_no,
            barrier              = EXCLUDED.barrier,
            weight_allocated     = EXCLUDED.weight_allocated,
            market_price_frac    = EXCLUDED.market_price_frac,
            market_price_decimal = EXCLUDED.market_price_decimal,
            running_gear         = EXCLUDED.running_gear,
            gear_changes         = EXCLUDED.gear_changes,
            scratched            = EXCLUDED.scratched,
            form_comments        = EXCLUDED.form_comments,
            comments             = EXCLUDED.comments,
            updated_at           = NOW()
        RETURNING id
    """, runner)
    return cursor.fetchone()[0]


def upsert_statistics(cursor, runner_id: str, stats: list):
    """Batch upsert all statistics rows for a runner in one query."""
    rows = [
        (runner_id, s["entity"], s["stat_type"],
         s.get("total", 0), s.get("firsts", 0), s.get("seconds", 0), s.get("thirds", 0))
        for s in stats if s.get("stat_type")
    ]
    if not rows:
        return
    psycopg2.extras.execute_values(cursor, """
        INSERT INTO runners_statistics
            (runner_id, entity, stat_type, total, firsts, seconds, thirds)
        VALUES %s
        ON CONFLICT (runner_id, entity, stat_type) DO UPDATE SET
            total      = EXCLUDED.total,
            firsts     = EXCLUDED.firsts,
            seconds    = EXCLUDED.seconds,
            thirds     = EXCLUDED.thirds,
            updated_at = NOW()
    """, rows)


def upsert_ratings(cursor, runner_id: str, ratings: list):
    """Batch upsert all ratings rows for a runner in one query."""
    rows = [
        (runner_id, r["rating_type"], r.get("value"), r.get("rating_date"))
        for r in ratings if r.get("rating_type")
    ]
    if not rows:
        return
    psycopg2.extras.execute_values(cursor, """
        INSERT INTO runners_ratings
            (runner_id, rating_type, value, rating_date)
        VALUES %s
        ON CONFLICT (runner_id, rating_type) DO UPDATE SET
            value       = EXCLUDED.value,
            rating_date = EXCLUDED.rating_date,
            updated_at  = NOW()
    """, rows)


def upsert_past_run(cursor, runner_id: str, past_run: dict):
    """Upsert a single past run record."""
    if not past_run.get("event_id"):
        return
    past_run["runner_id"]    = runner_id
    past_run["running_gear"] = to_pg_array(past_run.get("running_gear"))
    past_run["gear_changes"] = to_json(past_run.get("gear_changes"))
    past_run["other_runners"]= to_json(past_run.get("other_runners"))

    cursor.execute("""
        INSERT INTO past_runs (
            runner_id, event_id, meeting_date, rail_position,
            track_name, track_xml_id, track_country, track_condition,
            track_grading, track_surface, track_location, track_state_no, track_3char_abbrev,
            weight_type, race_number, race_name, distance_m, event_duration,
            group_level, night_meeting,
            restrictions_age, restrictions_sex, restrictions_jockey,
            class, class_id, second_class, second_class_id,
            event_prizemoney, horse_prizemoney, horse_prizemoney_bonus,
            barrier, weight_carried, weight_adj, limit_weight,
            jockey_name, jockey_xml_id, jockey_apprentice,
            price_opening_frac, price_mid_frac, price_sp_frac,
            price_opening_dec, price_mid_dec, price_sp_dec, favourite_indicator,
            pos_settling, pos_m400, pos_m800, pos_m1200, pos_finish,
            finish_position, margin, beaten_margin, official_margin_1, official_margin_2,
            starters, sectional_distance, sectional_time, sectional_location,
            rating_unadjusted, rating_adjusted, rating_handicap, rating_post_handicap,
            days_since_last_run, barrier_trial_indicator, blinker_indicator,
            stewards_report, running_gear, gear_changes, other_runners
        ) VALUES (
            %(runner_id)s, %(event_id)s, %(meeting_date)s, %(rail_position)s,
            %(track_name)s, %(track_xml_id)s, %(track_country)s, %(track_condition)s,
            %(track_grading)s, %(track_surface)s, %(track_location)s, %(track_state_no)s, %(track_3char_abbrev)s,
            %(weight_type)s, %(race_number)s, %(race_name)s, %(distance_m)s, %(event_duration)s,
            %(group_level)s, %(night_meeting)s,
            %(restrictions_age)s, %(restrictions_sex)s, %(restrictions_jockey)s,
            %(class)s, %(class_id)s, %(second_class)s, %(second_class_id)s,
            %(event_prizemoney)s, %(horse_prizemoney)s, %(horse_prizemoney_bonus)s,
            %(barrier)s, %(weight_carried)s, %(weight_adj)s, %(limit_weight)s,
            %(jockey_name)s, %(jockey_xml_id)s, %(jockey_apprentice)s,
            %(price_opening_frac)s, %(price_mid_frac)s, %(price_sp_frac)s,
            %(price_opening_dec)s, %(price_mid_dec)s, %(price_sp_dec)s, %(favourite_indicator)s,
            %(pos_settling)s, %(pos_m400)s, %(pos_m800)s, %(pos_m1200)s, %(pos_finish)s,
            %(finish_position)s, %(margin)s, %(beaten_margin)s, %(official_margin_1)s, %(official_margin_2)s,
            %(starters)s, %(sectional_distance)s, %(sectional_time)s, %(sectional_location)s,
            %(rating_unadjusted)s, %(rating_adjusted)s, %(rating_handicap)s, %(rating_post_handicap)s,
            %(days_since_last_run)s, %(barrier_trial_indicator)s, %(blinker_indicator)s,
            %(stewards_report)s, %(running_gear)s, %(gear_changes)s, %(other_runners)s
        )
        ON CONFLICT (event_id) DO UPDATE SET
            finish_position  = EXCLUDED.finish_position,
            margin           = EXCLUDED.margin,
            rating_adjusted  = EXCLUDED.rating_adjusted,
            stewards_report  = EXCLUDED.stewards_report,
            updated_at       = NOW()
    """, past_run)


# Main ingest function
def ingest_parsed_data(data: dict, label: str = "feed"):
    """
    Take a fully parsed feed dict and upsert everything
    into the database in the correct FK order.
    """
    logger.info(f"Starting DB ingest: {label}")

    conn   = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Track
        track_id = upsert_track(cursor, data["track"])
        logger.info(f"  Track upserted: {data['track'].get('name')} (id={track_id})")

        # 2. Meeting
        meeting_data = {**data["meeting"], **{
            "track_surface"     : data["track"].get("track_surface"),
            "expected_condition": data["track"].get("expected_condition"),
            "weather"           : data["track"].get("weather"),
            "penetrometer"      : data["track"].get("penetrometer"),
            "irrigation"        : data["track"].get("irrigation"),
            "rainfall"          : data["track"].get("rainfall"),
            "track_info"        : data["track"].get("track_info"),
        }}
        meeting_id = upsert_meeting(cursor, meeting_data, track_id)
        logger.info(f"  Meeting upserted: {data['meeting'].get('meeting_date')} (id={meeting_id})")

        total_runners = 0
        total_past_runs = 0

        # 3. Loop races
        for race_data in data.get("races", []):
            race_num  = race_data.get("race_number", "?")
            race_name = race_data.get("race_name", "?")
            logger.info(f"  Processing Race {race_num}: {race_name}")

            race_id = upsert_race(cursor, {k: v for k, v in race_data.items() if k != "runners"}, meeting_id)
            logger.debug(f"    Race upserted: id={race_id}")

            # 4. Loop runners in each race
            for runner_data in race_data.get("runners", []):
                horse_name = runner_data["horse"].get("name", "?")
                logger.debug(f"    Upserting runner: {horse_name}")

                horse_id   = upsert_horse(cursor, runner_data["horse"])
                trainer_id = upsert_person(cursor, runner_data["trainer"])
                jockey_id  = upsert_person(cursor, runner_data["jockey"])

                runner_row = {k: v for k, v in runner_data["runner"].items()
                              if k not in ("xml_horse_id", "xml_trainer_id", "xml_jockey_id")}

                runner_id = upsert_runner(
                    cursor, runner_row, race_id, horse_id, trainer_id, jockey_id
                )

                upsert_statistics(cursor, runner_id, runner_data.get("statistics", []))
                upsert_ratings(cursor, runner_id, runner_data.get("ratings", []))

                past_runs = runner_data.get("past_runs", [])
                for past_run in past_runs:
                    upsert_past_run(cursor, runner_id, past_run)
                total_past_runs += len(past_runs)

                # Commit per runner so we dont hold a massive transaction
                conn.commit()
                total_runners += 1

            logger.info(f"    Race {race_num} done — {len(race_data.get('runners', []))} runners")

        logger.info(f"  All done — {len(data['races'])} races, {total_runners} runners, {total_past_runs} past runs")

    except Exception as e:
        conn.rollback()
        logger.error(f"  DB error — rolled back: {e}")
        raise

    finally:
        cursor.close()
        conn.close()