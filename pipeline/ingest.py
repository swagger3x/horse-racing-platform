"""
Main pipeline entry point for the horse racing data platform.

Modes:
    --once      Run a single ingest cycle and exit
    --schedule  Run on a repeating schedule (every N minutes from .env)
    --file      Ingest a specific local XML file (for testing)

Usage:
    python pipeline/ingest.py --file sample-data/FLE_FIELDS_XML_A.xml
    python pipeline/ingest.py --once
    python pipeline/ingest.py --schedule
"""

import argparse
import os
import sys
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

from parser import parse_feed
from db import ingest_parsed_data

load_dotenv()


# Config
FEED_BASE_URL       = os.getenv("XML_FEED_BASE_URL", "")
FEED_USERNAME       = os.getenv("XML_FEED_USERNAME", "")
FEED_PASSWORD       = os.getenv("XML_FEED_PASSWORD", "")
FETCH_INTERVAL_MINS = int(os.getenv("FETCH_INTERVAL_MINUTES", "30"))
LOG_LEVEL           = os.getenv("LOG_LEVEL", "INFO")

logger.remove()
logger.add(sys.stdout, level="DEBUG", format="{time:HH:mm:ss} | {level} | {message}")
logger.add("docs/pipeline.log", level="DEBUG", rotation="10 MB",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


# Feed fetcher — STUB (Replace this function when real feed URL is available)
def fetch_feed_files() -> list[str]:
    """
    STUB: Fetch XML feed files from the provider.

    In production this will:
    1. Call the provider API/FTP to get today's feed URLs
    2. Download the FIELDS and FORM XML files
    3. Save them to a temp folder
    4. Return the local file paths

    Returns:
        List of local file paths to process
    """
    logger.warning("fetch_feed_files() is a STUB — no real URL configured yet")
    logger.info(f"  Feed base URL : {FEED_BASE_URL or 'NOT SET'}")
    logger.info(f"  Feed username : {FEED_USERNAME or 'NOT SET'}")
    logger.info("  Returning empty list — nothing to ingest from remote")
    return []


def fetch_todays_files() -> list[str]:
    """
    STUB: Build today's expected filenames and fetch them.

    Medialityracing naming convention:
        {TRACK}{YYYYMMDD}.XML  (FIELDS)
        {TRACK}{YYYYMMDD}_FORM.XML  (FORM)
    """
    today = datetime.now().strftime("%Y%m%d")
    logger.info(f"  Would fetch files for date: {today}")

    # TODO: Replace with real HTTP/FTP fetch when credentials available
    # Example structure when implemented:
    # import requests
    # fields_url = f"{FEED_BASE_URL}/{today}_FIELDS.XML"
    # form_url   = f"{FEED_BASE_URL}/{today}_FORM.XML"
    # response = requests.get(fields_url, auth=(FEED_USERNAME, FEED_PASSWORD))
    # ...save to temp file...
    # return [fields_path, form_path]

    return fetch_feed_files()


# Ingest cycle
def run_ingest_cycle(filepaths: list[str]):
    """Process a list of XML file paths through parse -> db upsert."""
    if not filepaths:
        logger.info("No files to process this cycle.")
        return

    for filepath in filepaths:
        if not os.path.exists(filepath):
            logger.warning(f"File not found, skipping: {filepath}")
            continue

        logger.info(f"Processing: {filepath}")
        try:
            label     = os.path.basename(filepath)
            data      = parse_feed(filepath)
            ingest_parsed_data(data, label=label)
            logger.success(f"Completed: {filepath}")
        except Exception as e:
            logger.error(f"Failed to process {filepath}: {e}")


def run_once():
    """Fetch and ingest once then exit."""
    logger.info("=" * 50)
    logger.info("Running single ingest cycle")
    logger.info("=" * 50)
    filepaths = fetch_todays_files()
    run_ingest_cycle(filepaths)
    logger.info("Single cycle complete.")


def run_scheduled():
    """Run on a schedule indefinitely."""
    logger.info("=" * 50)
    logger.info(f"Starting scheduled pipeline — every {FETCH_INTERVAL_MINS} minutes")
    logger.info("=" * 50)

    schedule.every(FETCH_INTERVAL_MINS).minutes.do(lambda: run_ingest_cycle(fetch_todays_files()))

    # Run immediately on start
    run_ingest_cycle(fetch_todays_files())

    while True:
        schedule.run_pending()
        time.sleep(30)


def run_local_file(filepath: str):
    """Ingest a specific local file — used for testing."""
    logger.info("=" * 50)
    logger.info(f"Ingesting local file: {filepath}")
    logger.info("=" * 50)
    run_ingest_cycle([filepath])
    logger.success("Done.")


# Entry point
def main():
    parser = argparse.ArgumentParser(description="Horse Racing XML Ingestion Pipeline")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once",     action="store_true", help="Run one cycle and exit")
    group.add_argument("--schedule", action="store_true", help="Run on a repeating schedule")
    group.add_argument("--file",     type=str,            help="Ingest a specific local XML file")
    args = parser.parse_args()

    if args.file:
        run_local_file(args.file)
    elif args.once:
        run_once()
    elif args.schedule:
        run_scheduled()


if __name__ == "__main__":
    main()