# Rotten Tomatoes Analysis

This project contains tools for scraping review data from Rotten Tomatoes and analyzing score evolution over time.

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. (Optional) Install Selenium web driver such as ChromeDriver and ensure it is available on your `PATH`.

## Usage

### Scraping Reviews

The scraper can be run via the `rt_scraper` CLI module. Example:

```bash
python -m rt_scraper.cli --url https://www.rottentomatoes.com/m/top_gun_maverick
```

### Processing Scores

`rt-score-cutoff.py` calculates daily cumulative scores and generates a plot. Example:

```bash
python rt-score-cutoff.py --file data/Top_Gun_Maverick_2022-05-27_20250531_235717.csv \
  --movie-name "Top Gun Maverick" --release-date 2022-05-27 --days-cutoff 4 \
  --output data/topgun_maverick_4day.png --save-data
```

### Batch Processing

Use `batch_processor.py` to run the cutoff script against a directory of CSV files:

```bash
python batch_processor.py --csv-dir data --cutoff-days 4
```

## Data Directory

Sample CSV and image outputs are stored in the `data/` folder. Large datasets should not be committed to version control.

## License

See [LICENSE](LICENSE) for license information.
