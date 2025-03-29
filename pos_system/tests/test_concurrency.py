# tests/test_concurrency.py
import datetime
import pytest
from concurrent.futures import ThreadPoolExecutor
from modules.product_management import add_or_update_product, update_stock, load_products
from modules.utils import get_db_connection

@pytest.fixture
def test_product():
    return {
        "reference": "CONCUR-001",
        "denomination": "Concurrency Test Product",
        "quantite_actuelle": 100,
        "quantite_initiale": 100,
        "quantite_restockee": 0,
        "quantite_vendue": 0,
        "couleurs-dispo-usine": "red",
        "red": 100,
        "images": "",
        "prix-super-gros": 0.0,
        "prix-gros": 0.0,
        "prix-détail": 0.0,
        "discontinued": 0,
        "category": "Test",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def edit_worker(reference, color, quantity_change):
    assert update_stock(reference, quantity_change, color=color), f"Worker failed for {reference}"

def test_concurrent_edits(test_product):
    assert add_or_update_product(test_product), "Failed to add product"
    initial_qty = 100
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(edit_worker, test_product["reference"], "red", -1) for _ in range(10)]
        for future in futures:
            future.result()
    final_product = load_products().query(f"reference == '{test_product['reference']}'").iloc[0]
    assert final_product["red"] == initial_qty - 10, f"Expected red {initial_qty - 10}, got {final_product['red']}"
    assert final_product["quantite_actuelle"] == initial_qty - 10, f"Expected total {initial_qty - 10}, got {final_product['quantite_actuelle']}"
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE reference = ?", (test_product["reference"],))
    conn.commit()
    conn.close()