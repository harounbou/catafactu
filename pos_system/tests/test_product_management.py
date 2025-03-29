# tests/test_product_management.py
import pytest
import json
from datetime import datetime
from modules.product_management import *
from modules.utils import get_db_connection

# Placeholder for testing
def log_audit_event(username, action, reference, description):
    pass  # Mock implementation

@pytest.fixture
def test_product():
    return {
        "reference": "TEST-001",
        "denomination": "Test Product",
        "quantite_actuelle": 10.0,
        "couleurs-dispo-usine": "",
        "images": "",
        "prix-super-gros": 0.0,
        "prix-gros": 0.0,
        "prix-détail": 0.0,
        "discontinued": 0,
        "category": "Test Category"  # Add category back
    }

def test_add_product(test_product):
    errors = validate_product_data(test_product)
    assert len(errors) == 0, f"Validation failed: {errors}"  # Expect no errors with category
    
    result = add_or_update_product(test_product)
    assert result, f"add_or_update_product failed with: {result}"
    
    products = load_products()
    assert test_product['reference'] in products['reference'].values, "Product not found in DB"
    assert products[products['reference'] == test_product['reference']]['category'].values[0] == "Test Category", "Category not set correctly"
    
    permanently_delete(test_product['reference'])

def test_delete_with_transactions(test_product):
    add_or_update_product(test_product)
    
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO transactions (items)
        VALUES (?)
    """, (json.dumps([{"reference": test_product['reference']}]),))
    conn.commit()
    
    with pytest.raises(ValueError, match="Product has associated transactions"):
        permanently_delete(test_product['reference'])
    
    conn.execute("DELETE FROM transactions WHERE items LIKE ?", (f'%{test_product["reference"]}%',))
    conn.commit()
    permanently_delete(test_product['reference'])