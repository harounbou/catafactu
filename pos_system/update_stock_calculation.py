#!/usr/bin/env python3
# Script to update stock calculations for all products

import sqlite3
import os
import sys
from datetime import datetime

# Get the absolute path to the project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "pos_system.db")

def get_db_connection():
    """Establish a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection failed: {e}")
        return None

def update_stock_calculations():
    """Update quantite_actuelle for all products based on color quantities."""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        return False
    
    try:
        # Get all products
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        
        updated_count = 0
        for product in products:
            # Calculate total from color quantities
            color_fields = [
                'uni_colour', 'default_colour', 'brown', 'brown_deg',
                'blue', 'white', 'black', 'green_bottle', 'red', 'grey',
                'grey_deg', 'beige', 'yellow', 'orange', 'garnet',
                'golden', 'green', 'rose'
            ]
            
            total = 0
            for color in color_fields:
                if color in product.keys() and product[color] is not None:
                    try:
                        total += int(product[color])
                    except (ValueError, TypeError):
                        # Skip if value can't be converted to int
                        pass
            
            # Update the product's quantite_actuelle
            cursor.execute("""
                UPDATE products 
                SET quantite_actuelle = ?, 
                    last_updated = ? 
                WHERE reference = ?
            """, (total, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product['reference']))
            updated_count += 1
        
        conn.commit()
        print(f"Successfully updated stock calculations for {updated_count} products.")
        return True
    
    except Exception as e:
        conn.rollback()
        print(f"Error updating stock calculations: {e}")
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting stock calculation update...")
    success = update_stock_calculations()
    if success:
        print("Stock calculation update completed successfully.")
    else:
        print("Stock calculation update failed.")
        sys.exit(1)