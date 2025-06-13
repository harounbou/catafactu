# modules/product_management.py
import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from .utils import get_db_connection
from .utils import get_db_color_name  # <-- KEY FIX


# Configurable feature flag
ENABLE_PRICE_HISTORY = False  # Toggle this in a config file or environment variable

def backup_database():
    """Create a backup of the database."""
    from .utils import DB_PATH
    conn = get_db_connection()
    try:
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite")
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        return backup_path
    except Exception as e:
        st.error(f"Backup failed: {str(e)}")
        return None
    finally:
        conn.close()
    
def calculate_current_quantity(product_row):
    """Calculate quantite_actuelle from color quantities"""
    color_fields = [
        'uni_colour', 'default_colour', 'brown', 'brown_deg',
        'blue', 'white', 'black', 'green_bottle', 'red', 'grey',
        'grey_deg', 'beige', 'yellow', 'orange', 'garnet',
        'golden', 'green', 'rose'
    ]
    return sum(int(product_row[col]) for col in color_fields if col in product_row)

def load_products(active_only=True):
    conn = get_db_connection()
    if conn is None:
        st.error("Debug: Failed to connect to database")
        return pd.DataFrame()
    
    query = "SELECT * FROM products WHERE discontinued = 0" if active_only else "SELECT * FROM products"
    #st.write(f"Debug: Executing query: {query}")  # Log query
    try:
        df = pd.read_sql_query(query, conn)
        #st.write(f"Debug: Raw data from DB: {df.shape}")  # Log shape of data
    except Exception as e:
        st.error(f"Debug: Error loading products: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def import_products_from_excel(file):
    """Handle Excel import with updates and inserts."""
    conn = get_db_connection()
    try:
        df = pd.read_excel(file).astype(str).replace({'nan': None})
        required_cols = ['reference', 'denomination', 'quantite_actuelle', 'prix-super-gros', 'prix-gros', 'prix-détail']
        if not all(col in df.columns for col in required_cols):
            st.error("Excel file missing required columns!")
            return False
        
        existing_df = load_products(active_only=False)
        missing_images = []
        with conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                ref = row['reference']
                images = row.get('images', '')
                if images:
                    image_list = [img.strip() for img in images.split(',')]
                    valid_images = []
                    for img in image_list:
                        img_path = img if os.path.isabs(img) else os.path.join("images", img)
                        if os.path.exists(img_path):
                            valid_images.append(img_path)
                        else:
                            missing_images.append(img)
                    images = ','.join(valid_images) if valid_images else ''
                
                values = (
                    ref, row['denomination'], float(row['quantite_actuelle'] or 0),
                    row.get('couleurs-dispo-usine', ''), images,
                    float(row['prix-super-gros'] or 0), float(row['prix-gros'] or 0), float(row['prix-détail'] or 0),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0
                )
                
                if ref in existing_df['reference'].values:
                    cursor.execute('''UPDATE products SET denomination=?, quantite_actuelle=?, 
                                    `couleurs-dispo-usine`=?, images=?, `prix-super-gros`=?, 
                                    `prix-gros`=?, `prix-détail`=?, last_updated=?, discontinued=?
                                    WHERE reference=?''', (*values[1:], ref))
                else:
                    cursor.execute('''INSERT INTO products 
                                    (reference, denomination, quantite_actuelle, `couleurs-dispo-usine`, 
                                    images, `prix-super-gros`, `prix-gros`, `prix-détail`, last_updated, discontinued)
                                    VALUES (?,?,?,?,?,?,?,?,?,?)''', values)
                
                if ENABLE_PRICE_HISTORY:
                    for price_type, value in [('super_gros', row['prix-super-gros']), ('gros', row['prix-gros']), ('detail', row['prix-détail'])]:
                        if value:
                            cursor.execute('''INSERT INTO price_history 
                                            (product_ref, price_type, old_price, new_price, changed_at)
                                            VALUES (?, ?, ?, ?, ?)''', 
                                            (ref, price_type, None, float(value), datetime.now()))
            conn.commit()
        
        st.success("Products imported successfully!")
        if missing_images:
            st.warning(f"Some images were not found and skipped: {', '.join(set(missing_images))}")
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Import failed: {str(e)}")
        return False
    finally:
        conn.close()

def add_or_update_product(product_data, is_update=False):
    """Add or update a product with image handling."""
    conn = get_db_connection()
    try:
        ref = product_data['reference']
        existing_df = load_products(active_only=False)
        with conn:
            cursor = conn.cursor()
            values = (
                ref, product_data['denomination'], product_data['quantite_actuelle'],
                product_data['couleurs-dispo-usine'], product_data['images'],
                product_data['prix-super-gros'], product_data['prix-gros'], product_data['prix-détail'],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0
            )
            
            if is_update and ref in existing_df['reference'].values:
                cursor.execute('''UPDATE products SET denomination=?, quantite_actuelle=?, 
                                `couleurs-dispo-usine`=?, images=?, `prix-super-gros`=?, 
                                `prix-gros`=?, `prix-détail`=?, last_updated=?, discontinued=?
                                WHERE reference=?''', (*values[1:], ref))
                action = "updated"
            else:
                if ref in existing_df['reference'].values:
                    st.error("Reference already exists!")
                    return False
                cursor.execute('''INSERT INTO products 
                                (reference, denomination, quantite_actuelle, `couleurs-dispo-usine`, 
                                images, `prix-super-gros`, `prix-gros`, `prix-détail`, last_updated, discontinued)
                                VALUES (?,?,?,?,?,?,?,?,?,?)''', values)
                action = "added"
            
            if ENABLE_PRICE_HISTORY and is_update:
                old_product = existing_df[existing_df['reference'] == ref].iloc[0]
                for price_type, new_val, old_val in [
                    ('super_gros', product_data['prix-super-gros'], old_product['prix-super-gros']),
                    ('gros', product_data['prix-gros'], old_product['prix-gros']),
                    ('detail', product_data['prix-détail'], old_product['prix-détail'])
                ]:
                    if new_val != old_val:
                        cursor.execute('''INSERT INTO price_history 
                                        (product_ref, price_type, old_price, new_price, changed_at)
                                        VALUES (?, ?, ?, ?, ?)''', 
                                        (ref, price_type, old_val, new_val, datetime.now()))
            conn.commit()
        st.success(f"Product {action} successfully!")
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error: {str(e)}")
        return False
    finally:
        conn.close()

def mark_discontinued(reference):
    """Mark a product as discontinued."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE products SET discontinued=1, last_updated=? WHERE reference=?", 
                         (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))
        st.success("Product marked as discontinued!")
        return True
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False
    finally:
        conn.close()

def permanently_delete(reference):
    """Permanently delete a discontinued product (admin only)."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM products WHERE reference=? AND discontinued=1", (reference,))
        st.success("Product permanently deleted!")
        return True
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False
    finally:
        conn.close()

