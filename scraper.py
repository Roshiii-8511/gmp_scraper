import os
import re
import json
from datetime import datetime
from pathlib import Path

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
OUTPUT_FILE = Path("data/gmp.json")

def fetch_gmp_once() -> dict:
    """Open the page with headless Chrome, scrape IPO → GMP, return dict."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    chrome_path = os.getenv("CHROME_PATH")
    if chrome_path:
        options.binary_location = chrome_path

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        driver.get(URL)

        # wait for table rows to appear
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '//table[contains(@class,"table-bordered")]/tbody/tr')
            )
        )

        rows = driver.find_elements(By.XPATH, '//table[contains(@class,"table-bordered")]/tbody/tr')
        data = {}

        for row in rows:
            try:
                ipo_name_raw = row.find_element(By.XPATH, "./td[1]").text.strip()
                gmp_text = row.find_element(By.XPATH, "./td[2]").text.strip()

                clean_name = ipo_name_raw.split(" IPO")[0].strip()

                # Extract only ₹ value or "--"
                m = re.search(r"(₹[\d.]+|₹--|--)", gmp_text)
                gmp_value = m.group(0) if m else "N/A"

                if clean_name:
                    data[clean_name] = gmp_value
            except Exception:
                continue

        return {
            "last_updated_ist": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "source": URL,
            "entries": data
        }

    finally:
        if driver:
            driver.quit()

def main():
    result = fetch_gmp_once()

    # Ensure data/ exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ Wrote {len(result.get('entries', {}))} IPOs to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
