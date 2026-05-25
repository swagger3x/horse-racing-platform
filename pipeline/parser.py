"""
Parses horse racing XML feeds (FIELDS and FORM) into clean
Python dictionaries ready for database upsert.

Handles:
- Date conversion DD/MM/YYYY -> ISO 8601
- Fractional price parsing
- Nested statistics and ratings normalisation
- Graceful handling of missing/empty elements
"""

from datetime import datetime
from lxml import etree


# Utility helpers
def parse_date(value: str) -> str | None:
    """Convert DD/MM/YYYY to ISO 8601 (YYYY-MM-DD). Returns None if invalid."""
    if not value or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def safe_int(value) -> int | None:
    """Safely convert to int. Returns None if not possible."""
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def safe_float(value) -> float | None:
    """Safely convert to float. Returns None if not possible."""
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def safe_bool(value) -> bool | None:
    """Convert Y/N/True/False strings to bool."""
    if value is None:
        return None
    v = str(value).strip().upper()
    if v in ("Y", "YES", "TRUE", "1"):
        return True
    if v in ("N", "NO", "FALSE", "0"):
        return False
    return None


def safe_text(value) -> str | None:
    """Strip and return text. Returns None if empty."""
    if value is None:
        return None
    v = str(value).strip()
    return v if v else None


def parse_gear_items(element) -> list:
    """Extract list of gear_item text values from a running_gear element."""
    if element is None:
        return []
    return [
        item.text.strip()
        for item in element.findall("gear_item")
        if item.text and item.text.strip()
    ]


def parse_gear_changes(element) -> list:
    """Extract gear_changes as a list of dicts."""
    if element is None:
        return []
    changes = []
    for gc in element.findall("gear_change"):
        changes.append({
            "id"    : safe_int(gc.get("id")),
            "gear"  : safe_text(gc.get("gear")),
            "option": safe_text(gc.get("option")),
        })
    return changes


def parse_other_runners(element) -> list:
    """Extract other_runners as a list of dicts."""
    if element is None:
        return []
    runners = []
    for r in element.findall("other_runner"):
        runners.append({
            "position"            : safe_int(r.get("position")),
            "horse"               : safe_text(r.get("horse")),
            "jockey"              : safe_text(r.get("jockey")),
            "barrier"             : safe_int(r.get("barrier")),
            "weight"              : safe_float(r.get("weight")),
            "margin"              : safe_float(r.get("margin")),
            "country"             : safe_text(r.get("country")),
            "dead_heat_indicator" : safe_text(r.get("dead_heat_indicator")),
        })
    return runners


# Meeting & track parser
def parse_meeting(root: etree._Element) -> dict:
    """Parse meeting-level and track-level data."""
    track_el = root.find("track")

    meeting = {
        "meeting_date"     : parse_date(root.findtext("date")),
        "stage"            : safe_text(root.findtext("stage")),
        "tab_indicator"    : safe_text(root.findtext("tab_indicator")),
        "ra_meeting_id"    : safe_int(root.findtext("ra_meeting_id")),
        "dual_track"       : safe_bool(root.findtext("dual_track")),
        "rail_position"    : safe_text(root.findtext("rail_position")),
        "feed_directory"   : safe_text(root.find("product").get("directory") if root.find("product") is not None else None),
        "feed_file"        : safe_text(root.find("product").get("file") if root.find("product") is not None else None),
    }

    track = {}
    if track_el is not None:
        track = {
            "xml_track_id"      : safe_int(track_el.get("id")),
            "name"              : safe_text(track_el.get("name")),
            "country"           : safe_text(track_el.get("country")),
            "state"             : safe_text(track_el.get("state")),
            "location"          : safe_text(track_el.get("location")),
            "club"              : safe_text(track_el.get("club")),
            "track_3char_abbrev": safe_text(track_el.get("track_3char_abbrev")),
            "track_4char_abbrev": safe_text(track_el.get("track_4char_abbrev")),
            "track_6char_abbrev": safe_text(track_el.get("track_6char_abbrev")),
            # Day-specific (goes into meetings)
            "track_surface"     : safe_text(track_el.get("track_surface")),
            "expected_condition": safe_text(track_el.get("expected_condition")),
            "weather"           : safe_text(track_el.findtext("weather")),
            "penetrometer"      : safe_float(track_el.findtext("penetrometer")),
            "irrigation"        : safe_text(track_el.findtext("irrigation")),
            "rainfall"          : safe_text(track_el.findtext("rainfall")),
            "track_info"        : safe_text(track_el.findtext("track_info")),
        }

    return {"meeting": meeting, "track": track}