# modules/product_management.py
def check_stock(reference, quantity, color=None):
    """Check stock for a specific product and color"""
    products_df = load_products()
    product = products_df[products_df['reference'] == reference]
    
    if product.empty:
        return False, "Product not found"
        
    if color:
        # Get database column name for the color
        db_color = get_db_color_name(color)
        if db_color not in product.columns:
            return False, f"Color {color} not available"
            
        stock = product[db_color].values[0]
        if pd.isna(stock) or stock < quantity:
            return False, f"Only {stock} units available in {color}"
    else:
        # Check total stock if no color specified
        stock = product['quantite_actuelle'].values[0]
        if pd.isna(stock) or stock < quantity:
            return False, f"Only {stock} units available in total"
    
    return True, "In stock"

def update_stock(reference, quantity_change, color=None):
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            if color:
                cursor.execute(f"""
                    UPDATE products 
                    SET `{color}` = `{color}` + ?, 
                        last_updated = ? 
                    WHERE reference = ?
                """, (quantity_change, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))

            # Calculate new total quantity from all colors
            cursor.execute("SELECT * FROM products WHERE reference = ?", (reference,))
            product = cursor.fetchone()
            colors = [c.strip().lower() for c in product['couleurs-dispo-usine'].split(',')] if product['couleurs-dispo-usine'] else []
            total = sum(int(product[color]) for color in colors if color in product)

            cursor.execute("""
                UPDATE products 
                SET quantite_actuelle = ?, 
                    last_updated = ? 
                WHERE reference = ?
            """, (total, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))
            
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error updating stock: {str(e)}")
        return False
    finally:
        conn.close()

def restock_product(reference, quantity_to_add, color=None):
    """Restock a product with color-aware quantity updates"""
    if quantity_to_add <= 0:
        raise ValueError("Restock quantity must be positive")
        
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            
            # Get current values for validation
            cursor.execute("SELECT * FROM products WHERE reference = ?", (reference,))
            product = cursor.fetchone()
            if not product:
                raise ValueError(f"Product {reference} not found")
            
            # Validate color exists if specified
            if color and color != "total":
                color = color.lower().replace(" ", "_")
                if color not in product.keys():
                    raise ValueError(f"Invalid color {color} for product {reference}")
                
                # Update color-specific quantity
                cursor.execute(f"""
                    UPDATE products 
                    SET `{color}` = `{color}` + ?,
                        quantite_restockee = quantite_restockee + ?,
                        last_updated = ?
                    WHERE reference = ?
                """, (quantity_to_add, quantity_to_add, 
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))
            else:
                # Update general restock quantity
                cursor.execute("""
                    UPDATE products 
                    SET quantite_restockee = quantite_restockee + ?,
                        last_updated = ?
                    WHERE reference = ?
                """, (quantity_to_add, 
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))
            
            conn.commit()
            return True
            
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"Database error during restock: {str(e)}")
        return False
    finally:
        conn.close()

def generate_excel_template():
    """Generate a sample Excel template."""
    sample_data = {
        'reference': ['REF001', 'REF002'],
        'denomination': ['Product 1', 'Product 2'],
        'prix-super-gros': [1000, 2000],
        'prix-gros': [1200, 2200],
        'prix-détail': [1500, 2500],
        'couleurs-dispo-usine': ['Red,Blue', 'Green,Black'],
        'note': ['Sample note', '']
    }
    return pd.DataFrame(sample_data)

def backup_products(backup_dir='backups'):
    """
    Create a backup of the products table.
    
    Args:
        backup_dir (str): Directory to store the backup file
        
    Returns:
        str: Path to the backup file or None if backup failed
    """
    import os
    import json
    from datetime import datetime
    
    try:
        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create a timestamp for the backup file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'products_backup_{timestamp}.json')
        
        # Get current products data
        conn = get_db_connection()
        products_df = pd.read_sql_query('SELECT * FROM products', conn)
        
        # Convert to dictionary and save as JSON
        products_data = products_df.to_dict(orient='records')
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'count': len(products_data),
                'data': products_data
            }, f, ensure_ascii=False, indent=2, default=str)
            
        return backup_file
    except Exception as e:
        print(f"Error creating products backup: {e}")
        return None

def get_product_categories():
    """
    Retrieve a list of unique product categories from the database.
    
    Returns:
        list: A list of unique category names
    """
    conn = get_db_connection()
    try:
        query = "SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != ''"
        categories_df = pd.read_sql_query(query, conn)
        return sorted(categories_df['category'].dropna().unique().tolist())
    except Exception as e:
        print(f"Error retrieving product categories: {e}")
        return []
    finally:
        conn.close()