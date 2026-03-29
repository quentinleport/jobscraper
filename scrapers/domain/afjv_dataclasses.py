from dataclasses import dataclass

@dataclass
class AFJVScraperConfig:
	output_csv: str = "jobs_afjv.csv"
	limit: int | None = 100
	include_details: bool = True
	delay_seconds: float = 0.2
	timeout_seconds: int = 20


@dataclass
class AFJVJob:
	id: str
	job_url: str
	title: str = ""
	company: str = ""
	location: str = ""
	date_posted: str = ""
	job_type: str = ""
	listing_type: str = ""
	description: str = ""
	company_addresses: str = ""