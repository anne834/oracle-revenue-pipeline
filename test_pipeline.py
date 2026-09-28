import csv
import importlib.util
import io
import random
from pathlib import Path

ROOT = Path(__file__).parent


def load(name, rel_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = load("generator_lambda", "lambda/generator/lambda_function.py")
processor = load("processor_lambda", "lambda/processor/lambda_function.py")


def roundtrip(rows):
    """Write rows to CSV text and read them back, exactly as the processor reads from S3."""
    text = generator.to_csv(rows).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def make_rows(n=300):
    random.seed(0)
    contracts, usage, billing = generator.generate_dataset(n)
    return processor.build_rows(roundtrip(contracts), roundtrip(usage), roundtrip(billing))


def test_generator_row_counts_and_unique_ids():
    contracts, usage, billing = generator.generate_dataset(200)
    assert len(contracts) == len(usage) == len(billing) == 200
    assert len({c["account_id"] for c in contracts}) == 200


def test_generator_regions_are_valid():
    contracts, _, _ = generator.generate_dataset(200)
    assert {c["region"] for c in contracts} <= set(generator.REGIONS)


def test_discount_violation_flag_matches_rule():
    _, _, billing = generator.generate_dataset(200)
    for b in billing:
        assert b["discount_violation_flag"] == (
            b["applied_discount_pct"] > b["discount_ceiling_pct"]
        )


def test_build_rows_joins_and_computes_unbilled():
    rows = make_rows(200)
    assert len(rows) == 200
    for r in rows:
        if r["underbilled_flag"]:
            assert r["unbilled_usd"] > 0
        else:
            assert r["unbilled_usd"] == 0


def test_detect_summary_is_consistent():
    rows, summary = processor.detect(make_rows(300))
    assert summary["accounts"] == 300
    assert summary["underbilled_accounts"] == sum(r["underbilled_flag"] for r in rows)
    assert summary["discount_violations"] == sum(r["discount_violation_flag"] for r in rows)
    assert "logreg_recall_holdout" in summary
    assert all("isolation_forest_flag" in r for r in rows)