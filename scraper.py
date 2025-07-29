import requests
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
import hashlib
from datetime import datetime

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

def scrape_remoteok_api(url):
    """
    Scrapes job postings from Remote OK API.
    
    Args:
        url (str): Remote OK API URL (e.g., https://remoteok.io/api)
    
    Returns:
        list: A list of dictionaries, where each dictionary represents a job
              and has 'id' and 'text' keys. Returns an empty list on failure.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    job_postings = []
    
    try:
        print(f"Fetching Remote OK jobs from: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        jobs_data = response.json()
        
        # Skip the first item as it's metadata
        if jobs_data and len(jobs_data) > 1:
            jobs_data = jobs_data[1:]
        
        for job in jobs_data:
            if not isinstance(job, dict):
                continue
                
            # Extract job information
            job_id = job.get('id', '')
            position = job.get('position', '')
            company = job.get('company', '')
            description = job.get('description', '')
            location = job.get('location', 'Remote')
            tags = job.get('tags', [])
            
            # Skip if essential fields are missing
            if not job_id or not position:
                continue
                
            # Create comprehensive job text
            job_text_parts = []
            
            if position:
                job_text_parts.append(f"Position: {position}")
            if company:
                job_text_parts.append(f"Company: {company}")
            if location:
                job_text_parts.append(f"Location: {location}")
            if tags:
                job_text_parts.append(f"Skills: {', '.join(tags)}")
            if description:
                # Clean HTML tags from description
                if '<' in description and '>' in description:
                    soup = BeautifulSoup(description, 'html.parser')
                    clean_description = soup.get_text(separator='\n', strip=True)
                else:
                    clean_description = description
                job_text_parts.append(f"Description: {clean_description}")
            
            job_text = '\n\n'.join(job_text_parts)
            
            # Filter out very short postings
            if len(job_text) > 50:
                job_postings.append({
                    'id': f"ro_{job_id}",  # Add remoteok prefix
                    'text': job_text
                })
        
        print(f"Successfully found {len(job_postings)} Remote OK job postings.")
        return job_postings
        
    except ValueError as e:
        print(f"Error parsing JSON from Remote OK API: {e}")
        return []
    except requests.RequestException as e:
        print(f"Error fetching Remote OK jobs: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during Remote OK scraping: {e}")
        return []

def scrape_arbeitnow_api(url):
    """
    Scrapes job postings from Arbeit Now API (free, no auth required).
    
    Args:
        url (str): Arbeit Now API URL (e.g., https://www.arbeitnow.com/api/job-board-api)
    
    Returns:
        list: A list of dictionaries, where each dictionary represents a job
              and has 'id' and 'text' keys. Returns an empty list on failure.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    job_postings = []
    
    try:
        print(f"Fetching Arbeit Now jobs from: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        jobs_data = response.json()
        
        # Extract jobs from the API response
        jobs_list = jobs_data.get('data', [])
        
        for job in jobs_list:
            if not isinstance(job, dict):
                continue
                
            # Extract job information
            job_id = job.get('slug', '')
            title = job.get('title', '')
            company = job.get('company_name', '')
            location = job.get('location', '')
            job_types = job.get('job_types', [])
            tags = job.get('tags', [])
            description = job.get('description', '')
            
            # Skip if essential fields are missing
            if not job_id or not title:
                continue
                
            # Create comprehensive job text
            job_text_parts = []
            
            if title:
                job_text_parts.append(f"Position: {title}")
            if company:
                job_text_parts.append(f"Company: {company}")
            if location:
                job_text_parts.append(f"Location: {location}")
            if job_types:
                job_text_parts.append(f"Type: {', '.join(job_types)}")
            if tags:
                job_text_parts.append(f"Skills: {', '.join(tags)}")
            if description:
                # Clean HTML tags from description
                if '<' in description and '>' in description:
                    soup = BeautifulSoup(description, 'html.parser')
                    clean_description = soup.get_text(separator='\n', strip=True)
                else:
                    clean_description = description
                job_text_parts.append(f"Description: {clean_description}")
            
            job_text = '\n\n'.join(job_text_parts)
            
            # Filter out very short postings
            if len(job_text) > 50:
                job_postings.append({
                    'id': f"an_{job_id}",  # Add arbeit now prefix
                    'text': job_text
                })
        
        print(f"Successfully found {len(job_postings)} Arbeit Now job postings.")
        return job_postings
        
    except ValueError as e:
        print(f"Error parsing JSON from Arbeit Now API: {e}")
        return []
    except requests.RequestException as e:
        print(f"Error fetching Arbeit Now jobs: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during Arbeit Now scraping: {e}")
        return []

def scrape_themusedev_api(url):
    """
    Scrapes job postings from The Muse API (free tier available).
    
    Args:
        url (str): The Muse API URL (e.g., https://www.themuse.com/api/public/jobs?category=Software%20Engineer)
    
    Returns:
        list: A list of dictionaries, where each dictionary represents a job
              and has 'id' and 'text' keys. Returns an empty list on failure.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    job_postings = []
    
    try:
        print(f"Fetching The Muse jobs from: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        jobs_data = response.json()
        
        # Extract jobs from the API response
        jobs_list = jobs_data.get('results', [])
        
        for job in jobs_list:
            if not isinstance(job, dict):
                continue
                
            # Extract job information
            job_id = str(job.get('id', ''))
            title = job.get('name', '')
            company = job.get('company', {}).get('name', '')
            locations = job.get('locations', [])
            categories = job.get('categories', [])
            levels = job.get('levels', [])
            contents = job.get('contents', '')
            
            # Skip if essential fields are missing
            if not job_id or not title:
                continue
                
            # Create comprehensive job text
            job_text_parts = []
            
            if title:
                job_text_parts.append(f"Position: {title}")
            if company:
                job_text_parts.append(f"Company: {company}")
            if locations:
                location_names = [loc.get('name', '') for loc in locations if loc.get('name')]
                if location_names:
                    job_text_parts.append(f"Location: {', '.join(location_names)}")
            if categories:
                category_names = [cat.get('name', '') for cat in categories if cat.get('name')]
                if category_names:
                    job_text_parts.append(f"Categories: {', '.join(category_names)}")
            if levels:
                level_names = [lvl.get('name', '') for lvl in levels if lvl.get('name')]
                if level_names:
                    job_text_parts.append(f"Levels: {', '.join(level_names)}")
            if contents:
                # Clean HTML tags from contents
                if '<' in contents and '>' in contents:
                    soup = BeautifulSoup(contents, 'html.parser')
                    clean_contents = soup.get_text(separator='\n', strip=True)
                else:
                    clean_contents = contents
                job_text_parts.append(f"Description: {clean_contents}")
            
            job_text = '\n\n'.join(job_text_parts)
            
            # Filter out very short postings
            if len(job_text) > 50:
                job_postings.append({
                    'id': f"tm_{job_id}",  # Add the muse prefix
                    'text': job_text
                })
        
        print(f"Successfully found {len(job_postings)} The Muse job postings.")
        return job_postings
        
    except ValueError as e:
        print(f"Error parsing JSON from The Muse API: {e}")
        return []
    except requests.RequestException as e:
        print(f"Error fetching The Muse jobs: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during The Muse scraping: {e}")
        return []

def generate_job_hash(job_text):
    """
    Generate a hash for job content to identify duplicates.
    
    Args:
        job_text (str): The job posting text
        
    Returns:
        str: SHA256 hash of normalized job text
    """
    # Normalize text for better deduplication
    normalized_text = re.sub(r'\s+', ' ', job_text.lower().strip())
    normalized_text = re.sub(r'[^\w\s]', '', normalized_text)  # Remove special characters
    return hashlib.sha256(normalized_text.encode()).hexdigest()

def deduplicate_jobs(all_jobs):
    """
    Remove duplicate jobs based on content similarity.
    
    Args:
        all_jobs (list): List of job dictionaries with 'id' and 'text' keys
        
    Returns:
        list: Deduplicated list of jobs
    """
    seen_hashes = set()
    deduplicated_jobs = []
    duplicates_removed = 0
    
    for job in all_jobs:
        job_hash = generate_job_hash(job['text'])
        
        if job_hash not in seen_hashes:
            seen_hashes.add(job_hash)
            deduplicated_jobs.append(job)
        else:
            duplicates_removed += 1
    
    print(f"Deduplication complete: Removed {duplicates_removed} duplicates, kept {len(deduplicated_jobs)} unique jobs")
    return deduplicated_jobs

def filter_jobs(jobs, keywords=None, locations=None, exclude_keywords=None):
    """
    Filter jobs based on keywords, locations, and exclusion criteria.
    
    Args:
        jobs (list): List of job dictionaries
        keywords (list): Keywords that must be present (OR logic)
        locations (list): Locations to include (OR logic)
        exclude_keywords (list): Keywords to exclude (ANY present = exclude)
        
    Returns:
        list: Filtered list of jobs
    """
    if not any([keywords, locations, exclude_keywords]):
        return jobs
    
    filtered_jobs = []
    
    for job in jobs:
        job_text_lower = job['text'].lower()
        should_include = True
        
        # Exclude jobs with blacklisted keywords
        if exclude_keywords:
            for exclude_keyword in exclude_keywords:
                if exclude_keyword.lower() in job_text_lower:
                    should_include = False
                    break
        
        if not should_include:
            continue
        
        # Check keyword requirements
        if keywords:
            keyword_found = False
            for keyword in keywords:
                if keyword.lower() in job_text_lower:
                    keyword_found = True
                    break
            if not keyword_found:
                continue
        
        # Check location requirements
        if locations:
            location_found = False
            for location in locations:
                if location.lower() in job_text_lower:
                    location_found = True
                    break
            if not location_found:
                continue
        
        filtered_jobs.append(job)
    
    original_count = len(jobs)
    filtered_count = len(filtered_jobs)
    print(f"Filtering complete: {filtered_count}/{original_count} jobs match criteria")
    
    return filtered_jobs

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