# Race parser
def parse_prizes(race_el: etree._Element) -> dict:
    """Extract prize money fields from a race element."""
    prizes = {
        "prize_1st"         : None,
        "prize_2nd"         : None,
        "prize_3rd"         : None,
        "prize_4th"         : None,
        "prize_5th"         : None,
        "prize_total"       : None,
        "prize_trophy_total": None,
    }
    prizes_el = race_el.find("prizes")
    if prizes_el is not None:
        for prize in prizes_el.findall("prize"):
            ptype = prize.get("type", "")
            val   = safe_int(prize.get("value"))
            if ptype == "1st":
                prizes["prize_1st"] = val
            elif ptype == "2nd":
                prizes["prize_2nd"] = val
            elif ptype == "3rd":
                prizes["prize_3rd"] = val
            elif ptype == "4th":
                prizes["prize_4th"] = val
            elif ptype == "5th":
                prizes["prize_5th"] = val
            elif ptype == "total_value":
                prizes["prize_total"] = val
            elif ptype == "trophy_total_value":
                prizes["prize_trophy_total"] = val
    return prizes


def parse_track_record(race_el: etree._Element) -> dict:
    """Extract track record from a race element."""
    result = {}
    tr = race_el.find(".//track_record")
    if tr is not None:
        horse_el = tr.find("horse")
        result["track_record_horse"] = safe_text(horse_el.get("name")) if horse_el is not None else None
        result["track_record_date"]  = parse_date(tr.findtext("meeting_date"))
        result["track_record_time"]  = safe_text(tr.findtext("duration"))
    return result


def parse_race(race_el: etree._Element) -> dict:
    """Parse a single race element into a dict."""
    race = {
        "xml_race_id"       : safe_int(race_el.get("id")),
        "race_number"       : safe_int(race_el.get("number")),
        "race_name"         : safe_text(race_el.get("name")),
        "nominations_number": safe_int(race_el.get("nominations_number")),
        "distance_m"        : safe_int(race_el.find("distance").get("metres")) if race_el.find("distance") is not None else None,
        "race_type"         : safe_text(race_el.findtext("race_type")),
        "weight_type"       : safe_text(race_el.findtext("weight_type")),
        "min_hcp_weight"    : safe_float(race_el.findtext("min_hcp_weight")),
        "size_field"        : safe_int(race_el.findtext("size_field")),
        "size_emergencies"  : safe_int(race_el.findtext("size_emergencies")),
        "start_time"        : safe_text(race_el.findtext("start_time")),
        "group_level"       : safe_int(race_el.findtext("group")),
    }

    # Class
    classes_el = race_el.find("classes")
    if classes_el is not None:
        race["class"]    = safe_text(classes_el.findtext("class"))
        race["class_id"] = safe_int(classes_el.findtext("class_id"))

    # Restrictions
    restr = race_el.find("restrictions")
    if restr is not None:
        race["restrictions_age"]    = safe_text(restr.get("age"))
        race["restrictions_sex"]    = safe_text(restr.get("sex"))
        race["restrictions_jockey"] = safe_text(restr.get("jockey"))

    # Prizes and track record
    race.update(parse_prizes(race_el))
    race.update(parse_track_record(race_el))

    return race


