# tests/test_edit_failures.py
import pytest
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

def test_edit_nonexistent_product():
    fake_product = {
        "reference": "NON-EXISTENT-123",
        "denomination": "Test",
        "category": "Test Category"
    }
    assert not add_or_update_product(fake_product, is_update=True), "Edit should fail for non-existent product"

def test_edit_invalid_data(sample_product):
    # Setup
    add_or_update_product(sample_product)
    
    # Invalid update
    product = {
        "reference": "EDIT-TEST-001",
        "denomination": "Test",
        "category": "Test Category",
        "prix-détail": -50  # Invalid price
    }
    errors = validate_product_data(product, is_update=True)
    assert "cannot be negative" in errors[0], "Validation should catch negative price"
    
    # Cleanup
    permanently_delete("EDIT-TEST-001")