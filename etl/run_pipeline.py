import logging
import time

from sqlalchemy import text

from etl.config import REPORTS
from etl.extract import extract
from etl.load import get_engine, load_warehouse
from etl.reconcile import reconcile
from etl.transform import transform
from etl.validate import quality_report, validate

log = logging.getLogger("pipeline")


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    engine = get_engine()
    start = time.perf_counter()

    with engine.begin() as conn:
        run_id = conn.execute(text(
            "INSERT INTO pipeline_runs (status) VALUES ('running') RETURNING run_id"
        )).scalar_one()

    status, notes = "failed", "unknown error"
    try:
        raw = extract()
        data = transform(raw)
        good, bad = validate(data)

        report = quality_report(data, good, bad)
        REPORTS.mkdir(exist_ok=True)
        (REPORTS / "quality_report.txt").write_text(report, encoding="utf-8")
        log.info("\n%s", report)

        load_warehouse(engine, good, bad)
        reconcile(engine, data, bad)

        status = "success"
        notes = f"{time.perf_counter() - start:.1f}s"
        log.info("PIPELINE SUCCESS in %s", notes)
    except Exception as exc:
        notes = str(exc)[:500]
        log.exception("PIPELINE FAILED")
        raise
    finally:
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE pipeline_runs SET finished_at = now(), status = :s, notes = :n "
                "WHERE run_id = :r"), {"s": status, "n": notes, "r": run_id})


if __name__ == "__main__":
    main()