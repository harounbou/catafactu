# modules/utils.py

import datetime
import shutil
import sqlite3
import os
import re
from PIL import Image
import streamlit as st
import pandas as pd

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_REGEX = r'^\d{10}$'

COLOR_STYLES = {
    'uni_colour': '#f5f5f5',
    'default_colour': '#e0e0e0',
    'brown': '#d7ccc8',
    'brown_deg': '#d7ccc8',
    'blue': '#bbdefb',
    'white': '#ffffff',
    'black': '#b0bec5',
    'green_bottle': '#c8e6c9',
    'red': '#ffcdd2',
    'grey': '#cfd8dc',
    'grey_deg': '#cfd8dc',
    'beige': '#d2b48c',
    'yellow': '#fff9c4',
    'orange': '#ffe0b2',
    'garnet': '#ffccbc',
    'golden': '#fff3e0',
    'green': '#c8e6c9',
    'rose': '#f8bbd0'
}

COLOR_COLUMNS = [
    "uni_colour", "default_colour", "brown", "brown_deg", "blue", "white", "black",
    "green_bottle", "red", "grey", "grey_deg", "beige", "yellow", "orange", "garnet",
    "golden", "green", "rose"
]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "test_pos_system.db" if os.environ.get("TESTING") == "1" else "pos_system.db")



COLOR_MAPPING = {
    # Gradient handling
    'brown_gradient': 'brown_deg',
    'grey_gradient': 'grey_deg',
    'gradient_brown': 'brown_deg',
    'gradient_grey': 'grey_deg',
    
    # Standard colors
    'brown': 'brown',
    'blue': 'blue',
    'white': 'white',
    'black': 'black',
    'green_bottle': 'green_bottle',
    'red': 'red',
    'grey': 'grey',
    'beige': 'beige',
    'yellow': 'yellow',
    'orange': 'orange',
    'garnet': 'garnet',
    'golden': 'golden',
    'green': 'green',
    'rose': 'rose'
}

def get_db_color_name(color):
    """Convert display color names to database columns"""
    if not color or pd.isna(color):
        return 'default_colour'
        
    cleaned = color.strip().lower().replace(' ', '_').replace('-', '_')
    
    # Special cases first
    if cleaned in ['brown_gradient', 'brown_grad']:
        return 'brown_deg'
    if cleaned in ['grey_gradient', 'gray_gradient']:
        return 'grey_deg'
        
    # Return mapped value or original
    return COLOR_MAPPING.get(cleaned, cleaned)

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection failed: {e}")
        return None

