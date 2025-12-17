import os
import re
import time
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_URL = "https://ww2db.com"
SAVE_DIR = "ww2db_ships/submarines"

DELAY = 0.8
os.makedirs(SAVE_DIR, exist_ok=True)

# Regex to find /images/ship_<anything>1.jpg (case-insensitive)
SHIP_REGEX = re.compile(r'/?images/ship_[A-Za-z0-9_\-\(\)\[\]\.]+?1\.jpg', re.I)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; scraper/1.0; +https://example.com)"
}

def find_ship_image_url(page_url, html_text, soup):
    # 1) Look in <img> tags, checking multiple attributes
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-original", "data-lazy", "data-srcset", "srcset"):
            val = img.get(attr)
            if not val:
                continue
            # if srcset, take first url token before whitespace/commas
            if attr == "srcset":
                val = val.split(",")[0].strip().split()[0]
            if SHIP_REGEX.search(val):
                return urljoin(BASE_URL, val)

    # 2) Look for og:image meta tag
    meta_og = soup.find("meta", property="og:image")
    if meta_og and meta_og.get("content") and SHIP_REGEX.search(meta_og.get("content")):
        return urljoin(BASE_URL, meta_og.get("content"))

    # 3) Search raw HTML with regex (catches inline JS, attributes, etc.)
    m = SHIP_REGEX.search(html_text)
    if m:
        candidate = m.group(0)
        # make sure it becomes an absolute URL
        return urljoin(BASE_URL, candidate)

    # nothing found
    return None

def download_url(url, dest_folder, filename=None):
    os.makedirs(dest_folder, exist_ok=True)
    filename = filename or url.split("/")[-1]
    filepath = os.path.join(dest_folder, filename)
    if os.path.exists(filepath):
        print("Already exists:", filepath)
        return filepath

    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
    except Exception as e:
        print("Download failed:", e)
        return None

    with open(filepath, "wb") as f:
        f.write(r.content)
    print("Downloaded:", filepath)
    return filepath

def download_main_ship_image(page_url, ship_name):
    print(f"\nScraping: {ship_name} -> {page_url}")

    r = requests.get(page_url, headers=HEADERS, timeout=12)
    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    img_url = find_ship_image_url(page_url, html, soup)
    if not img_url:
        print("No ship image found.")
        return

    # All files go to the main folder
    os.makedirs(SAVE_DIR, exist_ok=True)

    # Optional: name the file after the ship
    safe_name = ship_name.replace(" ", "_")
    filename = f"{safe_name}.jpg"

    download_url(img_url, SAVE_DIR, filename)
    time.sleep(DELAY)

def get_all_ships(ship_url):
    ALL_SHIPS_URL = ship_url

    print("Fetching ship list...")
    r = requests.get(ALL_SHIPS_URL, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # strict match: actual ship pages only
        if "ship_id=" not in href:
            continue

        ship_page = urljoin(BASE_URL, href)

        # get ship name from link text OR fallback to ID
        ship_name = a.text.strip()
        if not ship_name:
            m = re.search(r"ship_id=(\d+)", href)
            ship_name = f"ship_{m.group(1)}" if m else "unknown_ship"

        download_main_ship_image(ship_page, ship_name)
        time.sleep(DELAY)


# Example usage:
# download_main_ship_image("https://ww2db.com/ship_spec.php?ship_id=B795", "Alabama")

get_all_ships("https://ww2db.com/ship.php?list=S")
