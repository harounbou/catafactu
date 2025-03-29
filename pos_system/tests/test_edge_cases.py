# tests/test_edge_cases.py
import datetime
import pandas as pd
import pytest
from modules.product_management import add_or_update_product, validate_product_data, permanently_delete
from modules.utils import get_db_connection

def test_boundary_values():
    test_product = {
        "reference": "A" * 255,
        "denomination": "X" * 1000,
        "quantite_actuelle": 9999999,
        "quantite_initiale": 9999999,
        "quantite_restockee": 0,
        "quantite_vendue": 0,
        "couleurs-dispo-usine": "red",
        "red": 9999999,
        "images": "",
        "prix-super-gros": 999999.0,
        "prix-gros": 9999999.0,
        "prix-détail": 99999999.0,
        "discontinued": 0,
        "category": "Test",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    errors = validate_product_data(test_product)
    assert len(errors) == 0, f"Validation failed: {errors}"
    assert add_or_update_product(test_product), "Failed to add product"
    permanently_delete(test_product["reference"])

def test_special_characters():
    test_product = {
        "reference": "PROD-🤖",
        "denomination": "Product & Co ©®™",
        "quantite_actuelle": 10,
        "quantite_initiale": 10,
        "quantite_restockee": 0,
        "quantite_vendue": 0,
        "couleurs-dispo-usine": "red",
        "red": 10,
        "images": "",
        "prix-super-gros": 0.0,
        "prix-gros": 0.0,
        "prix-détail": 50.0,
        "discontinued": 0,
        "category": "Test",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    errors = validate_product_data(test_product)
    assert len(errors) == 0, f"Validation failed: {errors}"
    assert add_or_update_product(test_product), "Failed to add product"
    conn = get_db_connection()
    product = pd.read_sql_query("SELECT * FROM products WHERE reference = ?", conn, params=(test_product["reference"],))
    assert product["denomination"].iloc[0] == "Product & Co ©®™", "Special characters not preserved"
    permanently_delete(test_product["reference"])
    conn.close()