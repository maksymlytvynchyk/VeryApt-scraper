import requests
import time
import os
import re
import json
import pandas as pd
from urllib.parse import urljoin, urlparse
from collections import Counter
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# url = "https://www.veryapt.com/ApartmentReview-a15719-next-apartments-chicago"
BUILDINGS_FILE = "buildings.csv"
PHOTOS_FILE = "photos.csv"
AMENITIES_FILE = "amenities.csv"
# response = requests.get()

def append_to_csv(df, filepath):
    file_exists = os.path.exists(filepath)
    df.to_csv(filepath, mode="a", index=False, header=not file_exists, encoding="utf-8")
def render_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.locator(".apartment-item-image").wait_for()
        page.locator(".apartment-item-image").click()
        page.locator(".apartment-item-box-photo-lane").wait_for(state="visible")
        html = page.content()
        page.locator(".apartment-item-info-tab-button").nth(2).click()
        page.locator(".apartment-item-box-amenities").wait_for(state="visible")
        amenities_html = page.content()
        browser.close()
        amenities_soup = BeautifulSoup(amenities_html, "html.parser")
        soup = BeautifulSoup(html, "html.parser")
        return soup, amenities_soup

def clean_text(text):
    if not text:
        return ""
    text = text.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', text).strip()

def find_img(url):
    photo_urls = set()
    soup, amenities_soup = render_html(url)[0], render_html(url)[1]
    for img in soup.select(".apartment-item-box-photo"):
        for attr in ("src", "data-src", "data-lazy-src"):
            value = img.get(attr)
            if value:
                photo_urls.add(value)

        for candidate in img.get("srcset", "").split(","):
            value = candidate.strip().split(" ")[0]
            if value:
                photo_urls.add(value)
    name = soup.find(class_="detail-link").text
    neighborhood = soup.select_one(".apartment-item-location a").text.split(",")[0]
    address = ", ".join([s.text for s in soup.select(".apartment-item-location span")])
    building_type = next(soup.find("div", class_="apartment-item-building-type").stripped_strings)
    management = soup.select_one(".management-link a span").text
    rating = soup.select_one(".user-rating-number").text.strip()
    review_count = soup.select_one(".apartment-item-rating span").text
    
    pricing_rows = []
    floorplan_elements = soup.select(".apartment-item-pricing-list")
    for fp in floorplan_elements:
        beds_baths = clean_text(fp.select_one(".pricing-type").text)
        price = clean_text(fp.select_one(".pricing-price").text)
        pricing_rows.append({"beds_baths": beds_baths, "starting_price": price})
    
    amenities_data = [] # List of dicts for this building
    amenity_blocks = amenities_soup.select(".apartment-item-amenity-categories li")
    print(len(amenity_blocks))
    for block in amenity_blocks:
        category = block.select_one("h4")
        if category:
            category = clean_text(category.text)
            items = [el.text for el in block.select(".apartment-item-amenity-category li")]
            for item in items:
                # item = item.replace('\xa0', ' ')
                # item = re.sub(r'\s+', ' ', item).strip()
                amenity_name = clean_text(item)
                amenities_data.append({"category": category, "name": amenity_name})
    # print(name, neighborhood, address, building_type, management, rating, review_count, pricing_rows, amenities_data, sep="\n")
    
    building_record = {
        "name": name, "url": url, "neighborhood": neighborhood, "address": address,
        "building_type": building_type, "management_company": management,
        "rating": rating, "review_count": review_count, 
        "pricing_structure": json.dumps(pricing_rows), # Embedded JSON string to keep 1 row constraint
        "amenities_list": json.dumps(amenities_data)
    }
    append_to_csv(pd.DataFrame([building_record]), BUILDINGS_FILE)
    
    if photo_urls:
        photos_records = [{"building_url": url, "photo_url": p_url} for p_url in photo_urls]
        append_to_csv(pd.DataFrame(photos_records), PHOTOS_FILE)
    return sorted(photo_urls)

def generate_amenities_master():
    if not os.path.exists(BUILDINGS_FILE):
        return
    
    df = pd.read_csv(BUILDINGS_FILE)
    global_amenities = []

    for record in df["amenities_list"]:
        try:
            amenities = json.loads(record)
            for am in amenities:
                global_amenities.append((am['category'], am['name']))
        except Exception:
            continue
        
    counts = Counter(global_amenities)
    
    master_list = []
    
    for (category, name), count in counts.items():
        master_list.append({
            "Amenity Name": name,
            "Category": category,
            "Building Count": count
        })
    
    df_amenities = pd.DataFrame(master_list)
    df_amenities.to_csv(AMENITIES_FILE, index=False, encoding="utf-8")
# print(len(find_img(url)))
if __name__ == "__main__":
    url = "https://www.veryapt.com/ApartmentReview-a15719-next-apartments-chicago"
    find_img(url)