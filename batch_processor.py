#!/usr/bin/env python
"""Batch process Rotten Tomatoes review CSV files."""

from __future__ import annotations

import argparse
import glob
import logging
import os
import re
import subprocess
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def extract_release_date_from_filename(filename: str) -> str | None:
    """Return release date ``YYYY-MM-DD`` extracted from *filename*."""
    pattern = r"_(\d{4}-\d{2}-\d{2})_\d{8}_\d{6}\.csv$"
    match = re.search(pattern, filename)
    if match:
        return match.group(1)
    alt_pattern = r"(\d{4}-\d{2}-\d{2})_\d{8}_\d{6}\.csv$"
    match = re.search(alt_pattern, filename)
    if match:
        return match.group(1)
    return None


def extract_movie_name_from_filename(filename: str) -> str:
    """Return movie name from *filename* with spaces instead of underscores."""
    base_filename = os.path.basename(filename)
    pattern = r"^(.+?)_\d{4}-\d{2}-\d{2}_\d{8}_\d{6}\.csv$"
    match = re.search(pattern, base_filename)
    if match:
        return match.group(1).replace("_", " ")
    return "Unknown Movie"


def process_csv_files(csv_dir: str, cutoff_days: int, output_dir: str, rt_script_path: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    csv_files = glob.glob(os.path.join(csv_dir, "*.csv"))
    if not csv_files:
        logging.warning("No CSV files found in %s", csv_dir)
        return
    logging.info("Found %d CSV files to process", len(csv_files))
    for csv_file in csv_files:
        release_date = extract_release_date_from_filename(csv_file)
        if not release_date:
            logging.warning("Could not extract release date from %s, skipping", csv_file)
            continue
        movie_name = extract_movie_name_from_filename(csv_file)
        base_name = os.path.basename(csv_file).split('.')[0]
        output_file = os.path.join(output_dir, f"{base_name}_{cutoff_days}day.png")
        command = [
            "python",
            rt_script_path,
            "--file", csv_file,
            "--movie-name", movie_name,
            "--release-date", release_date,
            "--days-cutoff", str(cutoff_days),
            "--output", output_file,
            "--save-data",
        ]
        logging.info("Running: %s", ' '.join(command))
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            logging.error("Command failed: %s", exc)
        logging.info("%s", "-" * 40)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch process Rotten Tomatoes review CSV files")
    parser.add_argument("--csv-dir", required=True, help="Directory containing CSV files")
    parser.add_argument("--cutoff-days", type=int, default=4, help="Days after release to include")
    parser.add_argument("--output-dir", default="plots", help="Directory to save output files")
    parser.add_argument("--script", default="rt-score-cutoff.py", help="Path to the RT score script")
    args = parser.parse_args()
    if not os.path.exists(args.script):
        logging.error("Cutoff script not found at %s", args.script)
        return 1
    process_csv_files(args.csv_dir, args.cutoff_days, args.output_dir, args.script)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
