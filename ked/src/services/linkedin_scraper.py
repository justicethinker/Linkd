import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


def scrape_profile(url: str) -> dict:
    """Return scraped data from a LinkedIn profile URL.

    Note: This requires a webdriver and possibly login cookies.
    For now this is a stub that opens the page, grabs the HTML, and parses
    basic information.
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    with webdriver.Chrome(options=options) as driver:
        driver.get(url)
        time.sleep(3)  # allow page to load
        html = driver.page_source

    soup = BeautifulSoup(html, "html.parser")
    # TODO: parse specific pieces such as name, headline, experience
    profile = {
        "raw_html": html,
    }
    return profile
