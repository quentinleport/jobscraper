import csv

from jobspy import scrape_jobs

from dataclasses import dataclass


@dataclass
class ScraperConfig:
    filename: str
    search_term: str
    google_search_term: str
    result_wanted: int | None = 300
    hours_old: int | None = None


def scrape(scraper_conf: ScraperConfig) -> None:
    jobs = scrape_jobs(
        site_name=["linkedin", "google", "indeed"],
        search_term=scraper_conf.search_term,
        google_search_term=scraper_conf.google_search_term,
        location="Paris, FR",
        results_wanted=scraper_conf.result_wanted,
        country_indeed='France',
        linkedin_fetch_description=True,  # gets more info such as description, direct job url (slower)
        county_indeed='France',
        hours_old=scraper_conf.hours_old
        # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
    )

    jobs.to_csv(
        f'./job_spy_scraper_results/{scraper_conf.filename}',
        quoting=csv.QUOTE_NONNUMERIC,
        escapechar="\\",
        index=False,
        encoding='utf-8'
    )


def get_software_dev_jobs():
    scraper_conf = ScraperConfig(
        filename="software_dev_jobs.csv",
        search_term="software engineer",
        google_search_term="software engineer jobs in Paris",
        result_wanted=300,
        hours_old=24 * 7
    )
    scrape(scraper_conf)


def get_game_dev_jobs():
    scraper_conf = ScraperConfig(
        filename="game_dev_jobs.csv",
        search_term="game developer",
        google_search_term="game developer jobs in Paris",
        result_wanted=300,
        hours_old=None
    )
    scrape(scraper_conf)


def get_technical_artists_jobs():
    scraper_conf = ScraperConfig(
        filename="technical_artist_jobs.csv",
        search_term="technical artist",
        google_search_term="technical artist jobs in Paris",
        result_wanted=150,
        hours_old=None
    )
    scrape(scraper_conf)


def get_jobs():
    get_technical_artists_jobs()
    get_game_dev_jobs()
    get_software_dev_jobs()
