# modules/product_management.py
import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from .utils import get_db_connection, get_db_color_name, transactional_update
from io import BytesIO

# Configurable feature flag
ENABLE_PRICE_HISTORY = False  # Toggle this in a config file or environment variable

def log_audit_event(username, action, reference, description):
    """Log an audit event (placeholder implementation)."""
    pass

def add_or_update_product(product_data, is_update=False, enable_price_history=ENABLE_PRICE_HISTORY):
    conn = get_db_connection()
    try:
        ref = product_data['reference']
        errors = validate_product_data(product_data, is_update=is_update)
        if errors:
            print(f"Validation errors: {errors}")
            return False
        
        existing_df = load_products(active_only=False)
        with conn:
            cursor = conn.cursor()
            values = (
                ref,
                product_data['denomination'],
                product_data.get('quantite_initiale', 0.0),
                product_data.get('quantite_restockee', 0.0),
                product_data.get('quantite_vendue', 0),
                product_data.get('quantite_actuelle', 0),
                product_data.get('couleurs-dispo-usine', ''),
                product_data.get('images', ''),
                product_data.get('prix-super-gros', 0.0),
                product_data.get('prix-gros', 0.0),
                product_data.get('prix-détail', 0.0),
                product_data.get('red', 0),
                product_data.get('blue', 0),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                product_data.get('discontinued', 0),
                product_data.get('category', '')
            )
            
            if is_update:
                if ref not in existing_df['reference'].values:
                    print(f"Cannot update: Product {ref} does not exist!")
                    return False
                cursor.execute('''UPDATE products SET 
                    denomination=?, quantite_initiale=?, quantite_restockee=?, quantite_vendue=?, 
                    quantite_actuelle=?, `couleurs-dispo-usine`=?, images=?, `prix-super-gros`=?, 
                    `prix-gros`=?, `prix-détail`=?, red=?, blue=?, last_updated=?, discontinued=?, category=?
                    WHERE reference=?''', (*values[1:], ref))
                action = "updated"
            else:
                if ref in existing_df['reference'].values:
                    print("Reference already exists!")
                    return False
                cursor.execute('''INSERT INTO products 
                    (reference, denomination, quantite_initiale, quantite_restockee, quantite_vendue, 
                    quantite_actuelle, `couleurs-dispo-usine`, images, `prix-super-gros`, `prix-gros`, 
                    `prix-détail`, red, blue, last_updated, discontinued, category)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', values)
                action = "added"
            
            conn.commit()
        print(f"Product {action} successfully!")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error in add_or_update_product: {str(e)}")
        return False
    finally:
        conn.close()

def backup_database():
    """Create a backup of the database."""
    conn = get_db_connection()
    try:
        # Replace with actual database path or fetch from config
        db_path = "path/to/your/database.db"
        backup_path = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        import shutil
        shutil.copy2(db_path, backup_path)
        return backup_path
    except Exception as e:
        st.error(f"Backup failed: {str(e)}")
        return None
    finally:
        conn.close()

def calculate_current_quantity(product_row):
    """Calculate quantite_actuelle from color quantities."""
    color_fields = [
        'uni_colour', 'default_colour', 'brown', 'brown_deg',
        'blue', 'white', 'black', 'green_bottle', 'red', 'grey',
        'grey_deg', 'beige', 'yellow', 'orange', 'garnet',
        'golden', 'green', 'rose'
    ]
    return sum(int(product_row[col]) for col in color_fields if col in product_row and pd.notna(product_row[col]))

def load_products(active_only=True):
    """Load products from the database."""
    conn = get_db_connection()
    if conn is None:
        st.error("Debug: Failed to connect to database")
        return pd.DataFrame()
    
    query = "SELECT * FROM products WHERE discontinued = 0" if active_only else "SELECT * FROM products"
    try:
        df = pd.read_sql_query(query, conn)
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

def check_stock(reference, quantity, color=None):
    """Check stock for a specific product and color."""
    products_df = load_products()
    product = products_df[products_df['reference'] == reference]
    
    if product.empty:
        return False, "Product not found"
        
    if color:
        db_color = get_db_color_name(color)
        if db_color not in product.columns:
            return False, f"Color {color} not available"
            
        stock = product[db_color].values[0]
        if pd.isna(stock) or stock < quantity:
            return False, f"Only {stock} units available in {color}"
    else:
        stock = product['quantite_actuelle'].values[0]
        if pd.isna(stock) or stock < quantity:
            return False, f"Only {stock} units available in total"
    
    return True, "In stock"


def update_stock(reference, quantity_change, color=None):
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE reference = ? FOR UPDATE", (reference,))
            product = cursor.fetchone()
            if color:
                current = product[color] if color in product else 0
                cursor.execute(f"UPDATE products SET `{color}` = ?, last_updated = ? WHERE reference = ?",
                               (current + quantity_change, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))
            total = sum(int(product[col]) for col in product.keys() if col in ['red', 'blue', 'green'] and pd.notna(product[col]))
            cursor.execute("UPDATE products SET quantite_actuelle = ?, last_updated = ? WHERE reference = ?",
                           (total, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating stock: {str(e)}")
        return False
    finally:
        conn.close()


def restock_product(reference, quantity_to_add, color=None):
    """Restock a product with color-aware quantity updates."""
    if quantity_to_add <= 0:
        raise ValueError("Restock quantity must be positive")
        
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE reference = ?", (reference,))
            product = cursor.fetchone()
            if not product:
                raise ValueError(f"Product {reference} not found")
            
            if color and color != "total":
                color = color.lower().replace(" ", "_")
                if color not in product.keys():
                    raise ValueError(f"Invalid color {color} for product {reference}")
                
                cursor.execute(f"""
                    UPDATE products 
                    SET `{color}` = `{color}` + ?,
                        quantite_restockee = quantite_restockee + ?,
                        last_updated = ?
                    WHERE reference = ?
                """, (quantity_to_add, quantity_to_add, 
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))
            else:
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
        'reference': ['PROD001'], 'denomination': ['Sample Product'], 'quantite_actuelle': [100],
        'couleurs-dispo-usine': ['Red,Blue'], 'images': ['image1.jpg'], 
        'prix-super-gros': [5000], 'prix-gros': [7500], 'prix-détail': [10000]
    }
    output = BytesIO()
    pd.DataFrame(sample_data).to_excel(output, index=False)
    return output.getvalue()

def validate_product_data(data, is_update=False):
    """Validate product data before insertion/update."""
    errors = []
    required_fields = ['reference', 'denomination', 'category']
    for field in required_fields:
        if not data.get(field):
            errors.append(f"Field '{field}' is required")
    
    if not is_update:
        existing_refs = load_products(active_only=False)['reference'].tolist()
        if data['reference'] in existing_refs:
            errors.append("Reference must be unique")
    
    price_fields = ['prix-super-gros', 'prix-gros', 'prix-détail']
    for field in price_fields:
        if float(data.get(field, 0)) < 0:
            errors.append(f"{field} cannot be negative")
    
    return errors

def handle_product_images(reference, category, denomination, new_images, selected_color):
    """Process and store product images with proper organization."""
    image_paths = []
    base_dir = os.path.join("images", category.strip().replace(" ", "_"), denomination.strip().replace(" ", "_"))
    os.makedirs(base_dir, exist_ok=True)

    for idx, img in enumerate(new_images):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        ext = img.type.split("/")[-1]
        filename = f"{reference}_{selected_color}_{timestamp}_{idx}.{ext}"
        img_path = os.path.join(base_dir, filename)
        
        with open(img_path, "wb") as f:
            f.write(img.getbuffer())
        
        image_paths.append(img_path)
    
    return image_paths

def update_product_stock(reference):
    """Recalculate total stock from color quantities."""
    conn = get_db_connection()
    try:
        product = load_products(active_only=False).query(f"reference == '{reference}'")
        if product.empty:
            raise ValueError(f"Product {reference} not found")
        product = product.iloc[0]
        
        COLOR_STYLES = [
            'uni_colour', 'default_colour', 'brown', 'brown_deg', 'blue', 'white', 'black',
            'green_bottle', 'red', 'grey', 'grey_deg', 'beige', 'yellow', 'orange', 'garnet',
            'golden', 'green', 'rose'
        ]
        color_fields = [col for col in product.index if col in COLOR_STYLES]
        total_stock = sum(int(product[col]) for col in color_fields if pd.notna(product[col]))
        
        with conn:
            conn.execute("""
                UPDATE products 
                SET quantite_actuelle = ?
                WHERE reference = ?
            """, (total_stock, reference))
        return True
    except Exception as e:
        st.error(f"Stock update failed: {str(e)}")
        return False
    finally:
        conn.close()

@transactional_update
def permanently_delete(reference, conn=None):
    if st.session_state.user.get("role") != "admin":
        raise ValueError("Only admins can permanently delete products")
    transactions = conn.execute("SELECT COUNT(*) FROM transactions WHERE items LIKE ?", (f'%{reference}%',)).fetchone()[0]
    if transactions > 0:
        raise ValueError("Product has associated transactions")
    conn.execute("DELETE FROM price_history WHERE product_ref = ?", (reference,))
    conn.execute("DELETE FROM products WHERE reference = ?", (reference,))
    log_audit_event(st.session_state.user['username'], "DELETE", reference, "Product permanently deleted")
    return True