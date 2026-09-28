import csv
import io
import json
import os

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

FEATURES = ["usage_ratio", "bill_ratio", "discount_excess", "applied_discount_pct"]


def _flag(value):
    return str(value).strip().lower() == "true"


def build_rows(contracts, usage, billing):
    """Join contracts, usage, and billing on account_id and add features."""
    contracts_by_id = {r["account_id"]: r for r in contracts}
    usage_by_id = {r["account_id"]: r for r in usage}
    rows = []
    for b in billing:
        acc = b["account_id"]
        c, u = contracts_by_id[acc], usage_by_id[acc]
        expected = float(b["expected_bill_usd"])
        actual = float(b["actual_bill_usd"])
        applied = float(b["applied_discount_pct"])
        ceiling = float(b["discount_ceiling_pct"])
        rows.append({
            "account_id": acc,
            "assigned_rep_id": b["assigned_rep_id"],
            "region": c["region"],
            "usage_ratio": float(u["actual_compute_hours"]) / float(c["contracted_compute_hours"]),
            "bill_ratio": actual / expected if expected else 1.0,
            "discount_excess": applied - ceiling,
            "applied_discount_pct": applied,
            "unbilled_usd": round(expected - actual, 2),
            "overuse_flag": _flag(u["overuse_flag"]),
            "underbilled_flag": _flag(b["underbilled_flag"]),
            "discount_violation_flag": applied > ceiling,
        })
    return rows


def detect(rows, seed=42):
    """Run Isolation Forest (unsupervised) and Logistic Regression (supervised)."""
    X = np.array([[r[f] for f in FEATURES] for r in rows])
    X = StandardScaler().fit_transform(X)
    y = np.array([r["underbilled_flag"] for r in rows], dtype=int)

    iso = IsolationForest(contamination=0.15, random_state=seed)
    iso_pred = iso.fit_predict(X) == -1

    # Any injected leakage type counts as "leaky" for scoring Isolation Forest
    truth = np.array(
        [r["underbilled_flag"] or r["overuse_flag"] or r["discount_violation_flag"] for r in rows]
    )

    summary = {
        "accounts": len(rows),
        "overuse_accounts": sum(r["overuse_flag"] for r in rows),
        "underbilled_accounts": int(y.sum()),
        "unbilled_usd": round(sum(r["unbilled_usd"] for r in rows if r["underbilled_flag"]), 2),
        "discount_violations": sum(r["discount_violation_flag"] for r in rows),
        "isolation_forest_flagged": int(iso_pred.sum()),
    }
    if iso_pred.any() and truth.any():
        summary["isolation_forest_precision"] = round(float(precision_score(truth, iso_pred)), 3)
        summary["isolation_forest_recall"] = round(float(recall_score(truth, iso_pred)), 3)

    lr_pred = np.zeros(len(rows), dtype=bool)
    if 0 < y.sum() < len(y):
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.3, stratify=y, random_state=seed
        )
        lr = LogisticRegression(max_iter=1000).fit(X_tr, y_tr)
        held_out = lr.predict(X_te)
        summary["logreg_precision_holdout"] = round(float(precision_score(y_te, held_out)), 3)
        summary["logreg_recall_holdout"] = round(float(recall_score(y_te, held_out)), 3)
        lr_pred = lr.predict(X).astype(bool)

    for r, iso_flag, lr_flag in zip(rows, iso_pred, lr_pred):
        r["isolation_forest_flag"] = bool(iso_flag)
        r["logreg_underbilled_flag"] = bool(lr_flag)
    return rows, summary


def _read(s3, bucket, name, run_date):
    key = f"raw/{name}/date={run_date}/{name}.csv"
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(body)))


def lambda_handler(event, context):
    import boto3

    bucket = os.environ["BUCKET"]
    run_date = event["date"]
    s3 = boto3.client("s3")

    rows = build_rows(
        _read(s3, bucket, "contracts", run_date),
        _read(s3, bucket, "usage", run_date),
        _read(s3, bucket, "billing", run_date),
    )
    rows, summary = detect(rows)
    summary["date"] = run_date

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    prefix = f"processed/date={run_date}"
    s3.put_object(Bucket=bucket, Key=f"{prefix}/flagged_accounts.csv", Body=buf.getvalue().encode("utf-8"))
    s3.put_object(Bucket=bucket, Key=f"{prefix}/summary.json", Body=json.dumps(summary, indent=2).encode("utf-8"))
    return summary