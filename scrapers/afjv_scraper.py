from __future__ import annotations

import csv
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

import requests
from bs4 import BeautifulSoup

from scrapers.domain.afjv_dataclasses import AFJVJob, AFJVScraperConfig
from scrapers.domain.job_spy_config import JOBSPY_COLUMNS

AFJV_BASE_URL = "https://emploi.afjv.com"
AFJV_RSS_URL = f"{AFJV_BASE_URL}/rss.xml"

_BROWSER_HEADERS = {
	"User-Agent": (
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
		"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
	),
	"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


class JobDetail(TypedDict, total=False):
	"""Fields extracted from a single AFJV job detail page."""

	id: str
	title: str
	description: str
	company: str
	location: str
	date_posted: str
	job_type: str
	company_addresses: str


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def _build_session() -> requests.Session:
	"""Return a requests session that mimics a regular browser."""
	session = requests.Session()
	session.headers.update(_BROWSER_HEADERS)
	return session


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _safe_text(value: str | None) -> str:
	"""Collapse whitespace and return a trimmed string."""
	return re.sub(r"\s+", " ", value or "").strip()


def _parse_company_and_location_from_rss_description(description: str) -> tuple[str, str]:
	"""Parse company and location from the compact RSS description sentence.

	Expected format: "<Company> recrute un(e) <title>. Poste basé à <Location>."
	"""
	text = _safe_text(description)
	company_m = re.match(r"^(.*?)\s+recrute", text, flags=re.IGNORECASE)
	location_m = re.search(r"Poste\s+bas\S*\s+(.*)$", text, flags=re.IGNORECASE)
	return (
		_safe_text(company_m.group(1)) if company_m else "",
		_safe_text(location_m.group(1)) if location_m else "",
	)


def _parse_rss_date_to_iso8601(pub_date: str | None) -> str:
	"""Convert an RSS pubDate (RFC-822) to YYYY-MM-DD, or return empty."""
	if not pub_date:
		return ""
	try:
		return datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z").date().isoformat()
	except ValueError:
		return ""


def _parse_afjv_date_to_iso8601(value: str) -> str:
	"""Extract and convert an AFJV date (DD.MM.YYYY) to YYYY-MM-DD."""
	match = re.search(r"(\d{2}\.\d{2}\.\d{4})", value)
	if not match:
		return ""
	try:
		return datetime.strptime(match.group(1), "%d.%m.%Y").date().isoformat()
	except ValueError:
		return ""


def _extract_reference_from_text(value: str) -> str:
	"""Extract the AFJV reference token (e.g. AFJV-EDEV123-45678) from text."""
	m = re.search(r"(AFJV-[A-Z0-9\-]+)", value)
	return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Detail-page field extractors
# ---------------------------------------------------------------------------

def _extract_title(soup: BeautifulSoup) -> str:
	node = soup.select_one("h1.ann_pos")
	return _safe_text(node.get_text(strip=True) if node else "")


def _extract_description(soup: BeautifulSoup) -> str:
	"""Concatenate the job description and required profile sections."""
	desc_node = soup.select_one("#job_description")
	prof_node = soup.select_one("#profile_required")
	description = _safe_text(desc_node.get_text(strip=True) if desc_node else "")
	profile = _safe_text(prof_node.get_text(strip=True) if prof_node else "")
	if not profile:
		return description
	header = f"{description}\n\n" if description else ""
	return f"{header}Profil recherché :\n{profile}"


def _extract_company_info(soup: BeautifulSoup) -> tuple[str, str]:
	"""Return (company_name, company_address) from the .ann_adr block."""
	ann_adr = soup.select_one(".ann_adr")
	if not ann_adr:
		return "", ""
	lines = [line.strip() for line in ann_adr.get_text(strip=True).splitlines() if line.strip()]
	return lines[0] if lines else "", " | ".join(lines[1:])


def _extract_location_and_contract(soup: BeautifulSoup) -> tuple[str, str]:
	"""Return (location, job_type) from the .ann_vil block."""
	location = job_type = ""
	ann_vil = soup.select_one(".ann_vil")
	if not ann_vil:
		return location, job_type

	location = _safe_text(ann_vil.get_text(strip=True))
	span = ann_vil.select_one("span.fl")
	if span:
		span_text = _safe_text(span.get_text(strip=True))
		location = _safe_text(location.replace(span_text, ""))
		if "•" in span_text:
			job_type = _safe_text(span_text.split("•")[-1])

	return location, job_type


def _extract_date_and_reference(soup: BeautifulSoup) -> tuple[str, str]:
	"""Return (date_posted, reference) from the .ann_res block."""
	ann_res = soup.select_one(".ann_res")
	if not ann_res:
		return "", ""
	text = _safe_text(ann_res.get_text(strip=True))
	return _parse_afjv_date_to_iso8601(text), _extract_reference_from_text(text)


# ---------------------------------------------------------------------------
# Public scraping functions
# ---------------------------------------------------------------------------

def fetch_rss_jobs(session: requests.Session, timeout_seconds: int) -> list[AFJVJob]:
	"""Fetch the AFJV RSS feed and return a first-pass normalized job list.

	The RSS provides title, URL, date, categories and a short description.
	Individual job pages are NOT fetched here.
	"""
	response = session.get(AFJV_RSS_URL, timeout=timeout_seconds)
	response.raise_for_status()
	root = ET.fromstring(response.text)

	jobs: list[AFJVJob] = []
	for item in root.findall("./channel/item"):
		link = _safe_text(item.findtext("link"))
		if not link:
			continue

		categories = [_safe_text(category.text) for category in item.findall("category") if _safe_text(category.text)]
		company, location = _parse_company_and_location_from_rss_description(
			_safe_text(item.findtext("description"))
		)

		jobs.append(
			AFJVJob(
				id="",
				job_url=link,
				title=_safe_text(item.findtext("title")),
				company=company,
				location=location,
				date_posted=_parse_rss_date_to_iso8601(item.findtext("pubDate")),
				job_type=categories[0] if categories else "",
				listing_type=" | ".join(categories) if categories else "",
				description=_safe_text(item.findtext("description")),
			)
		)

	return jobs


def fetch_job_detail(session: requests.Session, job_url: str, timeout_seconds: int) -> JobDetail:
	"""Fetch a single AFJV job page and return a richer field mapping.

	The returned dict is meant to override RSS values in the caller.
	Raises requests exceptions on HTTP/network failures.
	"""
	response = session.get(job_url, timeout=timeout_seconds)
	response.raise_for_status()
	soup = BeautifulSoup(response.text, "html.parser")

	company, company_address = _extract_company_info(soup)
	location, job_type = _extract_location_and_contract(soup)
	date_posted, reference = _extract_date_and_reference(soup)

	return JobDetail(
		id=reference,
		title=_extract_title(soup),
		description=_extract_description(soup),
		company=company,
		location=location,
		date_posted=date_posted,
		job_type=job_type,
		company_addresses=company_address,
	)


def _merge_detail(job: AFJVJob, detail: JobDetail) -> None:
	"""Enrich a job in-place with non-empty values from the detail page."""
	for field, value in detail.items():
		if value:
			setattr(job, field, value)


def scrape_afjv_jobs(config: AFJVScraperConfig) -> list[AFJVJob]:
	"""Run the full AFJV scraping pipeline.

	1. Fetch the RSS feed.
	2. Deduplicate by URL.
	3. Optionally enrich each job with its detail page.
	4. Apply the configured limit and return normalized jobs.
	"""
	session = _build_session()
	seen: set[str] = set()
	final_jobs: list[AFJVJob] = []

	for job in fetch_rss_jobs(session, config.timeout_seconds):
		if config.limit is not None and len(final_jobs) >= config.limit:
			break
		if job.job_url in seen:
			continue
		seen.add(job.job_url)

		if config.include_details:
			try:
				_merge_detail(job, fetch_job_detail(session, job.job_url, config.timeout_seconds))
			except requests.RequestException as exc:
				print(f"[AFJV] Could not fetch detail for {job.job_url}: {exc}")
			if config.delay_seconds > 0:
				time.sleep(config.delay_seconds)

		if not job.id:
			job.id = job.job_url.rstrip("/").split("/")[-1]
		final_jobs.append(job)

	return final_jobs


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def _to_jobspy_row(job: AFJVJob) -> dict[str, Any]:
	"""Map an AFJVJob to the JobSpy-compatible CSV column schema."""
	row: dict[str, Any] = {col: "" for col in JOBSPY_COLUMNS}
	row.update(
		id=job.id,
		site="afjv",
		job_url=job.job_url,
		job_url_direct=job.job_url,
		title=job.title,
		company=job.company,
		location=job.location,
		date_posted=job.date_posted,
		job_type=job.job_type,
		listing_type=job.listing_type,
		description=job.description,
		company_addresses=job.company_addresses,
		is_remote="teletravail" in job.location.lower(),
	)
	return row


def export_afjv_jobs_to_csv(jobs: list[AFJVJob], output_csv: str) -> Path:
	"""Write a list of AFJVJob objects to a CSV file and return the path."""
	output_path = Path(output_csv)
	with output_path.open("w", encoding="utf-8", newline="") as csv_file:
		writer = csv.DictWriter(csv_file, fieldnames=JOBSPY_COLUMNS)
		writer.writeheader()
		writer.writerows(_to_jobspy_row(job) for job in jobs)
	return output_path


def get_afjv_jobs(config: AFJVScraperConfig | None = None) -> Path:
	"""Convenience entrypoint: scrape AFJV and export results to CSV."""
	config = config or AFJVScraperConfig()
	jobs = scrape_afjv_jobs(config)
	path = export_afjv_jobs_to_csv(jobs, config.output_csv)
	print(f"[AFJV] {len(jobs)} jobs exported to {path}")
	return path
