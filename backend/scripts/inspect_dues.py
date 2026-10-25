import os
import sys
sys.path.insert(0, ".")
from datetime import date
from collections import defaultdict
from app.config import get_settings
from app.db.client import Database

settings = get_settings()
db = Database(settings.database_url.get_secret_value())
db.open()

CURRENT_PERIOD = date(2026, 10, 1)

with db.transaction() as conn:
    with conn.cursor() as cur:
        # Test unpaid filter
        cur.execute('''
            SELECT s.id, s.name, s.id_no, s.monthly_fee_paise
            FROM students s
            WHERE NOT EXISTS (
                SELECT 1 FROM student_monthly_fees smf
                WHERE smf.student_id = s.id AND smf.period = '2026-10-01' AND smf.status = 'PAID'
            )
            LIMIT 5;
        ''')
        rows = cur.fetchall()
        print('Sample unpaid students count:', len(rows))
        student_ids = [r['id'] for r in rows]
        
        # Batch fetch their monthly fees
        cur.execute('''
            SELECT student_id, period, period_label, status, amount_paise
            FROM student_monthly_fees
            WHERE student_id = ANY(%s) AND status = 'PENDING'
            ORDER BY period DESC;
        ''', (student_ids,))
        fees = cur.fetchall()
        
        unpaid_map = defaultdict(list)
        for f in fees:
            unpaid_map[f['student_id']].append(f['period_label'])
            
        for s in rows:
            u_months = unpaid_map[s['id']]
            print(f"{s['id_no']} | {s['name']}: Oct 2026: UNPAID | Due: {u_months[:4]} ({len(u_months)} months)")

db.close()
