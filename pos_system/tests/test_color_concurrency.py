# tests/test_color_concurrency.py

import pytest
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from modules.product_management import add_or_update_product, update_stock, load_products
from modules.utils import get_db_connection
import streamlit as st

# Mock Streamlit's session_state
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
        "quantite_actuelle": 0,
        "quantite_initiale": 0,
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
        "blue": 0,
        "white": 0,
        "black": 0,
        "green_bottle": 0,
        "red": 0,
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
                quantite_initiale INTEGER,  -- Changed to INTEGER
                quantite_restockee INTEGER,  -- Changed to INTEGER
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

def test_concurrent_red_updates(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    initial_red = 0  # Starting at 0
    num_updates = 50
    
    # Add stock before reducing it
    update_stock(test_product["reference"], 50, "red")  # Add 50 red items
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(update_stock, test_product["reference"], -1, "red") for _ in range(num_updates)]
        for future in futures:
            future.result()
    
    final_product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    expected_red = 0  # 50 - 50 = 0
    color_fields = [
        "uni_colour", "default_colour", "brown", "brown_deg", "blue", "white", "black",
        "green_bottle", "red", "grey", "grey_deg", "beige", "yellow", "orange", "garnet",
        "golden", "green", "rose"
    ]
    color_sum = sum(final_product[col] for col in color_fields if final_product[col] is not None)
    print(f"Red updates: Initial red: {initial_red + 50}, Final red: {final_product['red']}, Expected: {expected_red}")
    print(f"quantite_actuelle: {final_product['quantite_actuelle']}, Sum of colors: {color_sum}")
    assert final_product["red"] == expected_red, f"Expected red {expected_red}, got {final_product['red']}"
    assert final_product["quantite_actuelle"] == color_sum, "quantite_actuelle should equal sum of colors"

def test_mixed_color_updates(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    initial_red = 0
    initial_blue = 0
    num_updates = 25
    
    # Add stock before reducing it
    update_stock(test_product["reference"], 50, "red")  # Add 50 red
    update_stock(test_product["reference"], 50, "blue")  # Add 50 blue
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        red_futures = [executor.submit(update_stock, test_product["reference"], -1, "red") for _ in range(num_updates)]
        blue_futures = [executor.submit(update_stock, test_product["reference"], -1, "blue") for _ in range(num_updates)]
        for future in red_futures + blue_futures:
            future.result()
    
    final_product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    expected_red = 25  # 50 - 25 = 25
    expected_blue = 25  # 50 - 25 = 25
    color_sum = sum(final_product[col] for col in [
        "uni_colour", "default_colour", "brown", "brown_deg", "blue", "white", "black",
        "green_bottle", "red", "grey", "grey_deg", "beige", "yellow", "orange", "garnet",
        "golden", "green", "rose"
    ] if final_product[col] is not None)
    print(f"Mixed updates: Initial red: {initial_red + 50}, Final red: {final_product['red']}, Expected: {expected_red}")
    print(f"Mixed updates: Initial blue: {initial_blue + 50}, Final blue: {final_product['blue']}, Expected: {expected_blue}")
    print(f"quantite_actuelle: {final_product['quantite_actuelle']}, Sum of colors: {color_sum}")
    assert final_product["red"] == expected_red, f"Expected red {expected_red}, got {final_product['red']}"
    assert final_product["blue"] == expected_blue, f"Expected blue {expected_blue}, got {final_product['blue']}"
    assert final_product["quantite_actuelle"] == color_sum, "quantite_actuelle should equal sum of colors"

def test_total_vs_color_conflict(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    initial_qty = 0
    initial_red = 0
    initial_blue = 0
    num_total_updates = 25
    num_red_updates = 25
    
    # Add stock before reducing it
    update_stock(test_product["reference"], 50, "red")  # Add 50 red
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        total_futures = [executor.submit(update_stock, test_product["reference"], -1) for _ in range(num_total_updates)]
        red_futures = [executor.submit(update_stock, test_product["reference"], -1, "red") for _ in range(num_red_updates)]
        for future in total_futures + red_futures:
            future.result()
    
    final_product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    expected_red = 0  # 50 - (25 + 25) = 0, assuming total updates affect colors
    color_sum = sum(final_product[col] for col in [
        "uni_colour", "default_colour", "brown", "brown_deg", "blue", "white", "black",
        "green_bottle", "red", "grey", "grey_deg", "beige", "yellow", "orange", "garnet",
        "golden", "green", "rose"
    ] if final_product[col] is not None)
    print(f"Total vs Color: Initial qty: {initial_qty + 50}, Final qty: {final_product['quantite_actuelle']}, Sum of colors: {color_sum}")
    print(f"Total vs Color: Initial red: {initial_red + 50}, Final red: {final_product['red']}, Expected: {expected_red}")
    print(f"Initial blue: {initial_blue}, Final blue: {final_product['blue']}")
    assert final_product["red"] == expected_red, f"Expected red {expected_red}, got {final_product['red']}"
    assert final_product["quantite_actuelle"] == color_sum, "quantite_actuelle should equal sum of colors"

def test_total_vs_color_conflict(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    initial_qty = 0
    initial_red = 0
    initial_blue = 0  # Added missing variable definition
    num_total_updates = 25
    num_red_updates = 25
    
    # Add stock before reducing it
    update_stock(test_product["reference"], 50, "red")  # Add 50 red
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        total_futures = [executor.submit(update_stock, test_product["reference"], -1) for _ in range(num_total_updates)]
        red_futures = [executor.submit(update_stock, test_product["reference"], -1, "red") for _ in range(num_red_updates)]
        for future in total_futures + red_futures:
            future.result()
    
    final_product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    expected_red = 0  # 50 - (25 + 25) = 0
    color_sum = sum(final_product[col] for col in [
        "uni_colour", "default_colour", "brown", "brown_deg", "blue", "white", "black",
        "green_bottle", "red", "grey", "grey_deg", "beige", "yellow", "orange", "garnet",
        "golden", "green", "rose"
    ] if final_product[col] is not None)
    print(f"Total vs Color: Initial qty: {initial_qty + 50}, Final qty: {final_product['quantite_actuelle']}, Sum of colors: {color_sum}")
    print(f"Total vs Color: Initial red: {initial_red + 50}, Final red: {final_product['red']}, Expected: {expected_red}")
    print(f"Initial blue: {initial_blue}, Final blue: {final_product['blue']}")
    assert final_product["red"] == expected_red, f"Expected red {expected_red}, got {final_product['red']}"
    assert final_product["quantite_actuelle"] == color_sum, "quantite_actuelle should equal sum of colors"