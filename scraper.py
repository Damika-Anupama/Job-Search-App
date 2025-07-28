import requests
from bs4 import BeautifulSoup
import re

def get_job_postings(url):
    """
    Scrapes the first page of a Hacker News "Who is Hiring?" thread for job postings.

    Args:
        url (str): URL of the HN hiring thread

    Returns:
        list: A list of dictionaries, where each dictionary represents a job
              and has 'id' and 'text' keys. Returns an empty list on failure.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    job_postings = []

    try:
        print(f"Fetching job postings from: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all top-level comments
        comments = soup.find_all('tr', class_='athing comtr')
        for comment in comments:
            # Top-level comments have an indentation width of 0
            indent_img = comment.find('img', width='0')
            if not indent_img:
                continue

            comment_id = comment.get('id')
            comment_text_div = comment.find('div', class_='commtext')

            if comment_id and comment_text_div:
                # Get clean text, stripping extra newlines
                text = comment_text_div.get_text(separator='\n', strip=True)
                # Filter out very short or deleted comments
                if text and len(text) > 50 and "[dead]" not in text:
                    job_postings.append({
                        'id': f"hn_{comment_id}", # Add a prefix to ensure uniqueness across sources later
                        'text': text
                    })

        print(f"Successfully found {len(job_postings)} top-level job postings.")
        return job_postings

    except requests.RequestException as e:
        print(f"Error: Could not fetch URL. {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        return []

if __name__ == "__main__":
    # The official "Who is Hiring?" thread for August 2025 (this is a future date, let's use a real one)
    # Using the one from your example: January 2025
    HIRING_THREAD_URL = "https://news.ycombinator.com/item?id=42575537"

    print("--- Starting Hacker News Scraper Test ---")
    jobs = get_job_postings(HIRING_THREAD_URL)

    if jobs:
        print("\n--- Scraping Complete. First 2 Jobs Found: ---")
        for i, job in enumerate(jobs[:2]):
            print(f"\n--- Job {i+1} (ID: {job['id']}) ---")
            # Print the first 250 characters of the job text
            print(job['text'][:250] + "...")
    else:
        print("\n--- Scraping Test Finished with No Results. ---")