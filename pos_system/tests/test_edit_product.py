# tests/test_edit_product.py
import pytest
from datetime import datetime
from modules.product_management import *
from modules.utils import get_db_connection

@pytest.fixture
def sample_product():
    return {
        "reference": "EDIT-TEST-001",
        "denomination": "Original Name",
        "category": "Test Category",
        "quantite_actuelle": 100.0,
        "couleurs-dispo-usine": "",
        "images": "",
        "prix-super-gros": 0.0,
        "prix-gros": 0.0,
        "prix-détail": 50.0,
        "discontinued": 0
    }

def test_product_edit_basic(sample_product):
    # Setup
    add_or_update_product(sample_product)
    
    # Edit values
    updates = {
        "reference": "EDIT-TEST-001",
        "denomination": "Updated Name",
        "quantite_actuelle": 150.0,
        "couleurs-dispo-usine": "",
        "images": "",
        "prix-super-gros": 0.0,
        "prix-gros": 0.0,
        "prix-détail": 75.0,
        "discontinued": 0,
        "category": "Test Category"
    }
    
    # Execute edit
    assert add_or_update_product(updates, is_update=True), "Edit failed"
    
    # Verify
    updated_product = load_products().query("reference == 'EDIT-TEST-001'").iloc[0]
    assert updated_product['denomination'] == "Updated Name"
    assert updated_product['prix-détail'] == 75.0
    assert updated_product['quantite_actuelle'] == 150.0
    
    # Cleanup
    permanently_delete("EDIT-TEST-001")

def test_edit_with_images(sample_product):
    # Setup
    add_or_update_product(sample_product)
    
    # Simulate image update
    test_images = ["image1.jpg", "image2.jpg"]
    updates = {
        "reference": "EDIT-TEST-001",
        "denomination": "Original Name",
        "quantite_actuelle": 100.0,
        "couleurs-dispo-usine": "",
        "images": ",".join(test_images),
        "prix-super-gros": 0.0,
        "prix-gros": 0.0,
        "prix-détail": 50.0,
        "discontinued": 0,
        "category": "Test Category"
    }
    
    assert add_or_update_product(updates, is_update=True), "Image edit failed"
    
    # Verify
    updated = load_products().query("reference == 'EDIT-TEST-001'").iloc[0]
    assert updated['images'] == "image1.jpg,image2.jpg"
    
    # Cleanup
    permanently_delete("EDIT-TEST-001")

def test_edit_with_price_history(sample_product):
    # Setup
    add_or_update_product(sample_product)
    
    # Edit with price change
    updates = {
        "reference": "EDIT-TEST-001",
        "denomination": "Original Name",
        "quantite_actuelle": 100.0,
        "couleurs-dispo-usine": "",
        "images": "",
        "prix-super-gros": 10.0,  # Change from 0.0
        "prix-gros": 0.0,
        "prix-détail": 75.0,  # Change from 50.0
        "discontinued": 0,
        "category": "Test Category"
    }
    
    assert add_or_update_product(updates, is_update=True, enable_price_history=True), "Price edit failed"
    
    # Verify price history
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM price_history WHERE product_ref = ?", ("EDIT-TEST-001",))
    history = cursor.fetchall()
    assert len(history) >= 2, "Price history not recorded"
    conn.close()
    
    # Cleanup
    permanently_delete("EDIT-TEST-001")