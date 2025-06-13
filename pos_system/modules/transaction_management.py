# modules/transaction_management.py
import streamlit as st
import sqlite3
import json
import pandas as pd
import numpy as np
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
        # Enhanced converter for JSON serialization
        def convert(o):
            if isinstance(o, (np.int64, np.int32)):
                return int(o)
            if isinstance(o, (np.float64, np.float32)):
                if np.isnan(o):
                    return None  # Handle NaN explicitly
                return float(o)
            if isinstance(o, np.ndarray):
                return o.tolist()  # Convert NumPy arrays to lists
            raise TypeError(f"Object of type {type(o)} is not JSON serializable")

        # Serialize with error handling
        try:
            items_json = json.dumps(items, default=convert)
        except Exception as e:
            st.error(f"Error serializing items: {str(e)}")
            raise

        try:
            payment_json = json.dumps(payment_details, default=convert)
        except Exception as e:
            st.error(f"Error serializing payment_details: {str(e)}")
            raise

        try:
            client_info_json = json.dumps(client_info, default=convert)
        except Exception as e:
            st.error(f"Error serializing client_info: {str(e)}")
            raise

        c = conn.cursor()
        transaction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO transactions (
                client_id, items, payment_details, total_amount, final_amount, 
                status, transaction_date, performed_by, tva_applied, tva_amount, 
                deposit_amount, remaining_amount, client_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client_info.get('id_client'), items_json, payment_json, total_amount, final_amount, 
            status, transaction_date, performed_by, tva_applied, tva_amount, 
            deposit_amount, remaining_amount, client_info_json
        ))
        transaction_id = c.lastrowid
        conn.commit()
        return transaction_id
    except Exception as e:
        conn.rollback()
        st.error(f"Error recording transaction: {str(e)}")
        raise
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
            st.error(f"Transaction {transaction_id} not found.")
            return False

        trans = trans_df.iloc[0]
        
        existing_payments = json.loads(trans['payment_details']) if trans['payment_details'] else {}
        updated_payments = {**existing_payments, **payment_details}
        
        total_paid = sum(updated_payments.values())
        
        c = conn.cursor()
        c.execute('''
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
    except Exception as e:
        st.error(f"Error fetching proformas: {str(e)}")
        return []
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
    conn = get_db_connection()
    try:
        # Get sum of all transactions
        transactions = pd.read_sql_query("""
            SELECT 
                SUM(CASE WHEN status = 'completed' THEN total_amount ELSE 0 END) as total_income,
                SUM(CASE WHEN status = 'canceled' THEN total_amount ELSE 0 END) as total_canceled,
                (SELECT COALESCE(SUM(amount), 0) FROM expenditures) as total_expenses,
                (SELECT COALESCE(SUM(amount), 0) FROM staff_payments) as total_staff_payments
            FROM transactions
        """, conn)
        
        balance = (transactions['total_income'].iloc[0] or 0) - \
                 (transactions['total_expenses'].iloc[0] or 0) - \
                 (transactions['total_staff_payments'].iloc[0] or 0)
        
        return balance
    except Exception as e:
        st.error(f"Error calculating till balance: {e}")
        return 0

def backup_transactions(backup_dir='backups'):
    """
    Create a backup of all transaction-related tables.
    
    Args:
        backup_dir (str): Directory to store the backup file
        
    Returns:
        dict: Dictionary with backup file paths or None if backup failed
    """
    import os
    import json
    from datetime import datetime
    
    try:
        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        conn = get_db_connection()
        backup_files = {}
        
        # Backup transactions table
        transactions_df = pd.read_sql_query('SELECT * FROM transactions', conn)
        transactions_file = os.path.join(backup_dir, f'transactions_backup_{timestamp}.json')
        transactions_df.to_json(transactions_file, orient='records', date_format='iso', default_handler=str)
        backup_files['transactions'] = transactions_file
        
        # Backup expenditures table
        try:
            expenditures_df = pd.read_sql_query('SELECT * FROM expenditures', conn)
            expenditures_file = os.path.join(backup_dir, f'expenditures_backup_{timestamp}.json')
            expenditures_df.to_json(expenditures_file, orient='records', date_format='iso', default_handler=str)
            backup_files['expenditures'] = expenditures_file
        except Exception as e:
            print(f"Warning: Could not backup expenditures: {e}")
        
        # Backup staff_payments table
        try:
            staff_payments_df = pd.read_sql_query('SELECT * FROM staff_payments', conn)
            staff_payments_file = os.path.join(backup_dir, f'staff_payments_backup_{timestamp}.json')
            staff_payments_df.to_json(staff_payments_file, orient='records', date_format='iso', default_handler=str)
            backup_files['staff_payments'] = staff_payments_file
        except Exception as e:
            print(f"Warning: Could not backup staff_payments: {e}")
        
        return backup_files
        
    except Exception as e:
        print(f"Error creating transactions backup: {e}")
        return None
    finally:
        conn.close()