def check_stock(reference, quantity, color=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if color:
            db_color = get_db_color_name(color)
            cursor.execute(f"SELECT {db_color}, quantite_actuelle FROM products WHERE reference = ?", (reference,))
            result = cursor.fetchone()
            if not result:
                return False, "Product not found"
            stock = result[db_color]
            if stock < quantity:
                return False, f"Only {stock} units available in {color}"
        else:
            cursor.execute("SELECT quantite_actuelle FROM products WHERE reference = ?", (reference,))
            result = cursor.fetchone()
            if not result:
                return False, "Product not found"
            stock = result['quantite_actuelle']
            if stock < quantity:
                return False, f"Only {stock} units available in total"
        return True, "In stock"
    finally:
        conn.close()

def fetch_df_from_db(table_name):
    """Fetch data from a table as a pandas DataFrame."""
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()
            return df
        except sqlite3.Error as e:
            st.error(f"Failed to fetch data from {table_name}: {e}")
            conn.close()
            return pd.DataFrame()
    return pd.DataFrame()

def save_df_to_db(df, table_name):
    """Save a pandas DataFrame to a SQLite table."""
    conn = get_db_connection()
    if conn:
        try:
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            st.error(f"Failed to save data to {table_name}: {e}")
            conn.close()
            return False
    return False

def sanitize_text(text):
    return text.replace("’", "'") if pd.notna(text) else ""

def truncate_text(text, max_length=14):
    text = str(text)
    if len(text) >= 15:
        return text[:max_length] + "..."
    return text

def get_full_image_path(image_path):
    """Resolve the full path to an image, prioritizing the reference_color.jpg format."""
    if not image_path or pd.isna(image_path):
        return None
    
    IMAGE_FOLDER = os.path.join(BASE_DIR, "images")
    image_path = image_path.strip()
    
    if os.path.isabs(image_path):
        if os.path.exists(image_path):
            return image_path
        st.warning(f"Absolute image path not found: {image_path}")
        return None
    
    # Split multiple image paths
    image_list = [img.strip() for img in image_path.split(',') if img.strip()]
    for img in image_list:
        cleaned_path = img.lstrip('/').lstrip('./').lstrip('images/').strip()
        full_path = os.path.join(IMAGE_FOLDER, cleaned_path)
        
        # Check if the exact path exists
        if os.path.exists(full_path):
            return full_path
        
        # Try matching the reference_color.jpg pattern
        match = re.match(r"(.*/)?([^/]+)_([^/]+)\.(jpg|jpeg|png|webp)", cleaned_path, re.IGNORECASE)
        if match:
            prefix, ref, color, ext = match.groups()
            test_path = os.path.join(IMAGE_FOLDER, prefix or '', f"{ref}_{color.upper()}.{ext.lower()}")
            if os.path.exists(test_path):
                return test_path
        
        # Fallback to checking directory for any matching file
        base, ext = os.path.splitext(full_path)
        extensions_to_try = [ext.lower(), '.jpg', '.jpeg', '.png', '.webp']
        for extension in extensions_to_try:
            test_path = f"{base}{extension}"
            if os.path.exists(test_path):
                return test_path
    
    # If no exact match, look for any file in the directory
    if len(image_list) > 0:
        dir_path, file_name = os.path.split(os.path.join(IMAGE_FOLDER, image_list[0].lstrip('/').lstrip('./').lstrip('images/')))
        if os.path.exists(dir_path):
            file_base = os.path.splitext(file_name)[0].lower()
            for f in os.listdir(dir_path):
                if f.lower().startswith(file_base):
                    return os.path.join(dir_path, f)
    
    st.warning(f"Image path not found: {image_path}")
    return None

def get_image_dimensions(image_path):
    try:
        with Image.open(image_path) as img:
            width, height = img.size
        return width, height
    except Exception as e:
        st.warning(f"Could not get dimensions for image {image_path}: {e}")
        return None, None

def calculate_image_dimensions(image_path, max_width_mm, max_height_mm):
    DPI = 72
    MM_PER_INCH = 25.4
    max_width_px = (max_width_mm / MM_PER_INCH) * DPI
    max_height_px = (max_height_mm / MM_PER_INCH) * DPI
    width_px, height_px = get_image_dimensions(image_path)
    if width_px is None or height_px is None:
        return max_width_mm, max_height_mm
    width_scaling = max_width_px / width_px
    height_scaling = max_height_px / height_px
    scaling_factor = min(width_scaling, height_scaling)
    new_width_mm = (width_px * scaling_factor) * MM_PER_INCH / DPI
    new_height_mm = (height_px * scaling_factor) * MM_PER_INCH / DPI
    return new_width_mm, new_height_mm

def validate_email(email):
    if not email:
        return True
    return bool(re.match(EMAIL_REGEX, email))

def validate_phone(phone):
    if not phone:
        return True
    return bool(re.match(PHONE_REGEX, phone))

def find_image_path_for_color(image_paths, color):
    """Find the first image path matching the specified color in the filename."""
    if not image_paths or pd.isna(image_paths) or not color:
        return None
    
    color_clean = color.lower().replace(' ', '_')
    image_list = [img.strip() for img in str(image_paths).split(',') if img.strip()]
    
    for img in image_list:
        img_name = os.path.basename(img).lower()
        if f"_{color_clean}_" in img_name:
            return get_full_image_path(img)
    
    for img in image_list:
        img_name = os.path.basename(img).lower()
        if color_clean in img_name:
            return get_full_image_path(img)
    
    for img in image_list:
        full_path = get_full_image_path(img)
        if full_path:
            st.warning(f"No image matched '{color}'. Using: {os.path.basename(full_path)}")
            return full_path
    
    st.warning(f"No valid images found for {image_paths}")
    return None

def transactional_update(func):
    """Decorator for database operations requiring transaction safety."""
    def wrapper(*args, **kwargs):
        conn = None
        try:
            conn = get_db_connection()
            conn.execute("BEGIN")
            result = func(*args, **kwargs, conn=conn)
            conn.commit()
            return result
        except Exception as e:
            if conn:
                conn.rollback()
            st.error(f"Operation failed: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()
    return wrapper

def log_audit_event(user, action, reference, details=None):
    """Record audit trail entries."""
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO audit_log 
            (timestamp, user, action, reference, details)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now(), user, action, reference, str(details)))
        conn.commit()
    except Exception as e:
        st.error(f"Audit log failed: {str(e)}")
    finally:
        conn.close()
    """Create a backup of the database."""
    conn = get_db_connection()
    try:
        # Replace with actual database path or fetch from config
        db_path = "data/pos_system.db"
        backup_path = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(db_path, backup_path)
        return backup_path
    except Exception as e:
        st.error(f"Backup failed: {str(e)}")
        return None
    finally:
        conn.close()