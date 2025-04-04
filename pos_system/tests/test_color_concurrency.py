# tests/test_color_concurrency.py
import os
import pytest
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from modules.product_management import update_stock, check_stock, get_db_connection
from modules.product_management import add_or_update_product, update_stock, load_products
from modules.utils import get_db_connection, DB_PATH


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
    os.environ["TESTING"] = "1"
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        DROP TABLE IF EXISTS products;
        CREATE TABLE products (
            reference TEXT PRIMARY KEY,
            denomination TEXT,
            quantite_initiale INTEGER,
            quantite_restockee INTEGER,
            quantite_vendue INTEGER,
            "couleurs-dispo-usine" TEXT,
            images TEXT,
            "prix-super-gros" REAL,
            "prix-gros" REAL,
            "prix-détail" REAL,
            uni_colour INTEGER DEFAULT 0,
            default_colour INTEGER DEFAULT 0,
            brown INTEGER DEFAULT 0,
            brown_deg INTEGER DEFAULT 0,
            blue INTEGER DEFAULT 0,
            white INTEGER DEFAULT 0,
            black INTEGER DEFAULT 0,
            green_bottle INTEGER DEFAULT 0,
            red INTEGER DEFAULT 0,
            grey INTEGER DEFAULT 0,
            grey_deg INTEGER DEFAULT 0,
            beige INTEGER DEFAULT 0,
            yellow INTEGER DEFAULT 0,
            orange INTEGER DEFAULT 0,
            garnet INTEGER DEFAULT 0,
            golden INTEGER DEFAULT 0,
            green INTEGER DEFAULT 0,
            rose INTEGER DEFAULT 0,
            note TEXT,
            category TEXT,
            quantite_vendu_actue INTEGER,
            last_updated TEXT,
            discontinued INTEGER DEFAULT 0,
            version INTEGER DEFAULT 0,
            quantite_actuelle INTEGER GENERATED ALWAYS AS (
                COALESCE(uni_colour, 0) + COALESCE(default_colour, 0) + 
                COALESCE(brown, 0) + COALESCE(brown_deg, 0) + 
                COALESCE(blue, 0) + COALESCE(white, 0) + 
                COALESCE(black, 0) + COALESCE(green_bottle, 0) + 
                COALESCE(red, 0) + COALESCE(grey, 0) + 
                COALESCE(grey_deg, 0) + COALESCE(beige, 0) + 
                COALESCE(yellow, 0) + COALESCE(orange, 0) + 
                COALESCE(garnet, 0) + COALESCE(golden, 0) + 
                COALESCE(green, 0) + COALESCE(rose, 0)
            ) STORED
        );
        INSERT INTO products (reference, denomination, white, black, golden) 
        VALUES ('CHAIRX', 'Chair X', 2, 3, 4);
        INSERT INTO products (reference, denomination) 
        VALUES ('NEWITEM', 'New Item');
    """)
    conn.commit()
    conn.close()

def test_mixed_color_updates(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    update_stock(test_product["reference"], 50, "red")  # Add 50 red
    update_stock(test_product["reference"], 50, "blue")  # Add 50 blue
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        red_futures = [executor.submit(update_stock, test_product["reference"], -1, "red") for _ in range(25)]
        blue_futures = [executor.submit(update_stock, test_product["reference"], -1, "blue") for _ in range(25)]
        for future in red_futures + blue_futures:
            future.result()
    
    final_product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    expected_red = 25  # 50 - 25 = 25
    expected_blue = 25  # 50 - 25 = 25
    color_sum = sum(final_product[col] for col in [
        "uni_colour", "default_colour", "brown", "brown_deg", "blue", "white", "black",
        "green_bottle", "red", "grey", "grey_deg", "beige", "yellow", "orange", "garnet",
        "golden", "green", "rose"
    ])
    print(f"Mixed updates: Final red: {final_product['red']}, Expected: {expected_red}")
    print(f"Mixed updates: Final blue: {final_product['blue']}, Expected: {expected_blue}")
    print(f"quantite_actuelle: {final_product['quantite_actuelle']}, Sum of colors: {color_sum}")
    assert final_product["red"] == expected_red, f"Expected red {expected_red}, got {final_product['red']}"
    assert final_product["blue"] == expected_blue, f"Expected blue {expected_blue}, got {final_product['blue']}"
    assert final_product["quantite_actuelle"] == color_sum, "quantite_actuelle should equal sum of colors"

def test_total_vs_color_conflict(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    update_stock(test_product["reference"], 50, "red")  # Add 50 red
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        total_futures = [executor.submit(update_stock, test_product["reference"], -1) for _ in range(25)]
        red_futures = [executor.submit(update_stock, test_product["reference"], -1, "red") for _ in range(25)]
        for future in total_futures + red_futures:
            future.result()
    
    final_product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    expected_red = 25  # 50 - 25 (red updates) = 25, total updates affect default_colour
    color_sum = sum(final_product[col] for col in [
        "uni_colour", "default_colour", "brown", "brown_deg", "blue", "white", "black",
        "green_bottle", "red", "grey", "grey_deg", "beige", "yellow", "orange", "garnet",
        "golden", "green", "rose"
    ])
    print(f"Total vs Color: Final red: {final_product['red']}, Expected: {expected_red}")
    print(f"Total vs Color: Final default_colour: {final_product['default_colour']}")
    print(f"quantite_actuelle: {final_product['quantite_actuelle']}, Sum of colors: {color_sum}")
    assert final_product["red"] == expected_red, f"Expected red {expected_red}, got {final_product['red']}"
    assert final_product["quantite_actuelle"] == color_sum, "quantite_actuelle should equal sum of colors"

def test_existing_item_unspecified_color():
    update_stock("CHAIRX", 1, color=None)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT default_colour, quantite_actuelle FROM products WHERE reference = 'CHAIRX'")
    result = cursor.fetchone()
    conn.close()
    assert result["default_colour"] == 1, f"Expected default_colour 1, got {result['default_colour']}"
    assert result["quantite_actuelle"] == 10, f"Expected quantite_actuelle 10, got {result['quantite_actuelle']}"

def test_new_item_unspecified_color():
    update_stock("NEWITEM", 5, color=None)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT default_colour, quantite_actuelle FROM products WHERE reference = 'NEWITEM'")
    result = cursor.fetchone()
    conn.close()
    assert result["default_colour"] == 5, f"Expected default_colour 5, got {result['default_colour']}"
    assert result["quantite_actuelle"] == 5, f"Expected quantite_actuelle 5, got {result['quantite_actuelle']}"

def test_concurrent_red_updates():

    update_stock("CHAIRX", 50, "red")
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(update_stock, "CHAIRX", -1, "red") for _ in range(50)]
        for future in futures:
            future.result()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT red, quantite_actuelle FROM products WHERE reference = 'CHAIRX'")
    result = cursor.fetchone()
    conn.close()
    assert result["red"] == 0, f"Expected red 0, got {result['red']}"
    assert result["quantite_actuelle"] == 9, f"Expected quantite_actuelle 9, got {result['quantite_actuelle']}"


@pytest.fixture
def setup_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products")
    cursor.execute("""
        INSERT INTO products (reference, denomination, white, black, default_colour)
        VALUES ('TEST1', 'Test Item', 10, 5, 3)
    """)
    conn.commit()
    yield conn
    conn.rollback()
    conn.close()

def test_update_stock_color_deduction(setup_db):
    update_stock('TEST1', -3, 'white', conn=setup_db)
    cursor = setup_db.cursor()
    cursor.execute("SELECT white, quantite_actuelle FROM products WHERE reference = 'TEST1'")
    result = dict(cursor.fetchone())
    assert result['white'] == 7
    assert result['quantite_actuelle'] == 15  # 7 + 5 + 3

def test_update_stock_no_color_error(setup_db):
    with pytest.raises(ValueError, match="Specify a color for stock reduction"):
        update_stock('TEST1', -2, None, conn=setup_db)

def test_check_stock_sufficient(setup_db):
    success, msg = check_stock('TEST1', 2, 'white')
    assert success
    assert msg == "In stock"

def test_check_stock_insufficient(setup_db):
    success, msg = check_stock('TEST1', 15, 'white')
    assert not success
    assert "Only 10 units available in white" in msg