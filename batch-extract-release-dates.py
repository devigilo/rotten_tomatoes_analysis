#!/usr/bin/env python
import os
import re
import glob
import argparse
import subprocess
from datetime import datetime

def extract_release_date_from_filename(filename):
    """
    Extract the release date from a filename in the format:
    MOVIE_NAME_YYYY-MM-DD_YYYYMMDD_HHMMSS.csv
    
    Returns the date in YYYY-MM-DD format, or None if not found
    """
    # Pattern to match the date in format YYYY-MM-DD in the filename
    pattern = r'_(\d{4}-\d{2}-\d{2})_\d{8}_\d{6}\.csv$'
    match = re.search(pattern, filename)
    
    if match:
        return match.group(1)
    else:
        # Try alternate pattern without underscores
        alt_pattern = r'(\d{4}-\d{2}-\d{2})_\d{8}_\d{6}\.csv$'
        match = re.search(alt_pattern, filename)
        if match:
            return match.group(1)
    
    return None

def extract_movie_name_from_filename(filename):
    """
    Extract the movie name from a filename in the format:
    MOVIE_NAME_YYYY-MM-DD_YYYYMMDD_HHMMSS.csv
    
    Returns the movie name with spaces instead of underscores
    """
    # Get base filename without path
    base_filename = os.path.basename(filename)
    
    # Pattern to match everything before the release date
    pattern = r'^(.+?)_\d{4}-\d{2}-\d{2}_\d{8}_\d{6}\.csv$'
    match = re.search(pattern, base_filename)
    
    if match:
        # Convert underscores to spaces for display
        return match.group(1).replace('_', ' ')
    
    return "Unknown Movie"

def process_csv_files(csv_dir, cutoff_days, output_dir, rt_script_path):
    """
    Process all CSV files in the given directory, extract release dates, 
    and run the cutoff script for each file
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all CSV files in the directory
    csv_files = glob.glob(os.path.join(csv_dir, "*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in {csv_dir}")
        return
    
    print(f"Found {len(csv_files)} CSV files to process")
    
    # Process each CSV file
    for csv_file in csv_files:
        # Extract release date from filename
        release_date = extract_release_date_from_filename(csv_file)
        
        if not release_date:
            print(f"Could not extract release date from {csv_file}, skipping...")
            continue
        
        # Extract movie name from filename
        movie_name = extract_movie_name_from_filename(csv_file)
        
        # Generate output filename
        base_name = os.path.basename(csv_file).split('.')[0]
        output_file = os.path.join(output_dir, f"{base_name}_{cutoff_days}day.png")
        
        print(f"\nProcessing: {movie_name} (Release Date: {release_date})")
        print(f"- Input file: {csv_file}")
        print(f"- Output file: {output_file}")
        
        # Build command to run the cutoff script
        command = [
            "python", 
            rt_script_path,
            "--file", csv_file,
            "--movie-name", f'"{movie_name}"',
            "--release-date", release_date,
            "--days-cutoff", str(cutoff_days),
            "--output", output_file,
            "--save-data"
        ]
        
        # Print the command
        print(f"- Running command: {' '.join(command)}")
        
        # Run the command
        try:
            result = subprocess.run(
                command, 
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"- Command completed successfully")
            
            # Optional: print some of the output
            output_lines = result.stdout.strip().split("\n")
            if output_lines:
                for line in output_lines[-5:]:  # Print last 5 lines
                    print(f"  {line}")
                    
        except subprocess.CalledProcessError as e:
            print(f"- ERROR: Command failed with exit code {e.returncode}")
            print(f"- Error message: {e.stderr}")
        except Exception as e:
            print(f"- ERROR: Failed to run command: {str(e)}")
        
        print("-" * 50)

def main():
    parser = argparse.ArgumentParser(description='Batch process Rotten Tomatoes review CSV files with cutoff script')
    parser.add_argument('--csv-dir', required=True, help='Directory containing CSV files')
    parser.add_argument('--cutoff-days', type=int, default=4, help='Number of days after release to include (default: 4)')
    parser.add_argument('--output-dir', default='plots', help='Directory to save output files')
    parser.add_argument('--script', default='rt-score-cutoff.py', help='Path to the RT score cutoff script')
    
    args = parser.parse_args()
    
    # Check if cutoff script exists
    if not os.path.exists(args.script):
        print(f"Error: Cutoff script not found at {args.script}")
        return 1
        
    # Process the files
    process_csv_files(args.csv_dir, args.cutoff_days, args.output_dir, args.script)
    
    return 0

if __name__ == "__main__":
    exit(main())
