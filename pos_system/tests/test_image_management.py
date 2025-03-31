# tests/test_image_management.py
import pytest
import os
from io import BytesIO
from modules.product_management import add_or_update_product, permanently_delete, load_products
from modules.utils import get_db_connection

@pytest.fixture
def test_product():
    return {
        "reference": "IMG-001",
        "denomination": "Image Test Product",
        "quantite_initiale": 10.0,
        "quantite_restockee": 0.0,
        "quantite_vendue": 0,
        "quantite_actuelle": 10,
        "couleurs-dispo-usine": "red,blue",
        "images": "",
        "prix-super-gros": 0.0,
        "prix-gros": 0.0,
        "prix-détail": 0.0,
        "red": 5,
        "blue": 5,
        "category": "Test",
        "note": "Image test",
        "quantite_vendu_actue": 0,
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
                quantite_initiale REAL,
                quantite_restockee REAL,
                quantite_vendue INTEGER,
                quantite_actuelle INTEGER,
                `couleurs-dispo-usine` TEXT,
                images TEXT,
                `prix-super-gros` REAL,
                `prix-gros` REAL,
                `prix-détail` REAL,
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
                discontinued INTEGER,
                version INTEGER DEFAULT 0
            )
        """)
        conn.execute("DROP TABLE IF EXISTS transactions")
        conn.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, items TEXT, date TEXT)")
        conn.commit()
    finally:
        conn.close()

@pytest.fixture
def mock_image():
    return BytesIO(b"fake_image_data")

def test_add_product_with_image(test_product, mock_image):
    test_product["new_images"] = [mock_image]
    test_product["selected_color"] = "red"
    assert add_or_update_product(test_product), "Failed to add product with image"
    product = load_products().query("reference == 'IMG-001'").iloc[0]
    assert product["images"], "Image path should not be empty"
    assert os.path.exists(product["images"]), "Image file should exist"
    assert "red" in product["images"], "Image should be tagged with color"

def test_replace_image(test_product, mock_image):
    # Add initial product with image
    test_product["new_images"] = [BytesIO(b"initial_data")]
    assert add_or_update_product(test_product)
    old_image = load_products().query("reference == 'IMG-001'").iloc[0]["images"]
    
    # Replace image
    test_product["new_images"] = [mock_image]
    test_product["selected_color"] = "blue"
    assert add_or_update_product(test_product, is_update=True)
    product = load_products().query("reference == 'IMG-001'").iloc[0]
    assert product["images"] != old_image, "Image should be replaced"
    assert "blue" in product["images"], "New image should reflect new color"
    assert os.path.exists(product["images"]), "New image file should exist"
    assert not os.path.exists(old_image), "Old image should be deleted"

def test_delete_image(test_product, mock_image):
    # Add with image
    test_product["new_images"] = [mock_image]
    assert add_or_update_product(test_product)
    old_image = load_products().query("reference == 'IMG-001'").iloc[0]["images"]
    
    # Delete image
    test_product["delete_image"] = True
    assert add_or_update_product(test_product, is_update=True)
    product = load_products().query("reference == 'IMG-001'").iloc[0]
    assert product["images"] == "", "Image field should be empty"
    assert not os.path.exists(old_image), "Image file should be deleted"

def test_delete_product_with_images(test_product, mock_image):
    # Add with image
    test_product["new_images"] = [mock_image]
    assert add_or_update_product(test_product)
    image_path = load_products().query("reference == 'IMG-001'").iloc[0]["images"]
    
    # Delete product
    assert permanently_delete("IMG-001")
    assert not os.path.exists(os.path.dirname(image_path)), "Image folder should be deleted"
    assert load_products().query("reference == 'IMG-001'").empty, "Product should be gone"