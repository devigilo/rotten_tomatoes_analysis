#!/usr/bin/env python
import argparse
import subprocess
import os
import sys
import time
import random
from datetime import datetime

def read_url_list(file_path):
    """Read URLs from a text file, one URL per line"""
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    return urls

def extract_movie_name(url):
    """Extract movie name from URL for display purposes"""
    parts = url.strip('/').split('/')
    if len(parts) >= 2 and parts[-2] == 'm':
        name = parts[-1].replace('_', ' ').title()
        return name
    return "Unknown Movie"

def process_urls(urls, output_dir, delay_min=60, delay_max=180, max_reviews=None, visible=False, max_attempts=25):
    """Process each URL by running the rotten-tomatoes-selenium-bugfix.py script"""
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    total_urls = len(urls)
    
    # Log file for results
    log_file = os.path.join(output_dir, f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    with open(log_file, 'w') as log:
        log.write(f"Batch Scraping started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Total URLs to process: {total_urls}\n\n")
        
        # Process each URL
        for i, url in enumerate(urls, 1):
            movie_name = extract_movie_name(url)
            
            print(f"\n[{i}/{total_urls}] Processing: {movie_name} ({url})")
            log.write(f"\n[{i}/{total_urls}] Processing: {movie_name} ({url})\n")
            log.write(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Build command
            command = [
                sys.executable,  # Current Python interpreter
                "rotten-tomatoes-selenium-bugfix.py",
                url,
                "--output", output_dir
            ]
            
            # Add optional parameters
            if max_reviews:
                command.extend(["--max-reviews", str(max_reviews)])
            
            if visible:
                command.append("--visible")
                
            if max_attempts:
                command.extend(["--max-attempts", str(max_attempts)])
            
            # Log the command
            log.write(f"Command: {' '.join(command)}\n")
            log.flush()  # Ensure log is written immediately
            
            try:
                # Run the script
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Log output
                log.write("STDOUT:\n")
                log.write(result.stdout)
                
                if result.stderr:
                    log.write("\nSTDERR:\n")
                    log.write(result.stderr)
                
                # Check if successful
                if result.returncode == 0:
                    status = "SUCCESS"
                else:
                    status = f"FAILED (Exit code: {result.returncode})"
                
                print(f"Status: {status}")
                log.write(f"\nStatus: {status}\n")
                
            except Exception as e:
                error_msg = f"Error running script: {str(e)}"
                print(f"Status: ERROR - {error_msg}")
                log.write(f"\nStatus: ERROR\n{error_msg}\n")
            
            log.write(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.flush()  # Ensure log is written immediately
            
            # If not the last URL, wait before processing the next one
            if i < total_urls:
                delay = random.uniform(delay_min, delay_max)
                print(f"Waiting {delay:.1f} seconds before processing next URL...")
                log.write(f"Waiting {delay:.1f} seconds before processing next URL...\n\n")
                log.flush()
                time.sleep(delay)
        
        # Final summary
        log.write(f"\nBatch processing completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Processed {total_urls} URLs\n")
    
    print(f"\nBatch processing complete! Results saved to {log_file}")
    return log_file

def main():
    parser = argparse.ArgumentParser(description='Process multiple Rotten Tomatoes URLs for review scraping')
    parser.add_argument('url_file', help='Text file containing list of Rotten Tomatoes review URLs, one per line')
    parser.add_argument('--output-dir', default='reviews', help='Directory to save review CSV files')
    parser.add_argument('--min-delay', type=int, default=60, help='Minimum delay between URLs in seconds (default: 60)')
    parser.add_argument('--max-delay', type=int, default=180, help='Maximum delay between URLs in seconds (default: 180)')
    parser.add_argument('--max-reviews', type=int, help='Maximum number of reviews to collect per URL (default: all)')
    parser.add_argument('--visible', action='store_true', help='Run Chrome in visible mode (not headless)')
    parser.add_argument('--max-attempts', type=int, default=25, help='Maximum attempts to click "Load More" per URL')
    
    args = parser.parse_args()
    
    # Check if URL file exists
    if not os.path.exists(args.url_file):
        print(f"Error: URL file '{args.url_file}' not found")
        return 1
    
    # Check if the rotten-tomatoes-selenium-bugfix.py script exists
    if not os.path.exists("rotten-tomatoes-selenium-bugfix.py"):
        print("Error: rotten-tomatoes-selenium-bugfix.py not found in the current directory")
        return 1
    
    # Read URLs from file
    urls = read_url_list(args.url_file)
    
    if not urls:
        print("No URLs found in the input file or all lines are commented out")
        return 1
    
    print(f"Found {len(urls)} URLs to process")
    
    # Process the URLs
    process_urls(
        urls,
        args.output_dir,
        delay_min=args.min_delay,
        delay_max=args.max_delay,
        max_reviews=args.max_reviews,
        visible=args.visible,
        max_attempts=args.max_attempts
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
