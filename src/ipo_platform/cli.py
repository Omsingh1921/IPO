"""
Operational CLI for Indian IPO Platform.
Provides command-line commands for ingestion, querying, daily briefing generation,
database migration, and backtesting simulation.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import List, Optional

from ipo_platform.db.session import DEFAULT_DATABASE_URL, get_engine, init_db
from ipo_platform.models.enums import IPOStatusEnum
from ipo_platform.services.backtest_service import IPOBacktestService
from ipo_platform.services.briefing_service import DailyBriefingService
from ipo_platform.services.ingestion_service import IPOIngestionService
from ipo_platform.services.query_service import IPOQueryService

logger = logging.getLogger(__name__)


def run_ingest(args: argparse.Namespace) -> int:
    """
    Executes 'ingest' command to parse and insert a MasterIPORecord JSON file.
    """
    if not args.file:
        sys.stderr.write("Error: --file argument is required for ingestion.\n")
        return 2

    if not os.path.isfile(args.file):
        sys.stderr.write(f"Error: Specified file does not exist: {args.file}\n")
        return 2

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as err:
        sys.stderr.write(f"Error: Invalid JSON syntax in file '{args.file}': {err}\n")
        return 2
    except Exception as err:
        sys.stderr.write(f"Error reading file '{args.file}': {err}\n")
        return 2

    try:
        engine = get_engine(args.db_url)
        ingestion_service = IPOIngestionService(engine)
        record = ingestion_service.ingest_json_dict(data)
        sys.stdout.write(f"Successfully ingested IPO: {record.ipo_entity.company_name} ({record.ipo_entity.ipo_id})\n")
        return 0
    except Exception as err:
        sys.stderr.write(f"Database/Ingestion Error: {err}\n")
        return 1


def run_list(args: argparse.Namespace) -> int:
    """
    Executes 'list' command to filter and display active offerings by status.
    """
    valid_statuses = [s.value for s in IPOStatusEnum]
    status_filter: Optional[str] = None

    if args.status:
        # Match case-insensitively or exactly
        matched = next((s for s in valid_statuses if s.lower() == args.status.lower()), None)
        if not matched:
            sys.stderr.write(
                f"Error: Invalid IPO status '{args.status}'. Allowed statuses: {', '.join(valid_statuses)}\n"
            )
            return 2
        status_filter = matched

    try:
        engine = get_engine(args.db_url)
        query_service = IPOQueryService(engine)

        if status_filter:
            records = query_service.list_ipos_by_status(status_filter, skip=args.skip, limit=args.limit)
            header = f"=== IPOs with Status: {status_filter} ({len(records)} found) ==="
        else:
            records = query_service.list_active_ipos(skip=args.skip, limit=args.limit)
            header = f"=== All Active IPOs ({len(records)} found) ==="

        sys.stdout.write(f"{header}\n")
        if not records:
            sys.stdout.write("No matching IPO records found.\n")
            return 0

        sys.stdout.write(f"{'IPO ID':<20} | {'Company Name':<35} | {'Status':<16} | {'Price Band':<15}\n")
        sys.stdout.write("-" * 92 + "\n")
        for rec in records:
            cname = rec.ipo_entity.company_name[:33]
            st = rec.ipo_status.status.value if hasattr(rec.ipo_status.status, "value") else str(rec.ipo_status.status)
            pb_low = rec.issue_structure.price_band_low.value
            pb_high = rec.issue_structure.price_band_high.value
            if pb_low != "Not available" and pb_high != "Not available":
                pb_str = f"₹{pb_low:.0f}-₹{pb_high:.0f}"
            else:
                pb_str = "N/A"
            sys.stdout.write(f"{rec.ipo_entity.ipo_id:<20} | {cname:<35} | {st:<16} | {pb_str:<15}\n")
        return 0
    except Exception as err:
        sys.stderr.write(f"Database Query Error: {err}\n")
        return 1


def run_briefing(args: argparse.Namespace) -> int:
    """
    Executes 'briefing' command to generate and save daily market intelligence reports.
    """
    target_date: Optional[str] = None
    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
            target_date = args.date
        except ValueError:
            sys.stderr.write(f"Error: Invalid date format '{args.date}'. Expected YYYY-MM-DD.\n")
            return 2

    try:
        engine = get_engine(args.db_url)
        reports_dir = args.output_dir or "reports/daily"
        briefing_service = DailyBriefingService(engine, reports_dir=reports_dir)
        report_text = briefing_service.generate_daily_briefing(target_date=target_date)

        effective_date = target_date or datetime.now().strftime("%Y-%m-%d")
        report_file = os.path.join(reports_dir, f"briefing_{effective_date}.md")
        sys.stdout.write(f"Daily Briefing Report generated successfully: {report_file}\n")
        if args.print:
            sys.stdout.write("\n" + report_text + "\n")

        # Optional notification dispatch
        if getattr(args, "notify", None):
            from ipo_platform.notifications import NotificationService
            channels = [ch.strip() for ch in args.notify.split(",") if ch.strip()]
            notif_service = NotificationService()
            results = notif_service.send_daily_briefing(
                briefing_markdown=report_text,
                target_date=effective_date,
                channels=channels,
                dry_run=getattr(args, "dry_run", False),
            )
            for res in results:
                status_str = "SUCCESS" if res.success else "FAILED"
                sys.stdout.write(f"Notification [{res.channel.value.upper()}]: {status_str} - {res.message}\n")

        return 0
    except Exception as err:
        sys.stderr.write(f"Briefing Generation Error: {err}\n")
        return 1


def run_migrate(args: argparse.Namespace) -> int:
    """
    Executes 'migrate' command to apply database schema upgrades via Alembic or Base metadata.
    """
    try:
        db_url = args.db_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        # Attempt alembic migration first if alembic.ini is present
        alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
        if os.path.isfile(alembic_ini_path):
            try:
                from alembic import command
                from alembic.config import Config

                alembic_cfg = Config(alembic_ini_path)
                alembic_cfg.set_main_option("sqlalchemy.url", db_url)
                command.upgrade(alembic_cfg, "head")
                sys.stdout.write("Alembic schema migration completed successfully (head).\n")
                return 0
            except Exception as alembic_err:
                logger.warning("Alembic upgrade encountered an issue: %s. Falling back to init_db.", alembic_err)

        # Fallback to init_db for in-memory or metadata creation
        engine = get_engine(db_url)
        init_db(engine)
        sys.stdout.write("Database schema synchronized successfully via metadata.\n")
        return 0
    except Exception as err:
        sys.stderr.write(f"Database Migration Error: {err}\n")
        return 1


def run_backtest(args: argparse.Namespace) -> int:
    """
    Executes 'backtest' command to run longitudinal outcome simulation across historical IPOs.
    """
    try:
        engine = get_engine(args.db_url)
        backtest_service = IPOBacktestService(engine)
        ipo_ids = args.ipo_ids.split(",") if args.ipo_ids else None
        results = backtest_service.run_backtest_simulation(ipo_ids=ipo_ids)

        sys.stdout.write("=== Backtest Simulation Summary ===\n")
        total_tested = results.get("total_ipos", 0)
        overall_metrics = results.get("overall_metrics", {})
        sys.stdout.write(f"Total IPOs Analyzed: {total_tested}\n")
        for metric, val in overall_metrics.items():
            sys.stdout.write(f"- {metric}: {val}\n")

        if args.json:
            sys.stdout.write("\n" + json.dumps(results, indent=2, default=str) + "\n")
        return 0
    except Exception as err:
        sys.stderr.write(f"Backtest Execution Error: {err}\n")
        return 1


def run_sync_sources(args: argparse.Namespace) -> int:
    """
    Executes 'sync-sources' command to synchronize live offerings from upstream exchange and market feeds.
    """
    from ipo_platform.services.sync_service import SourceSyncService

    from_date = None
    to_date = None

    if args.from_date:
        try:
            from_date = datetime.strptime(args.from_date, "%Y-%m-%d").date()
        except ValueError:
            sys.stderr.write(f"Error: Invalid --from-date format '{args.from_date}'. Expected YYYY-MM-DD.\n")
            return 2

    if args.to_date:
        try:
            to_date = datetime.strptime(args.to_date, "%Y-%m-%d").date()
        except ValueError:
            sys.stderr.write(f"Error: Invalid --to-date format '{args.to_date}'. Expected YYYY-MM-DD.\n")
            return 2

    sources = None
    if args.source and args.source.lower() != "all":
        sources = [s.strip().lower() for s in args.source.split(",") if s.strip()]

    try:
        engine = get_engine(args.db_url)
        sync_service = SourceSyncService(engine)
        sys.stdout.write(f"Synchronizing sources (sources={sources or 'all'}, dry_run={args.dry_run}, limit={args.limit})...\n")

        summary = sync_service.sync_all(
            sources=sources,
            from_date=from_date,
            to_date=to_date,
            limit=args.limit,
            dry_run=args.dry_run,
        )

        sys.stdout.write("=== Synchronization Results ===\n")
        sys.stdout.write(f"Total Sources Queried: {summary.total_sources}\n")
        sys.stdout.write(f"Total Raw Records Fetched: {summary.total_fetched}\n")
        sys.stdout.write(f"Total Valid Offerings Parsed: {summary.total_valid}\n")
        sys.stdout.write(f"Master IPO Records Ingested: {summary.master_records_ingested}\n")
        sys.stdout.write(f"GMP Quotes Recorded: {summary.gmp_quotes_recorded}\n")
        sys.stdout.write(f"Errors Encountered: {len(summary.errors)}\n")

        for src_name, res in summary.results_by_source.items():
            status_tag = "SUCCESS" if res.is_successful else "FAILED"
            sys.stdout.write(f"- [{src_name.upper()}]: {status_tag} (fetched: {res.records_fetched}, valid: {res.records_valid}, errors: {len(res.errors)})\n")

        if summary.errors:
            for err in summary.errors[:5]:
                sys.stderr.write(f"  Warning: {err}\n")

        return 0
    except Exception as err:
        sys.stderr.write(f"Sync Execution Error: {err}\n")
        return 1


def run_serve(args: argparse.Namespace) -> int:
    """
    Executes 'serve' command to launch the FastAPI REST API platform.
    """
    try:
        from ipo_platform.api.app import run_server
        sys.stdout.write(f"Starting IPO Platform API Server on {args.host}:{args.port} (reload={args.reload})...\n")
        run_server(host=args.host, port=args.port, reload=args.reload)
        return 0
    except Exception as err:
        sys.stderr.write(f"API Server Error: {err}\n")
        return 1


def build_parser() -> argparse.ArgumentParser:
    """
    Constructs the CLI ArgumentParser hierarchy.
    """
    parser = argparse.ArgumentParser(
        prog="ipo-cli",
        description="Operational CLI for Indian IPO Research, Analytics & Briefing Platform.",
    )
    parser.add_argument(
        "--db-url",
        dest="db_url",
        default=None,
        help="Target database connection URL (defaults to DATABASE_URL or sqlite:///:memory:)",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Operational Subcommands")

    # Command: ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a MasterIPORecord JSON file into the platform.")
    ingest_parser.add_argument("--file", "-f", required=True, help="Path to input JSON file.")

    # Command: list
    list_parser = subparsers.add_parser("list", help="List active IPO records with optional status filtering.")
    list_parser.add_argument(
        "--status",
        "-s",
        default=None,
        help="Optional IPO status filter (e.g. 'Currently Open', 'Closing Today', 'Upcoming').",
    )
    list_parser.add_argument("--skip", type=int, default=0, help="Number of records to skip.")
    list_parser.add_argument("--limit", type=int, default=100, help="Maximum records to return.")

    # Command: briefing
    briefing_parser = subparsers.add_parser("briefing", help="Generate daily intelligence briefing report.")
    briefing_parser.add_argument(
        "--date",
        "-d",
        default=None,
        help="Target date for the briefing (YYYY-MM-DD format). Defaults to today.",
    )
    briefing_parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="Output directory for generated markdown report (defaults to reports/daily).",
    )
    briefing_parser.add_argument(
        "--print",
        "-p",
        action="store_true",
        help="Print the generated briefing report to stdout.",
    )
    briefing_parser.add_argument(
        "--notify",
        "-n",
        default=None,
        help="Optional comma-separated channels to dispatch notification to (e.g., 'telegram,slack,email').",
    )
    briefing_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate notification dispatch without making external network calls.",
    )

    # Command: migrate
    subparsers.add_parser("migrate", help="Execute database schema migrations.")

    # Command: backtest
    backtest_parser = subparsers.add_parser("backtest", help="Execute historical strategy backtest.")
    backtest_parser.add_argument(
        "--ipo-ids",
        default=None,
        help="Optional comma-separated list of IPO IDs to simulate.",
    )
    backtest_parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON analysis results to stdout.",
    )

    # Command: sync-sources
    sync_parser = subparsers.add_parser("sync-sources", help="Synchronize live offerings from upstream exchange and market feeds.")
    sync_parser.add_argument(
        "--source",
        "-s",
        default="all",
        help="Specific source to sync ('nse', 'bse', 'gmp', or 'all'). Defaults to 'all'.",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate upstream synchronization without persisting records to the database.",
    )
    sync_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum records to fetch per source (defaults to 50).",
    )
    sync_parser.add_argument(
        "--from-date",
        default=None,
        help="Start date filter (YYYY-MM-DD format).",
    )
    sync_parser.add_argument(
        "--to-date",
        default=None,
        help="End date filter (YYYY-MM-DD format).",
    )

    # Command: serve
    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI REST API platform server.")
    serve_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host IP interface to bind server to (default: 0.0.0.0).",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="TCP port to bind server to (default: 8000).",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code modifications.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entrypoint.
    """
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.subcommand:
        parser.print_help(sys.stderr)
        return 2

    command_handlers = {
        "ingest": run_ingest,
        "list": run_list,
        "briefing": run_briefing,
        "migrate": run_migrate,
        "backtest": run_backtest,
        "sync-sources": run_sync_sources,
        "serve": run_serve,
    }

    handler = command_handlers.get(args.subcommand)
    if not handler:
        sys.stderr.write(f"Unknown subcommand: {args.subcommand}\n")
        return 2

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
