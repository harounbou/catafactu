# modules/product_management.py
import pandas as pd
import sqlite3
import streamlit as st
from .utils import get_db_connection

def load_products():
    """Load products with caching and refresh on update"""
    conn = get_db_connection()
    try:
        return pd.read_sql_query("SELECT * FROM products", conn)
    finally:
        conn.close()

def update_stock(items):
    """Update stock levels after sale with transaction safety"""
    conn = get_db_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        for item in items:
            cursor = conn.execute("""
                SELECT quantite_actuelle, golden, white, black 
                FROM products 
                WHERE reference = ?
            """, (item['reference'],))
            product = cursor.fetchone()
            if not product:
                raise ValueError(f"Product {item['reference']} not found")
            current_stock = product['quantite_actuelle']
            quantity = item['Quantity']
            color = item.get('Color', '').lower()
            available = current_stock
            if color in ['golden', 'white', 'black']:
                available = product[color]
                if available < quantity:
                    raise ValueError(f"Insufficient {color} stock for {item['reference']}")
                conn.execute(f"""
                    UPDATE products 
                    SET {color} = {color} - ?, 
                        quantite_actuelle = quantite_actuelle - ?
                    WHERE reference = ?
                """, (quantity, quantity, item['reference']))
            else:
                if current_stock < quantity:
                    raise ValueError(f"Insufficient total stock for {item['reference']}")
                conn.execute("""
                    UPDATE products 
                    SET quantite_actuelle = quantite_actuelle - ? 
                    WHERE reference = ?
                """, (quantity, item['reference']))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Stock update failed: {str(e)}")
        return False
    finally:
        conn.close()


    """Restock items with dynamic color support, return quantity restocked"""
    conn = get_db_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        if color:
            color_col = color.lower().strip()
            cursor = conn.execute("PRAGMA table_info(products)")
            columns = [row[1].lower() for row in cursor.fetchall()]
            if color_col in columns:
                conn.execute(f"""
                    UPDATE products 
                    SET {color_col} = {color_col} + ?, 
                        quantite_actuelle = quantite_actuelle + ?
                    WHERE reference = ?
                """, (quantity, quantity, reference))
            else:
                conn.execute("""
                    UPDATE products 
                    SET quantite_actuelle = quantite_actuelle + ?
                    WHERE reference = ?
                """, (quantity, reference))
        else:
            conn.execute("""
                UPDATE products 
                SET quantite_actuelle = quantite_actuelle + ?
                WHERE reference = ?
            """, (quantity, reference))
        conn.commit()
        return quantity  # Return quantity restocked
    except Exception as e:
        conn.rollback()
        st.error(f"Restock failed: {str(e)}")
        return 0
    finally:
        conn.close()

def restock_product(products_df, reference, quantity, total_cost=0, color=None):
    """Restock items with dynamic color support, return quantity restocked"""
    conn = get_db_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        if color:
            color_col = color.lower().strip()
            # Check if the color column exists; if not, only update quantite_actuelle
            cursor = conn.execute("PRAGMA table_info(products)")
            columns = [row[1].lower() for row in cursor.fetchall()]
            if color_col in columns:
                conn.execute(f"""
                    UPDATE products 
                    SET {color_col} = {color_col} + ?, 
                        quantite_actuelle = quantite_actuelle + ?
                    WHERE reference = ?
                """, (quantity, quantity, reference))
            else:
                conn.execute("""
                    UPDATE products 
                    SET quantite_actuelle = quantite_actuelle + ?
                    WHERE reference = ?
                """, (quantity, reference))
        else:
            conn.execute("""
                UPDATE products 
                SET quantite_actuelle = quantite_actuelle + ?
                WHERE reference = ?
            """, (quantity, reference))
        conn.commit()
        return quantity
    except Exception as e:
        conn.rollback()
        st.error(f"Restock failed: {str(e)}")
        return 0
    finally:
        conn.close()

def reserve_stock(items):
    """Reserve stock for proforma invoices"""
    conn = get_db_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        for item in items:
            conn.execute("""
                UPDATE products 
                SET reserved_stock = reserved_stock + ?, 
                    quantite_actuelle = quantite_actuelle - ?
                WHERE reference = ? 
                AND quantite_actuelle >= ?
            """, (item['Quantity'], item['Quantity'], item['reference'], item['Quantity']))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Stock reservation failed: {str(e)}")
        return False
    finally:
        conn.close()