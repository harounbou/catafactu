# tests/test_edge_cases.py
import pytest
import pandas as pd
from datetime import datetime
from modules.product_management import add_or_update_product, update_stock, load_products
from modules.utils import get_db_connection
import streamlit as st

# Mock Streamlit's session_state (copied from test_concurrency.py)
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

def test_negative_stock(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    assert not update_stock(test_product["reference"], -101), "Should fail reducing stock below 0"
    product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    assert product["quantite_actuelle"] == 100, "Stock should remain unchanged"

def test_duplicate_reference(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "First add should succeed"
    duplicate_product = test_product.copy()
    assert not add_or_update_product(duplicate_product), "Duplicate reference should fail"
    products = load_products()
    assert len(products) == 1, "Only one product should exist"

def test_invalid_color(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    assert not update_stock(test_product["reference"], -1, "green"), "Invalid color should fail"
    product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    assert product["red"] == 50 and product["blue"] == 50, "Colors should remain unchanged"

def test_zero_quantity_change(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    assert update_stock(test_product["reference"], 0), "Zero change should succeed"
    product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    assert product["quantite_actuelle"] == 100, "Stock should remain 100"
    assert product["version"] == 1, "Version should increment"

def test_missing_product(mock_streamlit):
    assert not update_stock("MISSING-001", -1), "Update on missing product should fail"