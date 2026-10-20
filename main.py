import requests
import time
import os
import re
import json
import pandas as pd
from urllib.parse import urljoin
from collections import Counter
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError


BUILDINGS_FILE = "buildings.csv"
PHOTOS_FILE = "photos.csv"
AMENITIES_FILE = "amenities.csv"


def append_to_csv(df, filepath):
    file_exists = os.path.exists(filepath)
    df.to_csv(filepath, mode="a", index=False, sep=";",
              header=not file_exists, encoding="utf-8")


def render_html(urls):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for url in urls:
            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded")
                try:
                    page.locator(
                        ".apartment-item-info-tab-button").filter(has_text="Photos").wait_for()
                    page.locator(
                        ".apartment-item-info-tab-button").filter(has_text="Photos").click()
                    page.locator(
                        ".apartment-item-box-photo-lane").wait_for(state="visible")
                except TimeoutError:
                    print("Photos not found")
                    pass
                html = page.content()
                try:
                    page.locator(
                        ".apartment-item-info-tab-button").filter(has_text="Amenities").click()
                    page.locator(
                        ".apartment-item-box-amenities").wait_for(state="visible")
                except TimeoutError:
                    print("Amenities not found")
                    pass
                amenities_html = page.content()
                amenities_soup = BeautifulSoup(amenities_html, "html.parser")
                soup = BeautifulSoup(html, "html.parser")
                scrape_building_page(soup, amenities_soup, url)
            finally:
                page.close()
        browser.close()
        generate_amenities_master()
    return


def clean_text(text):
    if not text:
        return ""
    text = text.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def scrape_building_page(soup, amenities_soup, url):
    photo_urls = set()
    for img in soup.select(".apartment-item-box-photo"):
        for attr in ("src", "data-src", "data-lazy-src"):
            value = img.get(attr)
            if value:
                photo_urls.add(value)

        for candidate in img.get("srcset", "").split(","):
            value = candidate.strip().split(" ")[0]
            if value:
                photo_urls.add(value)
    name = soup.find(
        class_="detail-link").text if soup.find(class_="detail-link") else "N/A"
    neighborhood = soup.select_one(".apartment-item-location a").text.split(
        ",")[0] if soup.select_one(".apartment-item-location a") else "N/A"
    address = ", ".join([s.text for s in soup.select(".apartment-item-location span")]
                        ) if soup.select(".apartment-item-location span") else "N/A"
    building_type = next(soup.find("div", class_="apartment-item-building-type").stripped_strings) if soup.find(
        "div", class_="apartment-item-building-type") else "N/A"
    management = soup.select_one(
        ".management-link a span").text if soup.select_one('.management-link a span') else "N/A"
    rating = soup.select_one(
        ".user-rating-number").text.strip() if soup.select_one(".user-rating-number") else "N/A"
    review_count = soup.select_one(
        ".apartment-item-rating span").text if soup.select_one(".apartment-item-rating span") else "N/A"

    pricing_rows = []
    floorplan_elements = soup.select(".apartment-item-pricing-list")
    for fp in floorplan_elements:
        beds_baths = clean_text(fp.select_one(
            ".pricing-type").text) if fp.select_one(".pricing-type") else "N/A"
        price = clean_text(fp.select_one(
            ".pricing-price").text) if fp.select_one(".pricing-price") else "N/A"
        pricing_rows.append(
            {"beds_baths": beds_baths, "starting_price": price})

    amenities_data = []
    amenity_blocks = amenities_soup.select(
        ".apartment-item-amenity-categories li")
    for block in amenity_blocks:
        category = block.select_one("h4")
        if category:
            category = clean_text(category.text) if category else "N/A"
            items = [el.text for el in block.select(
                ".apartment-item-amenity-category li")]
            for item in items:
                amenity_name = clean_text(item)
                amenities_data.append(
                    {"category": category, "name": amenity_name})

    building_record = {
        "name": name, "url": url, "neighborhood": neighborhood, "address": address,
        "building_type": building_type, "management_company": management,
        "rating": rating, "review_count": review_count,
        # Embedded JSON string to keep 1 row constraint
        "pricing_structure": json.dumps(pricing_rows),
        "amenities_list": json.dumps(amenities_data)
    }
    append_to_csv(pd.DataFrame([building_record]), BUILDINGS_FILE)

    if photo_urls:
        photos_records = [{"building_url": url, "photo_url": p_url}
                          for p_url in photo_urls]
        append_to_csv(pd.DataFrame(photos_records), PHOTOS_FILE)
    return sorted(photo_urls)


def generate_amenities_master():
    if not os.path.exists(BUILDINGS_FILE):
        return

    df = pd.read_csv(BUILDINGS_FILE, sep=";", on_bad_lines="skip")
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
    df_amenities.to_csv(AMENITIES_FILE, sep=";", index=False, encoding="utf-8")


def building_links(urls):
    results = set()
    for url in urls:
        page = 1
        while True:
            current_page = urljoin(url, f"?page={page}")
            print(current_page)
            response = requests.get(current_page, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            last_page = f"https://www.veryapt.com{soup.select_one(".ajax-listing-link-replace:-soup-contains(Last)").get('href')}"
            print(last_page)
            for card in soup.select("h3.whitney"):
                link = card.select_one("a[href]")
                if not link:
                    continue

                card_url = urljoin("https://www.veryapt.com", link["href"])
                results.add(card_url)
            if current_page == last_page:
                print("Reached the finall page")
                break
            page += 1
            time.sleep(1)

    render_html(results)


def main():
    urls = [
        "https://www.veryapt.com/Apartments-L657-chicago-near-northside",
        "https://www.veryapt.com/Apartments-L562-chicago-the-loop",
        "https://www.veryapt.com/Apartments-L662-chicago-near-south-side",
        "https://www.veryapt.com/Apartments-L661-chicago-near-west-side",
        "https://www.veryapt.com/Apartments-L659-chicago-west-town",
        "https://www.veryapt.com/Apartments-L563-chicago-lincoln-park"
    ]
    print(building_links(urls))


if __name__ == "__main__":
    main()
