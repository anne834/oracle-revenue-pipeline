from faker import Faker
import pandas as pd
import random

fake = Faker()

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
print(df_contracts.head())
print(f"\nTotal accounts generated: {len(df_contracts)}")