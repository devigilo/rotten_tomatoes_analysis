import time
import random
import os
import argparse
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
import re
import sys

global_title = "placeholder"

def extract_release_date(driver):
    """Extract the movie release date from the page if available"""
    try:
        # Try to find the release date in the sidebar information
        release_date_element = driver.find_element(By.XPATH, "//li[contains(text(), 'In Theaters:')]")
        if release_date_element:
            # Extract the text and clean it up
            release_date_text = release_date_element.text.replace('In Theaters:', '').strip()
            # Convert to a standardized format (YYYY-MM-DD)
            try:
                date_obj = datetime.strptime(release_date_text, '%b %d, %Y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                # If parsing fails, return the original text
                return release_date_text.replace(' ', '_').replace(',', '')
    except (NoSuchElementException, Exception) as e:
        print(f"Could not extract release date: {e}")
    
    return None

def clean_filename(filename):
    """
    Remove characters that aren't allowed in filenames across various operating systems.
    Also limits excessive whitespace and ensures the filename isn't too long.
    
    Args:
        filename (str): The string to clean
        
    Returns:
        str: A cleaned string that can safely be used as a filename
    """
    # Remove characters that are generally not allowed in filenames
    # across Windows, macOS, and Linux
    
    # Windows specifically forbids these characters: \ / : * ? " < > |
    # Replace them with underscores
    forbidden_chars = r'[\\/:*?"<>|]'
    safe_filename = re.sub(forbidden_chars, '_', filename)
    
    # Remove any control characters
    safe_filename = re.sub(r'[\x00-\x1f\x7f]', '', safe_filename)
    
    # Remove leading/trailing whitespace and dots
    safe_filename = safe_filename.strip(' .')
    
    # Replace multiple spaces with a single underscore
    safe_filename = re.sub(r'\s+', '_', safe_filename)
    
    # Make sure we don't have too many consecutive underscores
    safe_filename = re.sub(r'_+', '_', safe_filename)
    
    # Ensure filename isn't too long (Windows has a 255 character limit for path+filename)
    # Using 100 as a safe limit for the filename portion
    max_length = 100
    if len(safe_filename) > max_length:
        name_part, ext_part = os.path.splitext(safe_filename)
        safe_filename = name_part[:max_length-len(ext_part)] + ext_part
    
    # If by any chance we ended up with an empty string, use a default
    if not safe_filename:
        safe_filename = "unnamed_file"
    
    return safe_filename

def setup_driver(headless=True):
    """Set up and return a Selenium WebDriver for Chrome"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")  # Updated headless flag
    
    # Add additional options to make the browser more stable and less detectable
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Set user agent to appear more like a real browser
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36")
    
    # Create the driver
    driver = webdriver.Chrome(options=chrome_options)
    
    # Set window size to a common desktop resolution
    driver.set_window_size(1366, 768)
    
    return driver

def extract_movie_title(url):
    """Extract movie title from the URL"""
    try:
        # Extract movie title from URL (e.g., /m/beauty_and_the_beast_2017/ -> Beauty and the Beast 2017)
        parts = url.strip('/').split('/')
        if len(parts) >= 2 and parts[-2] == 'm':
            title = parts[-1].replace('_', ' ').title()
            return title
    except:
        pass
    return None

def wait_for_load_more_button(driver, timeout=10):
    """Wait for the Load More button to be clickable, with fallbacks for different button types"""
    try:
        # Try different selector strategies to find the load more button
        selectors = [
            "//rt-button[contains(@class, 'load-more-button') or @data-qa='load-more-btn']",
            "//div[contains(@class, 'load-more-container')]//rt-button",
            "//button[contains(text(), 'Load More')]",
            "//div[contains(@class, 'load-more')]//button"
        ]
        
        for selector in selectors:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                return element
            except (TimeoutException, NoSuchElementException):
                continue
        
        # If we get here, we couldn't find the button with any selector
        return None
    except Exception as e:
        print(f"Error waiting for Load More button: {e}")
        return None

def ensure_reviews_suffix(url):
    """
    Checks if the given URL ends with '/reviews' and appends it if it doesn't.
    
    Args:
        url (str): The URL to check.
        
    Returns:
        str: The URL with '/reviews' at the end.
    """
    if not url.endswith('/reviews'):
        # If the URL ends with '/' already, avoid adding a double slash
        if url.endswith('/'):
            url = url + 'reviews'
        else:
            url = url + '/reviews'
    
    return url

def scrape_reviews_with_selenium(url, max_reviews=None, min_delay=1, max_delay=2, scroll_delay=1, headless=True, max_attempts=25):
    """
    Scrape Rotten Tomatoes reviews using Selenium WebDriver
    
    Args:
        url: The URL of the Rotten Tomatoes reviews page
        max_reviews: Maximum number of reviews to collect (optional)
        min_delay: Minimum delay in seconds between clicking "Load More"
        max_delay: Maximum delay in seconds between clicking "Load More"
        scroll_delay: Delay after scrolling before attempting to click
        headless: Whether to run Chrome in headless mode
        max_attempts: Maximum number of attempts to click "Load More"
    
    Returns:
        A list of dictionaries containing the review data
    """

    global global_title

    print(f"Starting Selenium WebDriver to scrape: {url}")
    driver = setup_driver(headless)
    release_date = None

    url = ensure_reviews_suffix(url)
    
    try:
        # Navigate to the page
        print("Loading page...")
        driver.get(url)
        
        # Wait for the page to load
        # Wait for the page to load
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "review-row"))
            )
        except TimeoutException:
            print("Timed out waiting for page to load")
            return [], None
        
        release_date = extract_release_date(driver)
        if release_date:
            print(f"Movie release date: {release_date}")
        
        # Get initial page title for verification
        try:
            movie_title_element = driver.find_element(By.CLASS_NAME, "sidebar-title")
            if movie_title_element:
                movie_title = movie_title_element.text
                print(f"Scraping reviews for: {movie_title}")
                global_title = movie_title
        except NoSuchElementException:
            print("Could not find movie title, continuing anyway")
        
        # Initialize variables
        all_reviews = []
        seen_review_ids = set()
        load_more_attempts = 0
        consecutive_failures = 0
        max_consecutive_failures = 3
        last_review_count = 0
        
        # Initial page delay to ensure all content loads
        time.sleep(2)
        
        # Process visible reviews first
        process_visible_reviews(driver, all_reviews, seen_review_ids, url)
        print(f"Initially found {len(all_reviews)} reviews")
        last_review_count = len(all_reviews)
        
        # Click "Load More" button repeatedly until there are no more reviews or we reach max_reviews
        while load_more_attempts < max_attempts and (max_reviews is None or len(all_reviews) < max_reviews):
            # Scroll down to make sure the button is in view
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_delay)  # Wait a bit after scrolling
            
            # Find and click the Load More button
            load_more_button = wait_for_load_more_button(driver, timeout=10)
            
            if not load_more_button:
                print("No 'Load More' button found, trying one more scroll...")
                # Try one more scroll to make sure
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_delay * 2)
                load_more_button = wait_for_load_more_button(driver, timeout=5)
                
                if not load_more_button:
                    print("Still no 'Load More' button found. Assuming we've reached the end.")
                    break
            
            try:
                # Increment attempt counter before clicking
                load_more_attempts += 1
                print(f"Clicking 'Load More' button (attempt #{load_more_attempts})...")
                
                # Scroll to the button and click it with JavaScript
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more_button)
                time.sleep(0.5)  # Give a moment for the scroll to complete
                
                # Try clicking with JavaScript
                driver.execute_script("arguments[0].click();", load_more_button)
                
                # Wait for new content to load - look for the spinner or wait for new reviews
                try:
                    # First wait a bit for any spinner to appear
                    time.sleep(1)
                    
                    # Then wait for the page to stabilize with a minimum wait time
                    time.sleep(2)
                    
                    # Now scrape the updated page
                    old_count = len(all_reviews)
                    process_visible_reviews(driver, all_reviews, seen_review_ids, url)
                    new_count = len(all_reviews)
                    
                    # Check if we got new reviews
                    if new_count > old_count:
                        print(f"Added {new_count - old_count} new reviews. Total: {new_count}")
                        consecutive_failures = 0  # Reset failure counter on success
                        last_review_count = new_count
                    else:
                        consecutive_failures += 1
                        print(f"No new reviews found after clicking 'Load More'. Failures: {consecutive_failures}/{max_consecutive_failures}")
                        
                        # If we've had too many consecutive failures, assume we're done
                        if consecutive_failures >= max_consecutive_failures:
                            print(f"Stopping after {consecutive_failures} consecutive failures to load new reviews")
                            break
                except StaleElementReferenceException:
                    # The page was updated, try getting the reviews again
                    print("Page updated, re-collecting reviews...")
                    process_visible_reviews(driver, all_reviews, seen_review_ids, url)
                    new_count = len(all_reviews)
                    if new_count > last_review_count:
                        print(f"Added {new_count - last_review_count} new reviews. Total: {new_count}")
                        consecutive_failures = 0
                        last_review_count = new_count
                    else:
                        consecutive_failures += 1
                
                # Add a random delay between clicks to look more human-like
                delay = random.uniform(min_delay, max_delay)
                print(f"Waiting {delay:.2f} seconds before next click...")
                time.sleep(delay)
                
            except (ElementClickInterceptedException, StaleElementReferenceException) as e:
                print(f"Error clicking 'Load More' button: {e}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_consecutive_failures:
                    print(f"Stopping after {consecutive_failures} consecutive failures to click the button")
                    break
                    
                # Try to refresh the page state
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Check if we need to break due to max_reviews
            if max_reviews is not None and len(all_reviews) >= max_reviews:
                print(f"Reached maximum number of reviews ({max_reviews})")
                break
        
        # Do one final check for any reviews we might have missed
        process_visible_reviews(driver, all_reviews, seen_review_ids, url)
        
        print(f"Completed scraping. Found {len(all_reviews)} total unique reviews.")
        return all_reviews, release_date

    
    finally:
        # Always close the driver to clean up resources
        driver.quit()

def process_visible_reviews(driver, all_reviews, seen_review_ids, original_url):
    """Process all currently visible reviews on the page and add new ones to all_reviews"""
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Wait for reviews to be visible
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "review-row"))
                )
            except TimeoutException:
                print("Warning: Timed out waiting for reviews to appear")
                return
                
            # Get all review elements
            review_elements = driver.find_elements(By.CLASS_NAME, "review-row")
            
            # If we found reviews, process them
            if review_elements:
                for review_element in review_elements:
                    try:
                        review_data = extract_review_data(review_element, original_url)
                        # Create a unique ID based on multiple fields to avoid duplicates
                        review_text_snippet = review_data['Review Text'][:50] if review_data['Review Text'] else ""
                        review_id = f"{review_data['Critic']}_{review_data['Publication']}_{review_data['Date']}_{review_text_snippet}"
                        
                        if review_id not in seen_review_ids:
                            seen_review_ids.add(review_id)
                            all_reviews.append(review_data)
                    except Exception as e:
                        print(f"Error extracting review data: {e}")
                        continue
                        
                # Success, so break the retry loop
                break
            else:
                # No reviews found, retry
                print(f"No review elements found (try {retry_count+1}/{max_retries})")
                retry_count += 1
                time.sleep(1)
        except StaleElementReferenceException:
            # Page was updated during processing, retry
            print(f"Page updated while processing reviews (try {retry_count+1}/{max_retries})")
            retry_count += 1
            time.sleep(1)
        except Exception as e:
            print(f"Error in process_visible_reviews: {e}")
            retry_count += 1
            time.sleep(1)

def extract_review_data(review_element, original_url):
    """Extract all review data from a review element"""
    try:
        # Extract critic name
        try:
            critic_element = review_element.find_element(By.CLASS_NAME, "display-name")
            critic_name = critic_element.text.strip()
        except NoSuchElementException:
            critic_name = "Unknown"
        
        # Extract publication
        try:
            pub_element = review_element.find_element(By.CLASS_NAME, "publication")
            publication = pub_element.text.strip()
        except NoSuchElementException:
            publication = "Unknown"
        
        # Extract review text
        try:
            text_element = review_element.find_element(By.CLASS_NAME, "review-text")
            review_text = text_element.text.strip()
        except NoSuchElementException:
            review_text = "No text available"
        
        # Extract review score
        try:
            score_element = review_element.find_element(By.TAG_NAME, "score-icon-critics")
            score = score_element.get_attribute("sentiment").lower()
        except NoSuchElementException:
            score = "unknown"
        
        # Extract review date
        try:
            date_element = review_element.find_element(By.XPATH, ".//span[@data-qa='review-date']")
            review_date = date_element.text.strip()
        except NoSuchElementException:
            review_date = "Unknown"
        
        # Extract full review URL if available
        try:
            url_element = review_element.find_element(By.CLASS_NAME, "full-url")
            review_url = url_element.get_attribute("href")
        except NoSuchElementException:
            review_url = ""
        
        # Extract original score if available
        original_score = ""
        try:
            original_score_text = review_element.find_element(By.CLASS_NAME, "original-score-and-url")
            if original_score_text:
                text = original_score_text.text
                if "Original Score:" in text:
                    original_score = text.split("Original Score:")[1].split("|")[0].strip()
        except NoSuchElementException:
            pass
        
        # Compile review data
        review_data = {
            'Critic': critic_name,
            'Publication': publication,
            'Review Text': review_text,
            'Review Score': score,
            'Original Score': original_score,
            'Date': review_date,
            'URL': review_url,
            'Movie URL': original_url
        }
        
        return review_data
        
    except Exception as e:
        print(f"Error in extract_review_data: {e}")
        raise

def save_reviews(reviews, movie_title=None, release_date=None, output_dir="reviews"):
    """Save reviews to CSV file with proper formatting and movie name"""
    
    if not reviews:
        print("No reviews to save!")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Determine the title to use for the filename
    title_to_use = None
    
    # First check the passed movie_title parameter
    if movie_title and movie_title.strip():
        title_to_use = movie_title
        print(f"Using provided movie title: {title_to_use}")
    
    # Next check the global_title
    elif global_title and global_title != "placeholder":
        title_to_use = global_title
        print(f"Using global title: {title_to_use}")
    
    # Finally, try to extract from the first review URL
    else:
        try:
            movie_url = reviews[0].get('Movie URL', '')
            extracted_title = extract_movie_title(movie_url)
            if extracted_title:
                title_to_use = extracted_title
                print(f"Using extracted title from URL: {title_to_use}")
        except (IndexError, AttributeError):
            # If we can't extract a title, we'll use the default
            pass
    
    # Clean the title if we have one
    if title_to_use:
        clean_title = clean_filename(title_to_use)
        
        # Construct the filename with the title and optionally the release date
        if release_date:
            filename = f"{output_dir}/{clean_title}_{release_date}_{timestamp}.csv"
        else:
            filename = f"{output_dir}/{clean_title}_{timestamp}.csv"
    else:
        # Fallback to generic filename if no title could be determined
        if release_date:
            filename = f"{output_dir}/reviews_{release_date}_{timestamp}.csv"
        else:
            filename = f"{output_dir}/reviews_{timestamp}.csv"
        print("Warning: Could not determine movie title, using generic filename.")
    
    # Convert to DataFrame and save
    df = pd.DataFrame(reviews)
    
    # Check for unknown data
    unknown_counts = {
        'Critics': len(df[df['Critic'] == 'Unknown']),
        'Publications': len(df[df['Publication'] == 'Unknown']),
        'Dates': len(df[df['Date'] == 'Unknown']),
        'Scores': len(df[df['Review Score'] == 'unknown'])
    }
    
    print("\nData quality check:")
    for field, count in unknown_counts.items():
        percentage = (count / len(df)) * 100 if len(df) > 0 else 0
        print(f"- {field} unknown: {count}/{len(df)} ({percentage:.1f}%)")
    
    # Save to CSV
    df.to_csv(filename, index=False, encoding='utf-8')
    print(f"\n✓ Successfully saved {len(df)} reviews to '{filename}'")
    print(f"✓ DataFrame shape: {df.shape}")
    
    # Print sample of the data
    print("\nSample of saved data:")
    sample_columns = ['Critic', 'Publication', 'Review Score', 'Date']
    print(df[sample_columns].head(3))
    
    return True

def final_review_capture(driver, url):
    """
    Specialized function to capture the final review when stuck at 380.
    Add this to your script and call it right after scrape_reviews_with_selenium 
    if it returned exactly 380 reviews.
    """
    import time
    from selenium.webdriver.common.by import By
    
    print("\n=== ATTEMPTING SPECIALIZED FINAL REVIEW CAPTURE ===")
    
    # Force scroll to the very bottom of the page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    try:
        # Try to click the Load More button directly via JavaScript
        load_more_elements = driver.find_elements(By.XPATH, "//rt-button[contains(@class, 'load-more-button') or @data-qa='load-more-btn']")
        if load_more_elements:
            print(f"Found {len(load_more_elements)} potential Load More buttons")
            for i, element in enumerate(load_more_elements):
                try:
                    print(f"Attempting to force-click button {i+1}...")
                    driver.execute_script("arguments[0].click();", element)
                    time.sleep(3)  # Wait for content to load
                except Exception as e:
                    print(f"Error clicking button {i+1}: {e}")
        else:
            print("No Load More buttons found by primary selector")
            
            # Try alternative selectors
            alternative_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'load-more-container')]//rt-button")
            if alternative_elements:
                print(f"Found {len(alternative_elements)} buttons with alternative selector")
                for i, element in enumerate(alternative_elements):
                    try:
                        print(f"Attempting to force-click alternative button {i+1}...")
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(3)  # Wait for content to load
                    except Exception as e:
                        print(f"Error clicking alternative button {i+1}: {e}")
            else:
                print("No buttons found with alternative selector either")
                
        # Extract review info from all visible reviews
        print("Attempting to collect all visible reviews after force-clicking...")
        all_reviews = []
        review_elements = driver.find_elements(By.CLASS_NAME, "review-row")
        print(f"Found {len(review_elements)} review elements")
        
        # Get the last review (should be the missing one if we have 380 already)
        if review_elements and len(review_elements) > 380:
            final_review = review_elements[-1]
            print("Examining final review element:")
            try:
                # Extract critic name
                critic_element = final_review.find_element(By.CLASS_NAME, "display-name")
                critic_name = critic_element.text if critic_element else "Unknown"
                print(f"Final review critic: {critic_name}")
                
                # Extract text snippet
                text_element = final_review.find_element(By.CLASS_NAME, "review-text")
                text_snippet = text_element.text[:50] + "..." if text_element else "No text available"
                print(f"Final review text snippet: {text_snippet}")
                
                # Extract date
                date_element = final_review.find_element(By.XPATH, ".//span[@data-qa='review-date']")
                date = date_element.text if date_element else "Unknown"
                print(f"Final review date: {date}")
                
                print("Successfully extracted info from final review!")
                return True
            except Exception as e:
                print(f"Error extracting final review info: {e}")
        else:
            print("Could not find additional reviews beyond 380")
            
    except Exception as e:
        print(f"Error in final_review_capture: {e}")
    
    print("=== END OF SPECIALIZED FINAL REVIEW CAPTURE ===\n")
    return False
def main():
    global global_title

    parser = argparse.ArgumentParser(description='Scrape Rotten Tomatoes reviews using Selenium')
    parser.add_argument('url', help='Rotten Tomatoes URL for movie reviews (e.g., https://www.rottentomatoes.com/m/movie_name/reviews)')
    parser.add_argument('--max-reviews', type=int, default=None, help='Maximum number of reviews to collect (default: all available)')
    parser.add_argument('--min-delay', type=int, default=1, help='Minimum delay between clicks in seconds (default: 4)')
    parser.add_argument('--max-delay', type=int, default=3, help='Maximum delay between clicks in seconds (default: 8)')
    parser.add_argument('--scroll-delay', type=float, default=1, help='Delay after scrolling in seconds (default: 1)')
    parser.add_argument('--max-attempts', type=int, default=25, help='Maximum number of attempts to click "Load More" (default: 25)')
    parser.add_argument('--output', default='reviews', help='Output directory for CSV files')
    parser.add_argument('--visible', action='store_true', help='Run Chrome in visible mode (not headless)')
    
    args = parser.parse_args()
    
    # Extract movie title from URL
    movie_title = extract_movie_title(args.url)
    if movie_title:
        print(f"Scraping reviews for: {movie_title}")
        global_title = movie_title
        print(global_title)
    
    # Scrape reviews using Selenium
     # Scrape reviews using Selenium
    reviews, release_date = scrape_reviews_with_selenium(
        args.url,
        max_reviews=args.max_reviews,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        scroll_delay=args.scroll_delay,
        headless=not args.visible,
        max_attempts=args.max_attempts
    )


    # Add this to your main function right after calling scrape_reviews_with_selenium:
    # Check if we need to capture the final review
    # if len(reviews) == 380:
    #     print("Detected exactly 380 reviews - attempting to capture the final review")
    #     driver = setup_driver(headless=not args.visible)
    #     try:
    #         driver.get(args.url)
    #         time.sleep(5)  # Let the page load
    #         final_review_capture(driver, args.url)
    #         # Now try one more time to get all reviews
    #         extra_reviews = scrape_reviews_with_selenium(
    #             args.url,
    #             min_delay=1,
    #             max_delay=2,  # Use faster delays
    #             scroll_delay=0.5,
    #             headless=not args.visible,
    #             max_attempts=5  # Just a few attempts
    #         )
    #         # Add any new reviews
    #         for review in extra_reviews:
    #             if review not in reviews:
    #                 reviews.append(review)
    #     finally:
    #         driver.quit()
    
    # Save reviews
     # Save reviews with release date
    if reviews:
        save_reviews(reviews, movie_title, release_date, args.output)
        print(f"Total reviews collected: {len(reviews)}")
    else:
        print("No reviews were collected.")

if __name__ == "__main__":
    main()

