# tests/test_integration.py
import pytest
import pandas as pd
from datetime import datetime
from modules.product_management import add_or_update_product, mark_discontinued, permanently_delete, load_products
from modules.utils import get_db_connection

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

def record_transaction(reference, quantity, conn):
    """Simulate a transaction."""
    items = [{"reference": reference, "quantity": quantity}]
    conn.execute(
        "INSERT INTO transactions (items, status, transaction_date) VALUES (?, ?, ?)",
        (str(items), "completed", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

def test_full_product_lifecycle(test_product):
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
    assert len(transactions) > 0, "Transaction not found"
    assert mark_discontinued(test_product["reference"]), "Failed to discontinue"
    active_products = load_products(active_only=True)
    assert test_product["reference"] not in active_products["reference"].values, "Discontinued product in active list"
    with pytest.raises(ValueError, match="Product has associated transactions"):
        permanently_delete(test_product["reference"])
    conn.execute("DELETE FROM transactions WHERE items LIKE ?", (f'%{test_product["reference"]}%',))
    conn.commit()
    assert permanently_delete(test_product["reference"]), "Failed to delete after cleanup"
    conn.close()