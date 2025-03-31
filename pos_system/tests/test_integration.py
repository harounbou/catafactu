# tests/test_integration.py
import pytest
import pandas as pd
from datetime import datetime
from modules.product_management import add_or_update_product, mark_discontinued, permanently_delete, load_products
from modules.utils import get_db_connection
import streamlit as st

class MockSessionState:
    """Mimic Streamlit's SessionStateProxy with attribute access."""
    def __init__(self):
        self._data = {'user': {'role': 'admin', 'username': 'test_user'}}

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(f"'MockSessionState' object has no attribute '{key}'")

    def __getitem__(self, key):
        return self._data[key]

@pytest.fixture
def mock_streamlit(monkeypatch):
    """Mock streamlit.session_state for tests."""
    class MockStreamlit:
        session_state = MockSessionState()
        @staticmethod
        def error(msg):
            print(msg)
        @staticmethod
        def success(msg):
            print(msg)
    monkeypatch.setattr('modules.product_management.st', MockStreamlit())
    monkeypatch.setattr('modules.utils.st', MockStreamlit())

@pytest.fixture
def test_product():
    return {
        "reference": "INTEG-001",
        "denomination": "Integration Test Product",
        "quantite_actuelle": 50,
        "quantite_initiale": 50,
        "quantite_restockee": 0,
        "quantite_vendue": 0,
        "couleurs-dispo-usine": "red,blue",
        "red": 30,
        "blue": 20,
        "images": "",
        "prix-super-gros": 100.0,
        "prix-gros": 150.0,
        "prix-détail": 200.0,
        "discontinued": 0,
        "category": "Test",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@pytest.fixture(autouse=True)
def setup_database():
    """Ensure a clean database state before each test."""
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                reference TEXT PRIMARY KEY,
                denomination TEXT,
                quantite_initiale REAL,
                quantite_restockee REAL,
                quantite_vendue INTEGER,
                quantite_actuelle INTEGER,
                `couleurs-dispo-usine` TEXT,
                images TEXT,
                `prix-super-gros` REAL,
                `prix-gros` REAL,
                `prix-détail` REAL,
                red INTEGER,
                blue INTEGER,
                last_updated TEXT,
                discontinued INTEGER,
                category TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                client_id INTEGER,
                items TEXT,
                total_amount REAL,
                status TEXT,
                payment_type TEXT,
                deposit_amount REAL,
                remaining_amount REAL,
                payment_details TEXT,
                payment_amount REAL,
                transaction_date TEXT,
                performed_by TEXT,
                linked_proforma_id INTEGER,
                tva_applied BOOLEAN,
                tva_amount REAL,
                client_info TEXT,
                final_amount REAL,
                watermark TEXT,
                reservation_expiry TEXT
            )
        """)
        conn.execute("DELETE FROM products WHERE reference = 'INTEG-001'")
        conn.execute("DELETE FROM transactions WHERE items LIKE '%INTEG-001%'")
        conn.commit()
    except Exception as e:
        print(f"Setup cleanup failed: {str(e)}")
    finally:
        conn.close()

def record_transaction(reference, quantity, conn):
    """Simulate a transaction."""
    items = [{"reference": reference, "quantity": quantity}]
    conn.execute(
        "INSERT INTO transactions (items, status, transaction_date) VALUES (?, ?, ?)",
        (str(items), "completed", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

def test_full_product_lifecycle(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    conn = get_db_connection()
    record_transaction(test_product["reference"], 10, conn)
    updates = test_product.copy()
    updates["red"] = 25
    updates["quantite_actuelle"] = 45
    assert add_or_update_product(updates, is_update=True), "Failed to edit product"
    transactions = pd.read_sql_query(
        "SELECT * FROM transactions WHERE items LIKE ?",
        conn, params=(f'%{test_product["reference"]}%',)
    )
    print(f"Transactions after insert: {len(transactions)}")
    assert len(transactions) > 0, "Transaction not found"
    assert mark_discontinued(test_product["reference"]), "Failed to discontinue"
    active_products = load_products(active_only=True)
    assert test_product["reference"] not in active_products["reference"].values, "Discontinued product in active list"
    with pytest.raises(ValueError, match="Product has associated transactions"):
        permanently_delete(test_product["reference"])
    conn.execute("DELETE FROM transactions WHERE items LIKE ?", (f'%{test_product["reference"]}%',))
    conn.commit()
    transactions_after_cleanup = pd.read_sql_query(
        "SELECT * FROM transactions WHERE items LIKE ?",
        conn, params=(f'%{test_product["reference"]}%',)
    )
    print(f"Transactions after cleanup: {len(transactions_after_cleanup)}")
    assert permanently_delete(test_product["reference"]), "Failed to delete after cleanup"
    conn.close()