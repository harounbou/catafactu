# modules/transaction_management.py
# modules/transaction_management.py
import streamlit as st
import sqlite3
import json
import pandas as pd
from datetime import datetime
from .utils import get_db_connection

def initialize_db():
    """Initialize all database tables with proper schema"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY,
                    client_id TEXT,
                    items TEXT NOT NULL,
                    payment_details TEXT,
                    total_amount REAL NOT NULL,
                    final_amount REAL NOT NULL DEFAULT 0,
                    status TEXT CHECK(status IN ('proforma', 'completed', 'canceled', 'deposit_paid')),
                    transaction_date TEXT NOT NULL,
                    performed_by TEXT NOT NULL,
                    tva_applied BOOLEAN DEFAULT 0,
                    tva_amount REAL DEFAULT 0,
                    deposit_amount REAL DEFAULT 0,
                    remaining_amount REAL DEFAULT 0,
                    client_info TEXT,
                    linked_proforma_id INTEGER DEFAULT NULL,
                    FOREIGN KEY(linked_proforma_id) REFERENCES transactions(transaction_id)
                 )''')

    c.execute("PRAGMA table_info(transactions)")
    columns = [row[1] for row in c.fetchall()]
    
    missing_columns = {
        'deposit_amount': 'REAL DEFAULT 0',
        'remaining_amount': 'REAL DEFAULT 0',
        'client_info': 'TEXT',
        'final_amount': 'REAL NOT NULL DEFAULT 0'
    }
    
    for col, definition in missing_columns.items():
        if col not in columns:
            c.execute(f"ALTER TABLE transactions ADD COLUMN {col} {definition}")

    conn.commit()
    conn.close()

def safe_json_loads(value):
    """Safely load JSON, returning an empty dict if value is None, empty, or invalid"""
    if value is None or not value:  # Handles None and empty strings
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}  # Return empty dict if JSON is invalid

def fetch_df_from_db(table_name):
    """Fetch all records from the specified table and return as a DataFrame."""
    initialize_db()
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        # Convert JSON strings to Python objects, handling None and invalid values
        if 'items' in df.columns:
            df['items'] = df['items'].apply(safe_json_loads)
        if 'payment_details' in df.columns:
            df['payment_details'] = df['payment_details'].apply(safe_json_loads)
        if 'client_info' in df.columns:
            df['client_info'] = df['client_info'].apply(safe_json_loads)
        return df
    except sqlite3.Error as e:
        print(f"Database error fetching {table_name}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def record_transaction(client_info, items, total_amount, payment_details, final_amount, 
                      status, performed_by, tva_applied=False, tva_amount=0.0,
                      deposit_amount=0, remaining_amount=0):
    """Record a transaction with support for deposits and partial payments"""
    conn = get_db_connection()
    try:
        items_json = json.dumps(items)
        payment_json = json.dumps(payment_details)
        client_info_json = json.dumps(client_info)
        
        conn.execute('''INSERT INTO transactions 
                      (client_id, items, total_amount, payment_details, final_amount,
                      status, transaction_date, performed_by, tva_applied, tva_amount,
                      deposit_amount, remaining_amount, client_info)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (client_info.get('id_client', None), items_json, total_amount,
                       payment_json, final_amount, status, 
                       datetime.now().strftime("%d/%m/%Y %H:%M"),
                       performed_by, tva_applied, tva_amount,
                       deposit_amount, remaining_amount, client_info_json))
        conn.commit()
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    except Exception as e:
        conn.rollback()
        st.error(f"Error recording transaction: {str(e)}")
        return None
    finally:
        conn.close()

def fetch_incomplete_transactions():
    """Retrieve transactions with remaining balance"""
    conn = get_db_connection()
    try:
        query = '''
            SELECT transaction_id, 
                   json_extract(client_info, '$.nom_client') as client_name,
                   remaining_amount
            FROM transactions
            WHERE status = 'deposit_paid' AND remaining_amount > 0
        '''
        df = pd.read_sql_query(query, conn)
        return df.to_dict('records')
    except Exception as e:
        st.error(f"Error fetching incomplete transactions: {str(e)}")
        return []
    finally:
        conn.close()

def complete_transaction(transaction_id, payment_details):
    """Complete a partially paid transaction"""
    conn = get_db_connection()
    try:
        trans_df = pd.read_sql_query(
            f"SELECT * FROM transactions WHERE transaction_id = {transaction_id}", 
            conn
        )
        
        if trans_df.empty:
            return False

        trans = trans_df.iloc[0]
        
        existing_payments = json.loads(trans['payment_details']) if trans['payment_details'] else {}
        updated_payments = {**existing_payments, **payment_details}
        
        total_paid = sum(updated_payments.values())
        
        conn.execute('''
            UPDATE transactions
            SET payment_details = ?,
                status = 'completed',
                remaining_amount = 0,
                final_amount = ?
            WHERE transaction_id = ?
        ''', (json.dumps(updated_payments), total_paid, transaction_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error completing transaction: {str(e)}")
        return False
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
        
        c.execute("SELECT SUM(payment_amount) FROM transactions WHERE status = 'completed'")
        total_sales = c.fetchone()[0] or 0.0
        
        c.execute("SELECT SUM(amount) FROM expenditures")
        total_expenditures = c.fetchone()[0] or 0.0
        
        c.execute("SELECT SUM(amount) FROM staff_payments")
        total_staff_payments = c.fetchone()[0] or 0.0

        return total_sales - total_expenditures - total_staff_payments
    finally:
        conn.close()