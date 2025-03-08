import pandas as pd
import sqlite3
import json

DB_PATH = "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_products():
    conn = get_db_connection()
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return products_df

def update_stock(products_df, items):
    conn = get_db_connection()
    c = conn.cursor()
    for item in items:
        reference = item['reference']
        quantity = item['Quantity']
        color = item.get('Color')
        c.execute("SELECT quantite_actuelle, golden, white, black FROM products WHERE reference = ?", (reference,))
        row = c.fetchone()
        if row:
            current_stock = row['quantite_actuelle']
            new_stock = current_stock - quantity
            color_lower = color.lower() if color else None
            if color_lower in ['golden', 'white', 'black']:
                current_color_stock = row[color_lower]
                new_color_stock = current_color_stock - quantity
                c.execute(f"UPDATE products SET quantite_actuelle = ?, {color_lower} = ? WHERE reference = ?",
                          (new_stock, new_color_stock, reference))
            else:
                c.execute("UPDATE products SET quantite_actuelle = ? WHERE reference = ?",
                          (new_stock, reference))
    conn.commit()
    conn.close()
    return True

def restock_product(products_df, reference, quantity, cost_per_unit, color=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT quantite_actuelle, golden, white, black FROM products WHERE reference = ?", (reference,))
    row = c.fetchone()
    if row:
        current_stock = row['quantite_actuelle']
        new_stock = current_stock + quantity
        if color:
            color_lower = color.lower()
            if color_lower in ['golden', 'white', 'black']:
                current_color_stock = row[color_lower]
                new_color_stock = current_color_stock + quantity
                c.execute(f"UPDATE products SET quantite_actuelle = ?, {color_lower} = ? WHERE reference = ?",
                          (new_stock, new_color_stock, reference))
            else:
                c.execute("UPDATE products SET quantite_actuelle = ? WHERE reference = ?",
                          (new_stock, reference))
        else:
            c.execute("UPDATE products SET quantite_actuelle = ? WHERE reference = ?",
                      (new_stock, reference))
    total_cost = quantity * cost_per_unit
    conn.commit()
    conn.close()
    return total_cost