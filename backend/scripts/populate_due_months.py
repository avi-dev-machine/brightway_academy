import os
import sys
sys.path.insert(0, ".")
from datetime import date
from uuid import uuid4
from app.config import get_settings
from app.db.client import Database

settings = get_settings()
db = Database(settings.database_url.get_secret_value())
db.open()

CURRENT_PERIOD = date(2026, 10, 1)

MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def period_label(d: date) -> str:
    return f"{MONTH_NAMES[d.month]} {d.year}"

with db.transaction() as conn:
    with conn.cursor() as cur:
        # Fetch all active/valid students and their existing monthly records
        cur.execute('''
            SELECT s.id, s.id_no, s.name, s.monthly_fee_paise, s.status,
                   array_agg(smf.period) as all_periods,
                   array_agg(smf.period) FILTER (WHERE smf.status = 'PAID' OR smf.paid_on IS NOT NULL) as paid_periods
            FROM students s
            JOIN student_monthly_fees smf ON s.id = smf.student_id
            GROUP BY s.id, s.id_no, s.name, s.monthly_fee_paise, s.status;
        ''')
        students = cur.fetchall()
        
        inserted_smf = 0
        inserted_fees = 0
        
        for s in students:
            student_id = s['id']
            rate = s['monthly_fee_paise'] or 40000
            all_set = set(p for p in (s['all_periods'] or []) if p is not None)
            paid_set = set(p for p in (s['paid_periods'] or []) if p is not None)
            
            # Start period is either earliest recorded month, or at most 12 months back for inactive
            earliest = min(all_set) if all_set else date(2025, 1, 1)
            # For inactive students, only calculate up to 6 months back from their last active period
            if s['status'] == 'inactive':
                latest_paid = max(paid_set) if paid_set else earliest
                start_period = max(earliest, date(latest_paid.year, latest_paid.month, 1))
            else:
                start_period = max(earliest, date(2024, 1, 1))
            
            y, m = CURRENT_PERIOD.year, CURRENT_PERIOD.month
            while (y > start_period.year) or (y == start_period.year and m >= start_period.month):
                p = date(y, m, 1)
                label = period_label(p)
                
                # Check if this month is unpaid
                if p not in paid_set:
                    # 1. Insert or update student_monthly_fees as PENDING
                    cur.execute('''
                        INSERT INTO student_monthly_fees (
                            student_id, period, period_label, amount_paise, status, pending_paise
                        ) VALUES (%s, %s, %s, %s, 'PENDING', %s)
                        ON CONFLICT (student_id, period) DO UPDATE SET
                            status = 'PENDING',
                            amount_paise = EXCLUDED.amount_paise,
                            pending_paise = EXCLUDED.pending_paise
                        WHERE student_monthly_fees.status NOT IN ('PAID', 'CLOSED');
                    ''', (student_id, p, label, rate, rate))
                    inserted_smf += cur.rowcount
                    
                    # 2. Ensure matching record in fees table so student can pay online/offline
                    cur.execute('''
                        SELECT id FROM fees
                        WHERE student_id = %s AND due_date = %s;
                    ''', (student_id, p))
                    existing_fee = cur.fetchone()
                    if not existing_fee:
                        fee_id = uuid4()
                        cur.execute('''
                            INSERT INTO fees (
                                id, student_id, fee_type, title, amount_paise, paid_paise,
                                due_date, status, created_at
                            ) VALUES (%s, %s, 'MONTHLY', %s, %s, 0, %s, 'OVERDUE', now());
                        ''', (fee_id, student_id, f"Monthly Fee - {label}", rate, p))
                        inserted_fees += 1
                
                m -= 1
                if m == 0:
                    m = 12
                    y -= 1
        
        print(f"Due months synced: {inserted_smf} student_monthly_fees updated/created, {inserted_fees} payable fees created.")

db.close()
