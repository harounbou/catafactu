# tests/test_concurrency.py
import pytest
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from modules.product_management import add_or_update_product, update_stock, load_products
from modules.utils import get_db_connection
import streamlit as st

class MockSessionState:
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
        "reference": "SEC-001",
        "denomination": "Security Test Product",
        "quantite_actuelle": 100,
        "quantite_initiale": 100,
        "quantite_restockee": 0,
        "quantite_vendue": 0,
        "couleurs-dispo-usine": "red,blue",
        "images": "",
        "prix-super-gros": 10.0,
        "prix-gros": 15.0,
        "prix-détail": 20.0,
        "uni_colour": 0,
        "default_colour": 0,
        "brown": 0,
        "brown_deg": 0,
        "blue": 50,
        "white": 0,
        "black": 0,
        "green_bottle": 0,
        "red": 50,
        "grey": 0,
        "grey_deg": 0,
        "beige": 0,
        "yellow": 0,
        "orange": 0,
        "garnet": 0,
        "golden": 0,
        "green": 0,
        "rose": 0,
        "note": "Test note",
        "category": "Test",
        "quantite_vendu_actue": 0,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "discontinued": 0,
        "version": 0
    }

@pytest.fixture(autouse=True)
def setup_database():
    conn = get_db_connection()
    try:
        conn.execute("DROP TABLE IF EXISTS products")
        conn.execute("""
            CREATE TABLE products (
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
                uni_colour INTEGER,
                default_colour INTEGER,
                brown INTEGER,
                brown_deg INTEGER,
                blue INTEGER,
                white INTEGER,
                black INTEGER,
                green_bottle INTEGER,
                red INTEGER,
                grey INTEGER,
                grey_deg INTEGER,
                beige INTEGER,
                yellow INTEGER,
                orange INTEGER,
                garnet INTEGER,
                golden INTEGER,
                green INTEGER,
                rose INTEGER,
                note TEXT,
                category TEXT,
                quantite_vendu_actue INTEGER,
                last_updated TEXT,
                discontinued INTEGER,
                version INTEGER DEFAULT 0
            )
        """)
        conn.execute("DROP TABLE IF EXISTS transactions")
        conn.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                items TEXT,
                date TEXT
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Setup cleanup failed: {str(e)}")
    finally:
        conn.close()

def test_concurrent_stock_updates(test_product, mock_streamlit):
    # Initialize product
    assert add_or_update_product(test_product), "Failed to add product"
    initial_qty = 100

    # Simulate 10 concurrent updates, each reducing stock by 1
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(update_stock, test_product["reference"], -1) for _ in range(10)]
        for future in futures:
            future.result()  # Wait for all updates to complete

    # Verify final quantity
    final_product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    expected_qty = initial_qty - 10
    print(f"Initial qty: {initial_qty}, Final qty: {final_product['quantite_actuelle']}, Expected: {expected_qty}")
    assert final_product["quantite_actuelle"] == expected_qty, \
        f"Expected {expected_qty}, got {final_product['quantite_actuelle']}"