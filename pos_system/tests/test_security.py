# tests/test_security.py
import pytest
import pandas as pd
from datetime import datetime
from modules.product_management import add_or_update_product, update_stock, permanently_delete, load_products
from modules.utils import get_db_connection
import streamlit as st

# Mock Streamlit's session_state with configurable role
class MockSessionState:
    def __init__(self, role="user"):
        self._data = {'user': {'role': role, 'username': 'test_user'}}
    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(f"'MockSessionState' object has no attribute '{key}'")
    def __getitem__(self, key):
        return self._data[key]

@pytest.fixture
def mock_streamlit(monkeypatch, request):
    """Mock streamlit.session_state with role parameter."""
    role = getattr(request, "param", "admin")  # Default to admin unless specified
    class MockStreamlit:
        session_state = MockSessionState(role=role)
        @staticmethod
        def error(msg):
            print(msg)
        @staticmethod
        def success(msg):
            print(msg)
    monkeypatch.setattr('modules.product_management.st', MockStreamlit())
    monkeypatch.setattr('modules.utils.st', MockStreamlit())
    return MockStreamlit()


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


@pytest.mark.parametrize("mock_streamlit", ["user"], indirect=True)
def test_non_admin_delete(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    with pytest.raises(ValueError, match="Only admins can permanently delete products"):
        permanently_delete(test_product["reference"])
    product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    assert product["discontinued"] == 0, "Product should not be deleted"

def test_invalid_product_data(mock_streamlit):
    invalid_product = {
        "reference": "",  # Empty reference
        "denomination": "Invalid Product",
        "quantite_actuelle": 100,
        "category": "Test",
        "prix-super-gros": -5.0  # Negative price
    }
    assert not add_or_update_product(invalid_product), "Should fail due to invalid data"
    products = load_products()
    assert len(products) == 0, "No product should be added"

def test_sql_injection(test_product, mock_streamlit):
    malicious_product = test_product.copy()
    malicious_product["reference"] = "SEC-002'; DROP TABLE products; --"
    assert not add_or_update_product(malicious_product), "Should fail or handle SQL injection safely"
    products = load_products()
    assert "SEC-002'; DROP TABLE products; --" not in products["reference"].values, "Malicious reference should not be added"
    # Verify table still exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
    assert cursor.fetchone() is not None, "Products table should still exist"
    conn.close()

@pytest.mark.parametrize("mock_streamlit", ["user"], indirect=True)
def test_unauthorized_stock_update(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    # Temporarily unset session state to simulate no user
    original_session = st.session_state
    st.session_state = None
    try:
        assert update_stock(test_product["reference"], -10), "Stock update should succeed without strict auth check"
    finally:
        st.session_state = original_session
    product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    assert product["quantite_actuelle"] == 90, "Stock should update (current logic allows it)"

def test_discontinued_product_integrity(test_product, mock_streamlit):
    assert add_or_update_product(test_product), "Failed to add product"
    conn = get_db_connection()
    conn.execute("UPDATE products SET discontinued = 1 WHERE reference = ?", (test_product["reference"],))
    conn.commit()
    conn.close()
    
    assert not update_stock(test_product["reference"], -10), "Should not update discontinued product stock"
    product = load_products(active_only=False).query(f"reference == '{test_product['reference']}'").iloc[0]
    assert product["quantite_actuelle"] == 100, "Stock should remain unchanged"