# Horse & people parsers
def parse_horse(horse_el: etree._Element) -> dict:
    """Parse permanent horse profile data."""
    sire_el        = horse_el.find("sire")
    dam_el         = horse_el.find("dam")
    sire_of_dam_el = horse_el.find("sire_of_dam")

    return {
        "xml_horse_id"      : safe_int(horse_el.get("id")),
        "ra_horse_id"       : safe_int(horse_el.get("horse_RA_Id")),
        "name"              : safe_text(horse_el.get("name")),
        "previous_name"     : safe_text(horse_el.get("previous_name")),
        "country"           : safe_text(horse_el.get("country")),
        "sex"               : safe_text(horse_el.get("sex")),
        "colour"            : safe_text(horse_el.get("colour")),
        "foaling_date"      : parse_date(horse_el.get("foaling_date")),
        # Breeding
        "sire_name"         : safe_text(sire_el.get("name")) if sire_el is not None else None,
        "sire_country"      : safe_text(sire_el.get("country")) if sire_el is not None else None,
        "sire_xml_id"       : safe_int(sire_el.get("id")) if sire_el is not None else None,
        "dam_name"          : safe_text(dam_el.get("name")) if dam_el is not None else None,
        "dam_country"       : safe_text(dam_el.get("country")) if dam_el is not None else None,
        "dam_xml_id"        : safe_int(dam_el.get("id")) if dam_el is not None else None,
        "sire_of_dam_name"  : safe_text(sire_of_dam_el.get("name")) if sire_of_dam_el is not None else None,
        "sire_of_dam_country": safe_text(sire_of_dam_el.get("country")) if sire_of_dam_el is not None else None,
        "sire_of_dam_xml_id": safe_int(sire_of_dam_el.get("id")) if sire_of_dam_el is not None else None,
    }


def parse_trainer(horse_el: etree._Element) -> dict | None:
    """Parse trainer data from a horse element."""
    trainer_el = horse_el.find("trainer")
    if trainer_el is None:
        return None
    return {
        "xml_person_id"      : safe_int(trainer_el.get("id")),
        "role"               : "trainer",
        "full_name"          : safe_text(trainer_el.get("name")),
        "firstname"          : safe_text(trainer_el.get("firstname")),
        "surname"            : safe_text(trainer_el.get("surname")),
        "ra_id"              : safe_int(trainer_el.get("trainer_RA_Id")),
        "apprentice_indicator": False,
        "allowance_weight"   : None,
    }


def parse_jockey(horse_el: etree._Element) -> dict | None:
    """Parse jockey data from a horse element."""
    jockey_el = horse_el.find("jockey")
    if jockey_el is None:
        return None
    return {
        "xml_person_id"      : safe_int(jockey_el.get("id")),
        "role"               : "jockey",
        "full_name"          : safe_text(jockey_el.get("name")),
        "firstname"          : safe_text(jockey_el.get("firstname")),
        "surname"            : safe_text(jockey_el.get("surname")),
        "ra_id"              : safe_int(jockey_el.get("jockey_RA_Id")),
        "apprentice_indicator": safe_bool(jockey_el.get("apprentice_indicator")) or False,
        "allowance_weight"   : safe_float(jockey_el.get("allowance_weight")),
    }


# Runner parser
def parse_statistics(horse_el: etree._Element, entity: str) -> list:
    """
    Parse statistics for a given entity (horse/trainer/jockey).
    Returns a list of stat dicts.
    """
    stats = []
    if entity == "horse":
        parent = horse_el.find("statistics")
    elif entity == "trainer":
        trainer_el = horse_el.find("trainer")
        parent = trainer_el.find("statistics") if trainer_el is not None else None
    elif entity == "jockey":
        jockey_el = horse_el.find("jockey")
        parent = jockey_el.find("statistics") if jockey_el is not None else None
    else:
        return stats

    if parent is None:
        return stats

    for stat in parent.findall("statistic"):
        stats.append({
            "entity"   : entity,
            "stat_type": safe_text(stat.get("type")),
            "total"    : safe_int(stat.get("total")) or 0,
            "firsts"   : safe_int(stat.get("firsts")) or 0,
            "seconds"  : safe_int(stat.get("seconds")) or 0,
            "thirds"   : safe_int(stat.get("thirds")) or 0,
        })
    return stats


