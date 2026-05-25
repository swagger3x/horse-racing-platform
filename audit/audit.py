"""
Reads both FIELDS and FORM XML files and produces a detailed
field map report showing all available elements, attributes,
data types, and statistics.

Usage:
    python audit/audit.py --fields sample-data/FLE_FIELDS_XML_A.xml
                          --form   sample-data/FLE_FORM_XML_A.xml
"""

import argparse
import os
import sys
from datetime import datetime
from lxml import etree


# Helpers
def parse_xml(filepath: str) -> etree._Element:
    """Parse an XML file and return the root element."""
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)
    print(f"  Parsing: {filepath} ({os.path.getsize(filepath) / 1024:.1f} KB)")
    tree = etree.parse(filepath)
    return tree.getroot()


def infer_type(value: str) -> str:
    """Infer the data type of a string value."""
    if value is None or value.strip() == "":
        return "empty"
    v = value.strip()
    if v.upper() in ("Y", "N", "YES", "NO", "TRUE", "FALSE"):
        return "boolean"
    try:
        datetime.strptime(v, "%d/%m/%Y")
        return "date (DD/MM/YYYY)"
    except ValueError:
        pass
    if ":" in v and "." in v:
        return "duration (M:SS.mm)"
    try:
        int(v)
        return "integer"
    except ValueError:
        pass
    try:
        float(v)
        return "numeric"
    except ValueError:
        pass
    if "/" in v and len(v) <= 10:
        parts = v.split("/")
        if len(parts) == 2 and all(p.strip().isdigit() for p in parts):
            return "fractional price"
    if v.startswith("http://") or v.startswith("https://"):
        return "url"
    return "text"


def collect_fields(element: etree._Element,
                   path: str,
                   field_map: dict,
                   depth: int = 0,
                   max_depth: int = 10):
    """
    Recursively walk every element and collect:
    - element path
    - attributes and their inferred types
    - text content and its inferred type
    """
    if depth > max_depth:
        return

    for attr_name, attr_value in element.attrib.items():
        key = f"{path}[@{attr_name}]"
        inferred = infer_type(attr_value)
        if key not in field_map:
            field_map[key] = {"kind": "attribute", "types": set(), "samples": [], "count": 0}
        field_map[key]["types"].add(inferred)
        field_map[key]["count"] += 1
        if len(field_map[key]["samples"]) < 3 and attr_value.strip():
            field_map[key]["samples"].append(attr_value.strip()[:60])

    text = element.text
    if text and text.strip():
        key = f"{path}[text]"
        inferred = infer_type(text)
        if key not in field_map:
            field_map[key] = {"kind": "text", "types": set(), "samples": [], "count": 0}
        field_map[key]["types"].add(inferred)
        field_map[key]["count"] += 1
        if len(field_map[key]["samples"]) < 3:
            field_map[key]["samples"].append(text.strip()[:60])

    for child in element:
        child_path = f"{path}/{child.tag}"
        collect_fields(child, child_path, field_map, depth + 1, max_depth)


def gather_stats(root: etree._Element) -> dict:
    """Gather high-level statistics from the XML."""
    stats = {}
    stats["meeting_date"] = root.findtext("date", "N/A").strip()
    stats["stage"]        = root.findtext("stage", "N/A").strip()
    stats["ra_meeting_id"]= root.findtext("ra_meeting_id", "N/A").strip()

    track = root.find("track")
    if track is not None:
        stats["track_name"]         = track.get("name", "N/A")
        stats["track_country"]      = track.get("country", "N/A")
        stats["track_surface"]      = track.get("track_surface", "N/A")
        stats["expected_condition"] = track.get("expected_condition", "N/A")
        stats["weather"]            = track.findtext("weather", "N/A").strip()

    races = root.findall("./races/race")
    stats["total_races"] = len(races)

    total_runners = 0
    race_details  = []
    for race in races:
        horses = race.findall(".//horse")
        total_runners += len(horses)
        dist_el = race.find("distance")
        distance = dist_el.get("metres", "") if dist_el is not None else ""
        race_details.append({
            "number"  : race.get("number") or "",
            "name"    : race.get("name") or "",
            "distance": distance,
            "runners" : len(horses),
        })

    stats["total_runners"]      = total_runners
    stats["race_details"]       = race_details
    stats["total_form_entries"] = len(root.findall(".//form"))
    return stats


# Report printers
def sep(char="─", width=90):
    print(char * width)

def header(title):
    sep("═")
    print(f"  {title}")
    sep("═")

def section(title):
    print()
    sep()
    print(f"  {title}")
    sep()

def print_stats(label, stats):
    section(f"MEETING STATS — {label}")
    print(f"  Track          : {stats.get('track_name','N/A')} ({stats.get('track_country','N/A')})")
    print(f"  Date           : {stats.get('meeting_date','N/A')}")
    print(f"  Stage          : {stats.get('stage','N/A')}")
    print(f"  RA Meeting ID  : {stats.get('ra_meeting_id','N/A')}")
    print(f"  Surface        : {stats.get('track_surface','N/A')}")
    print(f"  Condition      : {stats.get('expected_condition','N/A')}")
    print(f"  Weather        : {stats.get('weather','N/A')}")
    print(f"  Total Races    : {stats.get('total_races',0)}")
    print(f"  Total Runners  : {stats.get('total_runners',0)}")
    if stats.get("total_form_entries", 0) > 0:
        print(f"  Form Entries   : {stats.get('total_form_entries',0)}")
    print()
    print(f"  {'Race':<6} {'Name':<45} {'Dist(m)':<10} Runners")
    print(f"  {'─'*6} {'─'*45} {'─'*10} {'─'*7}")
    for r in stats.get("race_details", []):
        print(f"  R{r['number']:<5} {r['name']:<45} {r['distance']:<10} {r['runners']}")

