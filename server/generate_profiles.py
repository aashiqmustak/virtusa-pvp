"""Add reproducible synthetic provider profiles without deleting existing cases."""
import argparse
from app.models import migrate,Session
from app.services.integrations.synthetic import seed_profiles
p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=100);args=p.parse_args()
if not 100<=args.count<=500:p.error('--count must be 100 to 500')
migrate()
with Session.begin() as s:seed_profiles(s,args.count)
print(f'{args.count} synthetic profiles available. No external requests made.')