def parse_ratings(horse_el: etree._Element) -> list:
    """Parse ratings block into a list of rating dicts."""
    ratings = []
    ratings_el = horse_el.find("ratings")
    if ratings_el is None:
        return ratings
    for rating in ratings_el.findall("rating"):
        val = safe_float(rating.get("value"))
        ratings.append({
            "rating_type": safe_text(rating.get("type")),
            "value"      : val,
            "rating_date": parse_date(rating.get("date")),
        })
    return ratings


def parse_runner(horse_el: etree._Element) -> dict:
    """Parse race-day specific runner data from a horse element."""
    weight_el  = horse_el.find("weight")
    market_el  = horse_el.find("market")
    trainer_el = horse_el.find("trainer")
    jockey_el  = horse_el.find("jockey")

    return {
        "xml_horse_id"        : safe_int(horse_el.get("id")),
        "xml_trainer_id"      : safe_int(trainer_el.get("id")) if trainer_el is not None else None,
        "xml_jockey_id"       : safe_int(jockey_el.get("id")) if jockey_el is not None else None,
        "tab_no"              : safe_int(horse_el.findtext("tab_no")),
        "barrier"             : safe_int(horse_el.findtext("barrier")),
        "selection"           : safe_int(horse_el.findtext("selection")),
        "weight_allocated"    : safe_float(weight_el.get("allocated")) if weight_el is not None else None,
        "weight_total"        : safe_float(weight_el.get("total")) if weight_el is not None else None,
        "market_price_frac"   : safe_text(market_el.get("price")) if market_el is not None else None,
        "market_price_decimal": safe_float(market_el.get("price_decimal")) if market_el is not None else None,
        "training_location"   : safe_text(horse_el.findtext("training_location")),
        "owners"              : safe_text(horse_el.findtext("owners")),
        "colours"             : safe_text(horse_el.findtext("colours")),
        "prizemoney_won"      : safe_int(horse_el.findtext("prizemoney_won")),
        "silks_url_jpg"       : safe_text(horse_el.findtext("horse_colours_image")),
        "silks_url_png"       : safe_text(horse_el.findtext("horse_colours_image_png")),
        "silks_url_svg"       : safe_text(horse_el.findtext("horse_colours_image_svg")),
        "last_four_starts"    : safe_text(horse_el.findtext("last_four_starts")),
        "last_ten_starts"     : safe_text(horse_el.findtext("last_ten_starts")),
        "last_fifteen_starts" : safe_text(horse_el.findtext("last_fifteen_starts")),
        "last_twenty_starts"  : safe_text(horse_el.findtext("last_twenty_starts")),
        "form_comments"       : safe_text(horse_el.findtext("form_comments")),
        "comments"            : safe_text(horse_el.findtext("comments")),
        "rating"              : safe_float(horse_el.findtext("rating")),
        "ff5_dry"             : safe_float(horse_el.findtext("FF5_dry")),
        "ff5_wet"             : safe_float(horse_el.findtext("FF5_wet")),
        "ff_dry_rating_100"   : safe_float(horse_el.findtext("FF_Dry_Rating_100")),
        "ff_wet_rating_100"   : safe_float(horse_el.findtext("FF_Wet_Rating_100")),
        "pace"                : safe_text(horse_el.findtext("pace")),
        "pace_value"          : safe_int(horse_el.findtext("pace_value")),
        "win_percentage"      : safe_float(horse_el.findtext("win_percentage")),
        "place_percentage"    : safe_float(horse_el.findtext("place_percentage")),
        "current_blinker_ind" : safe_text(horse_el.findtext("current_blinker_ind")),
        "running_gear"        : parse_gear_items(horse_el.find("running_gear")),
        "gear_changes"        : parse_gear_changes(horse_el.find("gear_changes")),
        "trainer_firststart"  : safe_bool(trainer_el.get("firststart")) if trainer_el is not None else None,
        "trainer_previous"    : safe_text(trainer_el.get("previous_trainer")) if trainer_el is not None else None,
        "trainer_previous_id" : safe_int(trainer_el.get("previous_trainer_id")) if trainer_el is not None else None,
        "scratched"           : safe_bool(horse_el.findtext("scratched")) or False,
    }


