#!/usr/bin/env python
"""Command line interface for scraping Rotten Tomatoes reviews."""

import argparse
from .scraper import (
    extract_movie_title,
    scrape_reviews_with_selenium,
    save_reviews,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Rotten Tomatoes reviews using Selenium")
    parser.add_argument("url", help="Rotten Tomatoes movie reviews URL")
    parser.add_argument("--max-reviews", type=int, default=None, help="Maximum number of reviews to collect")
    parser.add_argument("--min-delay", type=int, default=1, help="Minimum delay between clicks")
    parser.add_argument("--max-delay", type=int, default=3, help="Maximum delay between clicks")
    parser.add_argument("--scroll-delay", type=float, default=1, help="Delay after scrolling")
    parser.add_argument("--max-attempts", type=int, default=25, help="Maximum attempts to click Load More")
    parser.add_argument("--output", default="reviews", help="Output directory for CSV files")
    parser.add_argument("--visible", action="store_true", help="Run Chrome visibly (not headless)")
    args = parser.parse_args()

    movie_title = extract_movie_title(args.url)
    if movie_title:
        print(f"Scraping reviews for: {movie_title}")

    reviews, release_date = scrape_reviews_with_selenium(
        args.url,
        max_reviews=args.max_reviews,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        scroll_delay=args.scroll_delay,
        headless=not args.visible,
        max_attempts=args.max_attempts,
    )

    if reviews:
        save_reviews(reviews, movie_title, release_date, args.output)
        print(f"Total reviews collected: {len(reviews)}")
    else:
        print("No reviews were collected.")


if __name__ == "__main__":
    main()