def print_field_map(label, field_map):
    section(f"FIELD MAP — {label}  ({len(field_map)} unique fields)")
    print(f"  {'Field Path':<68} {'Kind':<10} {'Type(s)':<25} Samples")
    print(f"  {'─'*68} {'─'*10} {'─'*25} {'─'*20}")
    for path, info in sorted(field_map.items()):
        types_str   = ", ".join(sorted(info["types"]))
        samples_str = " | ".join(info["samples"][:2])
        if len(samples_str) > 38:
            samples_str = samples_str[:35] + "..."
        print(f"  {path:<68} {info['kind']:<10} {types_str:<25} {samples_str}")

def print_ingestion_notes():
    section("INGESTION NOTES")
    notes = [
        ("Dates",             "DD/MM/YYYY throughout — convert to ISO 8601 before storing"),
        ("Durations",         "'1:08.10' — parse to PostgreSQL interval type"),
        ("Fractional prices", "'5/4' — store both fractional string and decimal float"),
        ("Statistics",        "28 typed <statistic> elements — normalise into runners_statistics"),
        ("Ratings",           "25 typed <rating> elements — normalise into runners_ratings"),
        ("Upsert keys",       "meeting: track+date | race: xml_race_id | horse: xml_horse_id | run: event_id"),
        ("Silks URLs",        "Fully formed HTTPS URLs — store directly in runners table"),
        ("running_gear",      "Multiple <gear_item> children — store as PostgreSQL text[]"),
        ("FORM only",         "<forms> block only in FORM file — skip gracefully if absent"),
        ("Unknown fields",    "Use extra_data JSONB column to catch any unrecognised fields"),
    ]
    for label, note in notes:
        print(f"  • {label:<22} {note}")

def print_table_mapping():
    section("RECOMMENDED DATABASE TABLE MAPPING")
    mappings = [
        ("meetings",           "meeting.* + track.*"),
        ("races",              "race[number, name, id, distance, type, class, prizes...]"),
        ("horses",             "horse[id, name, country, sex, age, sire, dam, sire_of_dam...]"),
        ("people",             "trainer[id, name] + jockey[id, name, apprentice, allowance...]"),
        ("runners",            "horse entry per race [barrier, weight, tab_no, market, gear, silks...]"),
        ("past_runs",          "form[event_id, date, track, positions, margin, prices, ratings...]"),
        ("runners_statistics", "statistic[type, total, firsts, seconds, thirds] — 28 types"),
        ("runners_ratings",    "rating[type, value, date] — 25 types"),
    ]
    print(f"  {'Table':<25} XML Source")
    print(f"  {'─'*25} {'─'*55}")
    for table, source in mappings:
        print(f"  {table:<25} {source}")


# Main
def main():
    parser = argparse.ArgumentParser(description="Horse Racing XML Feed Audit Tool")
    parser.add_argument("--fields", required=True, help="Path to FIELDS XML file")
    parser.add_argument("--form",   required=True, help="Path to FORM XML file")
    args = parser.parse_args()

    header("HORSE RACING XML FEED AUDIT REPORT")
    print(f"  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Fields    : {args.fields}")
    print(f"  Form      : {args.form}")
    print()
    print("  Loading files...")

    fields_root = parse_xml(args.fields)
    form_root   = parse_xml(args.form)
    print("  Done.")

    # Stats
    fields_stats = gather_stats(fields_root)
    form_stats   = gather_stats(form_root)
    print_stats("FIELDS FILE", fields_stats)
    print_stats("FORM FILE",   form_stats)

    # Field maps
    fields_map = {}
    form_map   = {}
    print()
    print("  Building field maps (may take a moment for large files)...")
    collect_fields(fields_root, fields_root.tag, fields_map)
    collect_fields(form_root,   form_root.tag,   form_map)
    print(f"  Fields file : {len(fields_map)} unique fields")
    print(f"  Form file   : {len(form_map)} unique fields")

    form_only = {k: v for k, v in form_map.items() if k not in fields_map}

    print_field_map("FIELDS FILE", fields_map)
    print_field_map("FORM FILE — Fields not present in FIELDS file", form_only)

    print_ingestion_notes()
    print_table_mapping()

    # Summary
    section("SUMMARY")
    print(f"  FIELDS file unique fields  : {len(fields_map)}")
    print(f"  FORM file unique fields    : {len(form_map)}")
    print(f"  Fields only in FORM file   : {len(form_only)}")
    print(f"  Total races                : {fields_stats['total_races']}")
    print(f"  Total runners              : {fields_stats['total_runners']}")
    print(f"  Total past run records     : {form_stats['total_form_entries']}")
    print()
    sep("═")
    print("  Audit complete.")
    sep("═")


if __name__ == "__main__":
    main()