# Past run parser (FORM feed only)
def parse_past_run(form_el: etree._Element) -> dict:
    """Parse a single past run <form> element."""
    track_el    = form_el.find("track")
    positions_el = form_el.find("positions")
    rating_el   = form_el.find("rating")
    prices_el   = form_el.find("prices")
    dec_el      = form_el.find("decimalprices")
    sect_el     = form_el.find("sectional")
    jockey_el   = form_el.find("jockey")
    classes_el  = form_el.find("classes")
    restr_el    = form_el.find("restrictions")
    race_el     = form_el.find("race")
    dist_el     = form_el.find("distance")

    return {
        "event_id"              : safe_int(form_el.findtext("event_id")),
        "meeting_date"          : parse_date(form_el.findtext("meeting_date")),
        "rail_position"         : safe_text(form_el.findtext("rail_position")),
        # Track
        "track_name"            : safe_text(track_el.get("name")) if track_el is not None else None,
        "track_xml_id"          : safe_int(track_el.get("id")) if track_el is not None else None,
        "track_country"         : safe_text(track_el.get("country")) if track_el is not None else None,
        "track_condition"       : safe_text(track_el.get("condition")) if track_el is not None else None,
        "track_grading"         : safe_int(track_el.get("grading")) if track_el is not None else None,
        "track_surface"         : safe_text(track_el.get("track_surface")) if track_el is not None else None,
        "track_location"        : safe_text(track_el.get("location")) if track_el is not None else None,
        "track_state_no"        : safe_int(track_el.get("state_no")) if track_el is not None else None,
        "track_3char_abbrev"    : safe_text(track_el.get("track_3char_abbrev")) if track_el is not None else None,
        # Race
        "weight_type"           : safe_text(form_el.findtext("weight_type")),
        "race_number"           : safe_int(race_el.get("number")) if race_el is not None else None,
        "race_name"             : safe_text(race_el.get("name")) if race_el is not None else None,
        "distance_m"            : safe_int(dist_el.get("metres")) if dist_el is not None else None,
        "event_duration"        : safe_text(form_el.findtext("event_duration")),
        "group_level"           : safe_int(form_el.findtext("group")),
        "night_meeting"         : safe_bool(form_el.findtext("night_meeting")),
        # Restrictions
        "restrictions_age"      : safe_text(restr_el.get("age")) if restr_el is not None else None,
        "restrictions_sex"      : safe_text(restr_el.get("sex")) if restr_el is not None else None,
        "restrictions_jockey"   : safe_text(restr_el.get("jockey")) if restr_el is not None else None,
        # Class
        "class"                 : safe_text(classes_el.findtext("class")) if classes_el is not None else None,
        "class_id"              : safe_int(classes_el.findtext("class_id")) if classes_el is not None else None,
        "second_class"          : safe_text(classes_el.findtext("second_class")) if classes_el is not None else None,
        "second_class_id"       : safe_int(classes_el.findtext("second_class_id")) if classes_el is not None else None,
        # Prize
        "event_prizemoney"      : safe_int(form_el.findtext("event_prizemoney")),
        "horse_prizemoney"      : safe_int(form_el.findtext("horse_prizemoney")),
        "horse_prizemoney_bonus": safe_int(form_el.findtext("horse_prizemoney_bonus")),
        # Runner
        "barrier"               : safe_int(form_el.findtext("barrier")),
        "weight_carried"        : safe_float(form_el.findtext("weight_carried")),
        "weight_adj"            : safe_float(form_el.findtext("weight_adj")),
        "limit_weight"          : safe_float(form_el.findtext("limit_weight")),
        "jockey_name"           : safe_text(jockey_el.get("name")) if jockey_el is not None else None,
        "jockey_xml_id"         : safe_int(jockey_el.get("id")) if jockey_el is not None else None,
        "jockey_apprentice"     : safe_bool(jockey_el.get("apprentice_indicator")) if jockey_el is not None else None,
        # Prices
        "price_opening_frac"    : safe_text(prices_el.get("opening")) if prices_el is not None else None,
        "price_mid_frac"        : safe_text(prices_el.get("mid")) if prices_el is not None else None,
        "price_sp_frac"         : safe_text(prices_el.get("starting")) if prices_el is not None else None,
        "price_opening_dec"     : safe_float(dec_el.get("opening")) if dec_el is not None else None,
        "price_mid_dec"         : safe_float(dec_el.get("mid")) if dec_el is not None else None,
        "price_sp_dec"          : safe_float(dec_el.get("starting")) if dec_el is not None else None,
        "favourite_indicator"   : safe_bool(form_el.findtext("favourite_indicator")),
        # Positions
        "pos_settling"          : safe_int(positions_el.get("settling_down")) if positions_el is not None else None,
        "pos_m400"              : safe_int(positions_el.get("m400")) if positions_el is not None else None,
        "pos_m800"              : safe_int(positions_el.get("m800")) if positions_el is not None else None,
        "pos_m1200"             : safe_int(positions_el.get("m1200")) if positions_el is not None else None,
        "pos_finish"            : safe_int(positions_el.get("finish")) if positions_el is not None else None,
        "finish_position"       : safe_text(form_el.findtext("finish_position")),
        # Margins
        "margin"                : safe_float(form_el.findtext("margin")),
        "beaten_margin"         : safe_float(form_el.findtext("beaten_margin")),
        "official_margin_1"     : safe_text(form_el.findtext("official_margin_1")),
        "official_margin_2"     : safe_text(form_el.findtext("official_margin_2")),
        "starters"              : safe_int(form_el.findtext("starters")),
        # Sectionals
        "sectional_distance"    : safe_int(sect_el.get("distance")) if sect_el is not None else None,
        "sectional_time"        : safe_text(sect_el.get("time")) if sect_el is not None else None,
        "sectional_location"    : safe_text(sect_el.get("location")) if sect_el is not None else None,
        # Ratings
        "rating_unadjusted"     : safe_float(rating_el.get("unadjusted")) if rating_el is not None else None,
        "rating_adjusted"       : safe_float(rating_el.get("adjusted")) if rating_el is not None else None,
        "rating_handicap"       : safe_float(rating_el.get("handicap")) if rating_el is not None else None,
        "rating_post_handicap"  : safe_float(rating_el.get("post_handicap")) if rating_el is not None else None,
        # Other
        "days_since_last_run"   : safe_int(form_el.findtext("days_since_last_run")),
        "barrier_trial_indicator": safe_bool(form_el.findtext("barrier_trial_indicator")),
        "blinker_indicator"     : safe_text(form_el.findtext("blinker_indicator")),
        "stewards_report"       : safe_text(form_el.find(".//stewards_report").text if form_el.find(".//stewards_report") is not None else None),
        "running_gear"          : parse_gear_items(form_el.find("running_gear")),
        "gear_changes"          : parse_gear_changes(form_el.find("gear_changes")),
        "other_runners"         : parse_other_runners(form_el.find("other_runners")),
    }


