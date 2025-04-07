#modules/product_management.py
import glob
import logging
import sys
import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from io import BytesIO
import shutil
from modules.utils import get_db_connection, get_db_color_name, COLOR_COLUMNS, DB_PATH

# Configurable feature flag
ENABLE_PRICE_HISTORY = False  # Toggle this in a config file or environment variable

def import_products_from_excel(file):
    conn = get_db_connection()
    try:
        import glob
        df = pd.read_excel(file)
        df = df.replace({pd.NA: None, 'nan': None, '': None})
        
        required_cols = ['reference', 'denomination', 'prix-super-gros', 'prix-gros', 'prix-détail']
        if not all(col in df.columns for col in required_cols):
            missing = set(required_cols) - set(df.columns)
            st.error(f"Excel file missing required columns: {', '.join(missing)}")
            return False
        
        price_cols = ['prix-super-gros', 'prix-gros', 'prix-détail', 'quantite_actuelle', 'quantite_initiale', 'quantite_restockee']
        for col in price_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(' ', '').str.replace(',', '.'), errors='coerce').fillna(0)
        
        existing_df = load_products(active_only=False)
        with conn:
            cursor = conn.cursor()
            for index, row in df.iterrows():
                ref = row['reference']
                category = (row.get('category', 'Uncategorized') or 'Uncategorized').strip().replace(" ", "_").replace("/", "_").replace("&", "_")
                denomination = (row['denomination'] or 'No_Name').strip().replace(" ", "_").replace("/", "_").replace("&", "_")

                # Auto-detect existing images
                images = []
                colors = row.get('couleurs-dispo-usine', '').split(',') if pd.notna(row.get('couleurs-dispo-usine')) else []
                for color in colors:
                    color_clean = get_db_color_name(color.strip()).upper()
                    image_pattern = os.path.join("images", category, denomination, f"{ref}_{color_clean}_*.*")
                    matching_images = glob.glob(image_pattern)
                    images.extend([os.path.relpath(img, start="images") for img in matching_images])
                
                images_str = ','.join(images) if images else ''

                # Color quantities
                quantity = float(row.get('quantite_actuelle', 0) or 0)
                color_quantities = {col: 0 for col in COLOR_COLUMNS}
                if colors:
                    color_quantities[get_db_color_name(colors[0])] = quantity
                else:
                    color_quantities['default_colour'] = quantity
                quantite_actuelle = sum(color_quantities.values())

                values = (
                    ref, row['denomination'], float(row.get('quantite_initiale', 0) or 0),
                    float(row.get('quantite_restockee', 0) or 0), 0, quantite_actuelle,
                    row.get('couleurs-dispo-usine', ''), images_str,
                    float(row['prix-super-gros'] or 0), float(row['prix-gros'] or 0), float(row['prix-détail'] or 0),
                    *[color_quantities[col] for col in COLOR_COLUMNS],
                    '', row.get('category', ''), 0,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0, 0
                )
                
                if ref in existing_df['reference'].values:
                    cursor.execute('''UPDATE products SET 
                        denomination=?, quantite_initiale=?, quantite_restockee=?, quantite_vendue=?, 
                        quantite_actuelle=?, `couleurs-dispo-usine`=?, images=?, `prix-super-gros`=?, 
                        `prix-gros`=?, `prix-détail`=?, uni_colour=?, default_colour=?, brown=?, 
                        brown_deg=?, blue=?, white=?, black=?, green_bottle=?, red=?, grey=?, 
                        grey_deg=?, beige=?, yellow=?, orange=?, garnet=?, golden=?, green=?, rose=?, 
                        note=?, category=?, quantite_vendu_actue=?, last_updated=?, discontinued=?, version=?
                        WHERE reference=?''', (*values[1:], ref))
                else:
                    cursor.execute('''INSERT INTO products 
                        (reference, denomination, quantite_initiale, quantite_restockee, quantite_vendue, 
                        quantite_actuelle, `couleurs-dispo-usine`, images, `prix-super-gros`, `prix-gros`, 
                        `prix-détail`, uni_colour, default_colour, brown, brown_deg, blue, white, black, 
                        green_bottle, red, grey, grey_deg, beige, yellow, orange, garnet, golden, green, 
                        rose, note, category, quantite_vendu_actue, last_updated, discontinued, version)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', values)
            conn.commit()
        
        st.success("Products imported successfully!")
        st.cache_data.clear()
        st.rerun()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Import failed: {str(e)}")
        return False
    finally:
        conn.close()

def update_products_schema():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Backup the database first
        backup_path = backup_database()
        if not backup_path:
            raise Exception("Backup failed, aborting schema update.")

        # Create a new table with quantite_actuelle as a generated column
        cursor.execute("""
            CREATE TABLE products_new (
                reference TEXT PRIMARY KEY,
                denomination TEXT,
                quantite_initiale REAL DEFAULT 0,
                quantite_restockee REAL DEFAULT 0,
                quantite_vendue INTEGER DEFAULT 0,
                quantite_actuelle INTEGER GENERATED ALWAYS AS (
                    MAX(0, uni_colour + default_colour + brown + brown_deg + blue + white + black +
                           green_bottle + red + grey + grey_deg + beige + yellow + orange +
                           garnet + golden + green + rose)
                ) STORED,
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
                quantite_vendu_actue INTEGER DEFAULT 0,
                last_updated TEXT,
                discontinued BOOLEAN DEFAULT 0,
                version INTEGER DEFAULT 0
            )
        """)

        # Copy data from the old table to the new one
        cursor.execute("""
            INSERT INTO products_new 
            SELECT reference, denomination, quantite_initiale, quantite_restockee, quantite_vendue,
                   `couleurs-dispo-usine`, images, `prix-super-gros`, `prix-gros`, `prix-détail`,
                   uni_colour, default_colour, brown, brown_deg, blue, white, black,
                   green_bottle, red, grey, grey_deg, beige, yellow, orange, garnet,
                   golden, green, rose, note, category, quantite_vendu_actue, last_updated,
                   discontinued, version
            FROM products
        """)

        # Drop the old table and rename the new one
        cursor.execute("DROP TABLE products")
        cursor.execute("ALTER TABLE products_new RENAME TO products")
        conn.commit()
        st.success(f"Schema updated successfully! Backup saved at {backup_path}")
    except Exception as e:
        conn.rollback()
        st.error(f"Schema update failed: {str(e)}")
    finally:
        conn.close()

def transactional_update(func):
    """Decorator to handle transactions."""
    def wrapper(*args, **kwargs):
        conn = kwargs.get("conn") or get_db_connection()
        if not conn:
            raise ValueError("No database connection")
        try:
            result = func(*args, **kwargs, conn=conn)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            if "conn" not in kwargs:
                conn.close()
    return wrapper

@transactional_update
def update_stock(reference, quantity_change, color=None, conn=None):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT quantite_actuelle FROM products WHERE reference = ?", (reference,))
        product = cursor.fetchone()
        if not product:
            raise ValueError(f"Product {reference} not found")
        
        if quantity_change < 0:  # Stock reduction
            if color:
                db_color = color.lower().replace(' ', '_')
                if db_color not in COLOR_COLUMNS:
                    raise ValueError(f"Invalid color: {color}")
            else:
                db_color = 'default_colour'  # Use default_colour if no color specified
            cursor.execute(f"SELECT {db_color} FROM products WHERE reference = ?", (reference,))
            current_stock = cursor.fetchone()[0]
            if current_stock < -quantity_change:
                raise ValueError(f"Not enough stock in {db_color}: {current_stock} available")
            new_stock = max(0, current_stock + quantity_change)
            cursor.execute(f"UPDATE products SET {db_color} = ? WHERE reference = ?", (new_stock, reference))
        else:  # Stock addition
            if color:
                db_color = color.lower().replace(' ', '_')
                if db_color not in COLOR_COLUMNS:
                    raise ValueError(f"Invalid color: {color}")
            else:
                db_color = 'default_colour'
            cursor.execute(f"UPDATE products SET {db_color} = {db_color} + ? WHERE reference = ?", (quantity_change, reference))
        
        return True
    except Exception as e:
        raise e

def handle_product_images(reference, category, denomination, new_images=None, color=None, delete_existing=False):
    """Handle images with path: images/{category}/{denomination}/{reference}_{color}_{index}.jpg"""
    category = (category or 'Uncategorized').strip().replace(" ", "_").replace("/", "_").replace("&", "_")
    denomination = (denomination or 'No_Name').strip().replace(" ", "_").replace("/", "_").replace("&", "_")
    base_dir = os.path.join("images", category, denomination)
    image_paths = []
    
    if delete_existing and os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    
    if new_images and color:
        os.makedirs(base_dir, exist_ok=True)
        color_clean = get_db_color_name(color.lower().replace(' ', '_')).upper()  # Uppercase for consistency
        
        # Handle multiple images with indexing
        for idx, img in enumerate(new_images, start=1):
            ext = os.path.splitext(img.name)[1].lower() or '.jpg'
            filename = f"{reference}_{color_clean}_{idx}{ext}"  # e.g., RT0032_RED_1.jpg
            dest_path = os.path.join(base_dir, filename)
            
            # Skip if file exists unless delete_existing is True
            if os.path.exists(dest_path) and not delete_existing:
                st.warning(f"Image {filename} already exists. Skipping to avoid overwrite.")
                image_paths.append(dest_path)
            else:
                with open(dest_path, "wb") as f:
                    if hasattr(img, "read"):
                        f.write(img.read())
                    else:
                        f.write(img.getbuffer())
                image_paths.append(dest_path)
    
    # If no new images, return existing paths for the specified color
    if not new_images and color:
        color_clean = get_db_color_name(color.lower().replace(' ', '_')).upper()
        image_pattern = os.path.join(base_dir, f"{reference}_{color_clean}_*.*")
        existing_images = glob.glob(image_pattern)
        image_paths.extend(existing_images)
    
    return ','.join(image_paths) if image_paths else ''

@transactional_update
def add_or_update_product(product_data, is_update=False, enable_price_history=False, conn=None):
    cursor = conn.cursor()
    try:
        ref = product_data['reference']
        errors = validate_product_data(product_data, is_update=is_update)
        if errors:
            print(f"Validation errors: {errors}")
            return False
        
        existing_df = load_products(active_only=False)
        color_fields = COLOR_COLUMNS

        # Handle images
        new_images = product_data.get('new_images')
        selected_color = product_data.get('selected_color', 'default')
        delete_image = product_data.get('delete_image', False)
        images = handle_product_images(
            ref, product_data['category'], product_data['denomination'],
            new_images, selected_color, delete_image
        ) if new_images or delete_image else product_data.get('images', '')

        # Prepare values, including quantite_actuelle
        quantite_actuelle = sum(product_data.get(col, 0) for col in color_fields)
        values = (
            ref, product_data['denomination'], product_data.get('quantite_initiale', 0.0),
            product_data.get('quantite_restockee', 0.0), product_data.get('quantite_vendue', 0),
            quantite_actuelle, product_data.get('couleurs-dispo-usine', ''), images,
            product_data.get('prix-super-gros', 0.0), product_data.get('prix-gros', 0.0),
            product_data.get('prix-détail', 0.0), *[product_data.get(col, 0) for col in color_fields],
            product_data.get('note', ''), product_data['category'], product_data.get('quantite_vendu_actue', 0),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product_data.get('discontinued', 0),
            product_data.get('version', 0)
        )
        
        if is_update:
            if ref not in existing_df['reference'].values:
                print(f"Cannot update: Product {ref} does not exist!")
                return False
            cursor.execute('''UPDATE products SET 
                denomination=?, quantite_initiale=?, quantite_restockee=?, quantite_vendue=?, 
                quantite_actuelle=?, `couleurs-dispo-usine`=?, images=?, `prix-super-gros`=?, 
                `prix-gros`=?, `prix-détail`=?, uni_colour=?, default_colour=?, brown=?, 
                brown_deg=?, blue=?, white=?, black=?, green_bottle=?, red=?, grey=?, 
                grey_deg=?, beige=?, yellow=?, orange=?, garnet=?, golden=?, green=?, rose=?, 
                note=?, category=?, quantite_vendu_actue=?, last_updated=?, discontinued=?, version=?
                WHERE reference=?''', (*values[1:], ref))
            action = "updated"
        else:
            if ref in existing_df['reference'].values:
                print("Reference already exists!")
                return False
            cursor.execute('''INSERT INTO products 
                (reference, denomination, quantite_initiale, quantite_restockee, quantite_vendue, 
                quantite_actuelle, `couleurs-dispo-usine`, images, `prix-super-gros`, `prix-gros`, 
                `prix-détail`, uni_colour, default_colour, brown, brown_deg, blue, white, black, 
                green_bottle, red, grey, grey_deg, beige, yellow, orange, garnet, golden, green, 
                rose, note, category, quantite_vendu_actue, last_updated, discontinued, version)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', values)
            action = "added"
        
        print(f"Product {action} successfully!")
        return True
    except Exception as e:
        print(f"Error in add_or_update_product: {str(e)}")
        return False

def log_audit_event(username, action, reference, description):
    """Log an audit event (placeholder implementation)."""
    pass

def backup_database():
    conn = get_db_connection()
    try:
        backup_path = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(DB_PATH, backup_path)
        return backup_path
    except Exception as e:
        st.error(f"Backup failed: {str(e)}")
        return None
    finally:
        conn.close()

def calculate_current_quantity(product_row):
    """Calculate quantite_actuelle from color quantities."""
    return sum(int(product_row[col]) for col in COLOR_COLUMNS if col in product_row and pd.notna(product_row[col]))

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

def mark_discontinued(reference):
    """Mark a product as discontinued."""
    conn = get_db_connection()
    if conn is None:
        print("Failed to connect to database in mark_discontinued")
        return False
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE products SET discontinued=1, last_updated=? WHERE reference=?", 
                           (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))
            if cursor.rowcount == 0:
                print(f"No product found with reference {reference}")
                return False
            conn.commit()
        print("Product marked as discontinued!")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error in mark_discontinued: {str(e)}")
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
                if color not in COLOR_COLUMNS:
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
    """Generate a sample Excel template without images column."""
    sample_data = {
        'reference': ['PROD001'],
        'denomination': ['Sample Product'],
        'category': ['CHAIR'],
        'couleurs-dispo-usine': ['Red,Blue'],
        'quantite_actuelle': [100],
        'prix-super-gros': [5000],
        'prix-gros': [7500],
        'prix-détail': [10000]
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

@transactional_update
def permanently_delete(reference, conn=None):
    try:
        cursor = conn.cursor()
        product = load_products(active_only=False).query(f"reference == '{reference}'")
        if product.empty:
            raise ValueError("Product not found")

        transactions = conn.execute("SELECT COUNT(*) FROM transactions WHERE items LIKE ?", (f'%{reference}%',)).fetchone()[0]
        if transactions > 0:
            raise ValueError("Product has associated transactions and cannot be deleted")

        cursor.execute("DELETE FROM products WHERE reference = ?", (reference,))
        return True
    except Exception as e:
        st.error(f"Deletion failed: {str(e)}")
        return False

def update_product_stock(reference):
    """Recalculate total stock from color quantities."""
    conn = get_db_connection()
    try:
        product = load_products(active_only=False).query(f"reference == '{reference}'")
        if product.empty:
            raise ValueError(f"Product {reference} not found")
        product = product.iloc[0]
        
        total_stock = sum(int(product[col]) for col in COLOR_COLUMNS if pd.notna(product[col]))
        
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