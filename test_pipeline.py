import pandas as pd
import random
import pytest

# ── Helper function to generate test data ─────────────────────────────
def generate_contracts(n=500):
    contracts = []
    for i in range(n):
        contracts.append({
            'account_id': f'ACC-{i:04d}',
            'contracted_compute_hours': random.randint(500, 10000),
            'contracted_storage_tb': random.randint(1, 100),
            'discount_ceiling_pct': round(random.uniform(5, 30), 2),
            'region': random.choice(['US-EAST', 'US-WEST', 'EU', 'APAC']),
            'assigned_rep_id': f'REP-{random.randint(1, 200):03d}'
        })
    return pd.DataFrame(contracts)

# ── Test 1: Contract data has correct shape ────────────────────────────
def test_contract_shape():
    df = generate_contracts(500)
    assert df.shape[0] == 500, "Should have 500 rows"
    assert df.shape[1] == 6, "Should have 6 columns"
    print("✓ Test 1 passed: Contract data shape is correct")

# ── Test 2: No duplicate account IDs ──────────────────────────────────
def test_no_duplicate_accounts():
    df = generate_contracts(500)
    assert df['account_id'].nunique() == 500, "All account IDs should be unique"
    print("✓ Test 2 passed: No duplicate account IDs")

# ── Test 3: Leakage flag logic is correct ─────────────────────────────
def test_leakage_flag_logic():
    df = generate_contracts(500)
    df['actual_compute_hours'] = df['contracted_compute_hours'] * 1.2
    df['overuse_flag'] = df['actual_compute_hours'] > df['contracted_compute_hours']
    assert df['overuse_flag'].all(), "All accounts should be flagged as overuse"
    print("✓ Test 3 passed: Leakage flag logic is correct")

# ── Test 4: Discount violation detection ──────────────────────────────
def test_discount_violation_detection():
    df = generate_contracts(500)
    df['applied_discount_pct'] = 50  # force all discounts above ceiling
    df['discount_violation_flag'] = df['applied_discount_pct'] > df['discount_ceiling_pct']
    assert df['discount_violation_flag'].all(), "All accounts should have discount violations"
    print("✓ Test 4 passed: Discount violation detection works correctly")

# ── Test 5: Region values are valid ───────────────────────────────────
def test_valid_regions():
    df = generate_contracts(500)
    valid_regions = ['US-EAST', 'US-WEST', 'EU', 'APAC']
    assert df['region'].isin(valid_regions).all(), "All regions should be valid"
    print("✓ Test 5 passed: All region values are valid")