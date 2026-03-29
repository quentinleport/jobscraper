# jobScraper

Job offer scrapers for:
- `JobSpy` (LinkedIn, Google Jobs, Indeed)
- `AFJV` (https://emploi.afjv.com)

## Installation

With `uv`:

```bash
uv sync
```

Or with `pip`:

```bash
pip install -e .
```

## Quick start

Run AFJV (default):

```bash
python main.py
```

Run AFJV with a limit and without detail pages:

```bash
python main.py --source afjv --limit 50 --no-details --output jobs_afjv.csv
```

Run JobSpy:

```bash
python main.py --source jobspy
```

Run both:

```bash
python main.py --source all
```

Quick AFJV test runner:

```bash
python run_afjv.py
```

## Outputs

- `jobs_afjv.csv` for AFJV
- files under `job_spy_scraper_results/` for JobSpy

The AFJV CSV is aligned with the JobSpy column schema to make downstream merging and processing straightforward.
