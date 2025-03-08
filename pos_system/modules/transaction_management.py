import sqlite3
import json
from datetime import datetime

DB_PATH = "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY,
                    client_id TEXT,
                    items TEXT,
                    payment_details TEXT,
                    payment_amount REAL,
                    total_amount REAL,
                    status TEXT,
                    transaction_date TEXT,
                    performed_by TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenditures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT,
                    amount REAL,
                    date TEXT,
                    performed_by TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS staff_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_name TEXT,
                    amount REAL,
                    date TEXT,
                    performed_by TEXT,
                    note TEXT
                 )''')
    
    # Check and add missing columns to transactions table
    c.execute("PRAGMA table_info(transactions)")
    columns = [row[1] for row in c.fetchall()]
    required_columns = {
        'client_id': 'TEXT',
        'items': 'TEXT',
        'payment_details': 'TEXT',
        'payment_amount': 'REAL',
        'total_amount': 'REAL',
        'status': 'TEXT',
        'transaction_date': 'TEXT',
        'performed_by': 'TEXT'
    }
    for col, col_type in required_columns.items():
        if col not in columns:
            c.execute(f"ALTER TABLE transactions ADD COLUMN {col} {col_type}")
    
    conn.commit()
    conn.close()

def record_transaction(client_info, items, payment_details, payment_amount, total_amount, status, performed_by="N/A"):
    initialize_db()
    conn = get_db_connection()
    c = conn.cursor()
    transaction_id = c.execute("SELECT MAX(transaction_id) FROM transactions").fetchone()[0]
    transaction_id = (transaction_id + 1) if transaction_id else 1000
    client_id = client_info.get('id_client', 'N/A') if client_info else 'N/A'
    items_json = json.dumps(items)
    date = datetime.now().strftime("%d/%m/%Y")
    c.execute("INSERT INTO transactions (transaction_id, client_id, items, payment_details, payment_amount, total_amount, status, transaction_date, performed_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (transaction_id, client_id, items_json, payment_details, payment_amount, total_amount, status, date, performed_by))
    conn.commit()
    conn.close()
    return transaction_id

def record_expenditure(description, amount, performed_by="N/A"):
    initialize_db()
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime("%d/%m/%Y")
    c.execute("INSERT INTO expenditures (description, amount, date, performed_by) VALUES (?, ?, ?, ?)",
              (description, amount, date, performed_by))
    conn.commit()
    conn.close()

def record_staff_payment(staff_name, amount, performed_by="N/A", note=""):
    initialize_db()
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime("%d/%m/%Y")
    c.execute("INSERT INTO staff_payments (staff_name, amount, date, performed_by, note) VALUES (?, ?, ?, ?, ?)",
              (staff_name, amount, date, performed_by, note))
    conn.commit()
    conn.close()

def get_till_balance():
    initialize_db()
    conn = get_db_connection()
    c = conn.cursor()
    total_sales = c.execute("SELECT SUM(payment_amount) FROM transactions WHERE status = 'completed'").fetchone()[0] or 0
    total_expenditures = c.execute("SELECT SUM(amount) FROM expenditures").fetchone()[0] or 0
    total_staff_payments = c.execute("SELECT SUM(amount) FROM staff_payments").fetchone()[0] or 0
    conn.close()
    return total_sales - total_expenditures - total_staff_payments