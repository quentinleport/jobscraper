import argparse

from scrapers.afjv_scraper import AFJVScraperConfig, get_afjv_jobs
from scrapers.job_spy_scraper import get_jobs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Job scraper runner")
    parser.add_argument(
        "--source",
        choices=["afjv", "jobspy", "all"],
        default="afjv",
        help="Source a scraper (defaut: afjv)",
    )
    parser.add_argument("--output", default="jobs_afjv.csv", help="Fichier CSV AFJV de sortie")
    parser.add_argument("--limit", type=int, default=100, help="Nombre max d'offres AFJV")
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="N'effectue pas la recuperation des pages detail AFJV",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.source in {"afjv", "all"}:
        afjv_config = AFJVScraperConfig(
            output_csv=args.output,
            limit=max(args.limit, 1),
            include_details=not args.no_details,
        )
        get_afjv_jobs(afjv_config)

    if args.source in {"jobspy", "all"}:
        get_jobs()


if __name__ == "__main__":
    main()
