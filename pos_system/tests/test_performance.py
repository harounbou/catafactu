# tests/test_performance.py
import datetime
import pytest
import time
from modules.product_management import add_or_update_product, load_products, permanently_delete
from modules.utils import get_db_connection

def generate_test_product(i):
    return {
        "reference": f"PERF-{i:04d}",
        "denomination": f"Performance Product {i}",
        "quantite_actuelle": 100,
        "quantite_initiale": 100,
        "quantite_restockee": 0,
        "quantite_vendue": 0,
        "couleurs-dispo-usine": "red",
        "red": 100,
        "images": "",
        "prix-super-gros": 10.0,
        "prix-gros": 15.0,
        "prix-détail": 20.0,
        "discontinued": 0,
        "category": "Test",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def test_bulk_operations():
    products = [generate_test_product(i) for i in range(1000)]
    start = time.time()
    for p in products:
        assert add_or_update_product(p), f"Failed to add {p['reference']}"
    duration = time.time() - start
    assert duration < 5.0, f"Bulk insert took {duration:.2f}s, expected < 5s"
    all_products = load_products(active_only=False)
    assert len(all_products) >= 1000, f"Expected 1000 products, got {len(all_products)}"
    conn = get_db_connection()
    for p in products:
        conn.execute("DELETE FROM products WHERE reference = ?", (p["reference"],))
    conn.commit()
    conn.close()