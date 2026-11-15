"""Compute headline leakage figures from the CSVs written by generate_data.py.

Usage: python analyze_local.py   (expects contracts.csv, usage.csv, billing.csv in the current folder)
"""
import pandas as pd

HOURLY_RATE = 0.50

contracts = pd.read_csv("contracts.csv")
usage = pd.read_csv("usage.csv")
billing = pd.read_csv("billing.csv")

merged = usage.merge(contracts, on="account_id").merge(billing, on="account_id", suffixes=("", "_b"))

overuse_usd = ((merged.actual_compute_hours - merged.contracted_compute_hours) * HOURLY_RATE)[merged.overuse_flag].sum()
underbilled_usd = (merged.expected_bill_usd - merged.actual_bill_usd)[merged.underbilled_flag].sum()
any_leak = merged.overuse_flag | merged.underbilled_flag | merged.discount_violation_flag

print(f"Accounts:                    {len(merged)}")
print(f"Overuse accounts:            {int(merged.overuse_flag.sum())}  (${overuse_usd:,.2f})")
print(f"Underbilled accounts:        {int(merged.underbilled_flag.sum())}  (${underbilled_usd:,.2f})")
print(f"Overuse + underbilling:      ${overuse_usd + underbilled_usd:,.2f}")
print(f"Discount violations:         {int(merged.discount_violation_flag.sum())}")
print(f"Accounts with any leakage:   {int(any_leak.sum())}")