# Main parse function
def parse_feed(filepath: str) -> dict:
    """
    Parse a full XML feed file (FIELDS or FORM).
    Returns a structured dict with all data ready for upsert.
    """
    tree = etree.parse(filepath)
    root = tree.getroot()

    result = parse_meeting(root)
    result["races"] = []

    for race_el in root.findall("./races/race"):
        race_data = parse_race(race_el)
        race_data["runners"] = []

        for horse_el in race_el.findall(".//horse"):
            runner = {
                "horse"     : parse_horse(horse_el),
                "trainer"   : parse_trainer(horse_el),
                "jockey"    : parse_jockey(horse_el),
                "runner"    : parse_runner(horse_el),
                "statistics": (
                    parse_statistics(horse_el, "horse") +
                    parse_statistics(horse_el, "trainer") +
                    parse_statistics(horse_el, "jockey")
                ),
                "ratings"   : parse_ratings(horse_el),
                "past_runs" : [],
            }

            # Past runs — only present in FORM feed
            forms_el = horse_el.find("forms")
            if forms_el is not None:
                for form_el in forms_el.findall("form"):
                    try:
                        runner["past_runs"].append(parse_past_run(form_el))
                    except Exception as e:
                        print(f"  [WARN] Skipping past run: {e}")

            race_data["runners"].append(runner)

        result["races"].append(race_data)

    return result