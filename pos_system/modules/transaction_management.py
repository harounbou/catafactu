# modules/transaction_management.py
import sqlite3
import json
import pandas as pd
from datetime import datetime
from .utils import get_db_connection
from turtle import st


def initialize_db():
    """Initialize all database tables with proper schema"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Transactions Table (updated with proforma relationship)
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY,
                    client_id TEXT,
                    items TEXT NOT NULL,
                    payment_details TEXT,
                    payment_amount REAL,
                    total_amount REAL NOT NULL,
                    status TEXT CHECK(status IN ('proforma', 'completed', 'canceled')),
                    transaction_date TEXT NOT NULL,
                    performed_by TEXT NOT NULL,
                    linked_proforma_id INTEGER DEFAULT NULL,
                    FOREIGN KEY(linked_proforma_id) REFERENCES transactions(transaction_id)
                 )''')

    # Expenditures Table
    c.execute('''CREATE TABLE IF NOT EXISTS expenditures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL,
                    assistant_name TEXT NOT NULL
                 )''')

    # Staff Payments Table
    c.execute('''CREATE TABLE IF NOT EXISTS staff_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL
                 )''')

    # Check and add missing columns to transactions table
    c.execute("PRAGMA table_info(transactions)")
    columns = [row[1] for row in c.fetchall()]
    
    column_definitions = {
        'linked_proforma_id': 'INTEGER DEFAULT NULL REFERENCES transactions(transaction_id)'
    }
    
    for col, definition in column_definitions.items():
        if col not in columns:
            c.execute(f"ALTER TABLE transactions ADD COLUMN {col} {definition}")

    conn.commit()
    conn.close()

def fetch_df_from_db(table_name):
    """Fetch all records from the specified table and return as a DataFrame."""
    initialize_db()  # Ensure the table exists
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        return df
    except sqlite3.Error as e:
        print(f"Database error fetching {table_name}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def record_transaction(client_info, items, payment_details, payment_amount, 
                      total_amount, status, performed_by, proforma_id=None):
    """Record any type of transaction (proforma or sale)"""
    initialize_db()
    conn = get_db_connection()
    c = conn.cursor()

    try:
        # Get next transaction ID
        transaction_id = c.execute("SELECT MAX(transaction_id) FROM transactions").fetchone()[0] or 1000
        transaction_id += 1

        c.execute("""
            INSERT INTO transactions 
            (transaction_id, client_id, items, payment_details, payment_amount,
             total_amount, status, transaction_date, performed_by, linked_proforma_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id,
            client_info.get('id_client') if client_info else None,
            json.dumps(items),
            payment_details,
            payment_amount,
            total_amount,
            status,
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            performed_by,
            proforma_id
        ))

        conn.commit()
        return transaction_id
    except sqlite3.Error as e:
        conn.rollback()
        raise Exception(f"Database error: {str(e)}")
    finally:
        conn.close()

def get_proformas():
    """Retrieve all proforma transactions"""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT transaction_id, transaction_date, client_id, items, total_amount 
            FROM transactions 
            WHERE status = 'proforma'
        """)
        return c.fetchall()
    finally:
        conn.close()

def record_expenditure(description, amount, assistant_name="N/A"):
    """Record an expenditure"""
    initialize_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        date = datetime.now().strftime("%d/%m/%Y")
        c.execute("""
            INSERT INTO expenditures 
            (description, amount, date, assistant_name)
            VALUES (?, ?, ?, ?)
        """, (description, amount, date, assistant_name))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Failed to record expenditure: {str(e)}")
    finally:
        conn.close()

def record_staff_payment(staff_name, amount, performed_by="N/A", note=""):
    """Record staff payment"""
    initialize_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        date = datetime.now().strftime("%d/%m/%Y")
        c.execute("""
            INSERT INTO staff_payments 
            (staff_name, amount, date)
            VALUES (?, ?, ?)
        """, (staff_name, amount, date))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Failed to record staff payment: {str(e)}")
    finally:
        conn.close()

def get_till_balance():
    """Calculate current till balance"""
    initialize_db()
    conn = get_db_connection()
    try:
        c = conn.cursor()
        
        # Get total completed sales
        c.execute("SELECT SUM(payment_amount) FROM transactions WHERE status = 'completed'")
        total_sales = c.fetchone()[0] or 0.0
        
        # Get total expenditures
        c.execute("SELECT SUM(amount) FROM expenditures")
        total_expenditures = c.fetchone()[0] or 0.0
        
        # Get total staff payments
        c.execute("SELECT SUM(amount) FROM staff_payments")
        total_staff_payments = c.fetchone()[0] or 0.0

        return total_sales - total_expenditures - total_staff_payments
    finally:
        conn.close()