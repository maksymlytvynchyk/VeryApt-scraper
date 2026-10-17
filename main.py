import requests
import time
import os
import pandas as pd
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

"""
https://www.upwork.com/nx/find-work/most-recent/details/~022110260925663995874?pageTitle=Job%20Details&_modalInfo=%5B%7B%22navType%22%3A%22slider%22,%22title%22%3A%22Job%20Details%22,%22modalId%22%3A%221792003426759%22%7D%5D
Summary
I need a one-time scrape of apartment building listings from VeryApt.com for downtown Chicago, delivered as clean CSV files. The work must be done from your own infrastructure.

Scope
Source: VeryApt Chicago region pages, starting points:
veryapt.com/Apartments-L657-chicago-near-northside
veryapt.com/Apartments-L562-chicago-the-loop
veryapt.com/Apartments-L662-chicago-near-south-side
veryapt.com/Apartments-L661-chicago-near-west-side
veryapt.com/Apartments-L659-chicago-west-town
veryapt.com/Apartments-L563-chicago-lincoln-park
Plus any other region pages needed to cover the boundary.

Boundary: only buildings between Armitage (2000 N) and 26th St (2600 S), and between the Lake and Ashland (1600 W).
Includes Gold Coast, Old Town, River North, Streeterville, Lakeshore East, Loop, West Loop, Fulton Market, South Loop and River West.
Regions overlap, so dedupe by building URL.

Estimated volume: about 1,200 raw listings, likely 500–800 unique buildings after filtering.

Fields per building
Name, URL, VeryApt neighborhood label, street address,
Building type (high-rise apartment, condo, etc.)
Management company
User rating and review count
Every pricing row (unit type, beds/baths, starting price)
Full amenity list with VeryApt's categories (Kitchen, Laundry, Pet Terms, etc.)
Photo URLs, all available per building. Photos load via JavaScript, so a headless browser (Playwright, Puppeteer or Selenium) is likely required.
Nice to have:  year built, unit count and lat/long, if available on building pages.

Deliverables
buildings.csv: one row per building with all the fields above.
amenities.csv: master list of every amenity, with its category and the count of buildings that have it.
photos.csv: building URL and photo URL, one row per photo. The downloaded images in folders by building.

Requirements
Proven experience scraping JavaScript-rendered sites. Please share examples.
Polite request pacing with no aggressive hammering of the site.

Spot-check accuracy against at least 10 live listings before delivery.

To apply, include:
Your approach and tools
Estimated turnaround
Fixed price quote
One similar project you've completed
Budget: [fixed price, your range]
Timeline: [e.g., 5–7 days]
"""

urls = [
    # "https://www.veryapt.com/Apartments-L657-chicago-near-northside",
    "https://www.veryapt.com/Apartments-L657-chicago-near-northside?page=",
    "https://www.veryapt.com/Apartments-L562-chicago-the-loop",
    "https://www.veryapt.com/Apartments-L662-chicago-near-south-side",
    "https://www.veryapt.com/Apartments-L661-chicago-near-west-side",
    "https://www.veryapt.com/Apartments-L659-chicago-west-town",
    "https://www.veryapt.com/Apartments-L563-chicago-lincoln-park"
]
# page = requests.get(url)
# for index, url in enumerate(urls, start=1):
#     # Dynamically create a unique file name for each link
#     file_name = f"page_{index}.html"
    
#     try:
#         # Fetch the webpage content
#         response = requests.get(url, timeout=10)
#         response.raise_for_status()
        
#         # Write the HTML content to its respective file
#         with open(file_name, "w", encoding="utf-8") as file:
#             file.write(response.text)
            
#         print(f"Successfully saved {url} -> {file_name}")
        
#     except requests.exceptions.RequestException as e:
#         print(f"Failed to download {url}: {e}")

"""

"""
output_file = "scraped_data.csv"
base_urls = []
def building_links(html, base_url):
    all_data = []
    page = 1
    results = set()
    while True:
        params = {"page": page}
        current_page = urls[0] + str(page)
        response = requests.get(current_page, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        last_page = f"https://www.veryapt.com{soup.select_one(".ajax-listing-link-replace:contains(Last)").get('href')}"
        # all_data.append(soup)
        for card in soup.select("h3.whitney"):
            print(card)
            link = card.select_one("a[href]")
            if not link:
                continue

            url = urljoin(base_url, link["href"])
            # if urlparse(url).netloc.endswith("veryapt.com"):
            results.add(url)
        if current_page == last_page:
            print("Reached the finall page")
            break
        page += 1
        time.sleep(1)
        
    # for p in all_data:
        

    return results

def main():
    pass
print(building_links("page_1.html", base_urls))
# with open("page_1.html") as fp:
#     soup = BeautifulSoup(fp, "html.parser")
# print(soup.find_all(class_="whitney"))
