from faker import Faker
import pandas as pd
import random

fake = Faker()

# ── 1. Contracts (same as before) ──────────────────────────────────────
contracts = []
for _ in range(500):
    contracts.append({
        'account_id': fake.uuid4(),
        'company_name': fake.company(),
        'contracted_compute_hours': random.randint(500, 10000),
        'contracted_storage_tb': random.randint(1, 100),
        'discount_ceiling_pct': round(random.uniform(5, 30), 2),
        'contract_start': str(fake.date_between(start_date='-2y', end_date='-1y')),
        'contract_end': str(fake.date_between(start_date='today', end_date='+1y')),
        'assigned_rep_id': fake.bothify('REP-###'),
        'region': random.choice(['US-EAST', 'US-WEST', 'EU', 'APAC'])
    })

df_contracts = pd.DataFrame(contracts)

# ── 2. Usage data ───────────────────────────────────────────────────────
# Some accounts use MORE than their contract allows (overuse leakage)
usage = []
for _, row in df_contracts.iterrows():
    overuse = random.random() < 0.15  # 15% of accounts overuse
    multiplier = random.uniform(1.1, 1.5) if overuse else random.uniform(0.5, 0.95)
    usage.append({
        'account_id': row['account_id'],
        'actual_compute_hours': round(row['contracted_compute_hours'] * multiplier, 2),
        'actual_storage_tb': round(row['contracted_storage_tb'] * multiplier, 2),
        'overuse_flag': overuse
    })

df_usage = pd.DataFrame(usage)

# ── 3. Billing data ─────────────────────────────────────────────────────
# Some accounts are billed LESS than they should be (underbilling leakage)
HOURLY_RATE = 0.50  # $0.50 per compute hour

billing = []
for _, row in df_usage.iterrows():
    expected_bill = round(row['actual_compute_hours'] * HOURLY_RATE, 2)
    underbilled = random.random() < 0.15  # 15% are underbilled
    actual_bill = round(expected_bill * random.uniform(0.65, 0.90), 2) if underbilled else expected_bill
    
    # Find rep for this account
    rep_id = df_contracts.loc[df_contracts['account_id'] == row['account_id'], 'assigned_rep_id'].values[0]
    applied_discount = round(random.uniform(0, 40), 2)  # some reps over-discount
    ceiling = df_contracts.loc[df_contracts['account_id'] == row['account_id'], 'discount_ceiling_pct'].values[0]

    billing.append({
        'account_id': row['account_id'],
        'expected_bill_usd': expected_bill,
        'actual_bill_usd': actual_bill,
        'underbilled_flag': underbilled,
        'assigned_rep_id': rep_id,
        'applied_discount_pct': applied_discount,
        'discount_ceiling_pct': ceiling,
        'discount_violation_flag': applied_discount > ceiling
    })

df_billing = pd.DataFrame(billing)

# ── 4. Save all three to CSV ────────────────────────────────────────────
df_contracts.to_csv('contracts.csv', index=False)
df_usage.to_csv('usage.csv', index=False)
df_billing.to_csv('billing.csv', index=False)

print("✓ contracts.csv generated:", len(df_contracts), "rows")
print("✓ usage.csv generated:", len(df_usage), "rows")
print("✓ billing.csv generated:", len(df_billing), "rows")
print("\nLeakage summary:")
print("  Overuse cases:", df_usage['overuse_flag'].sum())
print("  Underbilling cases:", df_billing['underbilled_flag'].sum())
print("  Discount violations:", df_billing['discount_violation_flag'].sum())