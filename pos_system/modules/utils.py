# modules/utils.py
import sqlite3
import os
import re
from PIL import Image
import streamlit as st
import pandas as pd
import smtplib
#from email.mime.multipart import MIMEMultipart
#from email.mime.text import MIMEText
#from email.mime.application import MIMEApplication



EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_REGEX = r'^\d{10}$'

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Points to pos_system/
DB_PATH = os.path.join(BASE_DIR, "data", "pos_system.db")

# modules/utils.py

# Add these to existing utils.py
COLOR_MAPPING = {
    'brown_gradient': 'brown_deg',
    'grey_gradient': 'grey_deg',
    'gradient_brown': 'brown_deg',
    'gradient_grey': 'grey_deg'
}

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
    'rose': '#f8bbd0',
    'default': '#f5f5f5'
}

def get_db_color_name(display_color):
    """Map display color names to database column names"""
    cleaned_color = display_color.lower().replace(" ", "_")
    return COLOR_MAPPING.get(cleaned_color, cleaned_color)

def get_db_connection():
    """Establish a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # <-- KEY FIX
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection failed: {e}")
        return None

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
    """Resolve the full path to an image, handling relative and absolute paths."""
    if not image_path or pd.isna(image_path):
        return None
    
    IMAGE_FOLDER = os.path.join(BASE_DIR, "images")
    image_path = image_path.strip()  # Remove leading/trailing whitespace
    
    # If it's already an absolute path, use it directly if it exists
    if os.path.isabs(image_path):
        if os.path.exists(image_path):
            return image_path
        st.warning(f"Absolute image path not found: {image_path}")
        return None
    
    # Clean relative path (remove redundant prefixes like './' or 'images/')
    cleaned_path = image_path.lstrip('/').lstrip('./').lstrip('images/').strip()
    full_path = os.path.join(IMAGE_FOLDER, cleaned_path)
    
    # Check if the exact path exists
    if os.path.exists(full_path):
        return full_path
    
    # Try common image extensions if the base file doesn’t exist
    base, ext = os.path.splitext(full_path)
    extensions_to_try = [ext.lower(), '.jpg', '.jpeg', '.png', '.webp']
    for extension in extensions_to_try:
        test_path = f"{base}{extension}"
        if os.path.exists(test_path):
            return test_path
    
    # If still not found, search directory for a case-insensitive match
    dir_path, file_name = os.path.split(full_path)
    if os.path.exists(dir_path):
        file_base = os.path.splitext(file_name)[0].lower()
        for f in os.listdir(dir_path):
            if f.lower().startswith(file_base):
                return os.path.join(dir_path, f)
    
    st.warning(f"Image path not found: {full_path}*")
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

"""def send_email(to_email, subject, body, attachment_path=None):
    """"Send an email with optional attachment.""""""
    sender_email = st.secrets["gmail"]["email"]
    sender_password = st.secrets["gmail"]["password"]
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    if attachment_path:
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Échec de l'envoi de l'email : {e}")
        return False"""

def find_image_path_for_color(image_paths, color):
    """
    Find the image path matching a given color from a comma-separated list of image paths.
    Returns the first matching full path or None if no match is found.
    """
    if not image_paths or pd.isna(image_paths):
        return None
        
    # Handle case where image_paths is already a list
    if isinstance(image_paths, list):
        paths = image_paths
    else:
        # Split the comma-separated string into a list
        paths = [path.strip() for path in str(image_paths).split(',')]
    
    # Clean the color name (remove spaces, convert to lowercase)
    clean_color = str(color).lower().strip().replace(' ', '_')
    
    # Try to find a matching image path
    for path in paths:
        if not path or not isinstance(path, str):
            continue
            
        # Get the filename without extension and clean it
        filename = os.path.splitext(os.path.basename(path))[0].lower()
        filename = filename.replace(' ', '_')
        
        # Check if color is in the filename
        if clean_color in filename:
            full_path = get_full_image_path(path)
            if full_path and os.path.exists(full_path):
                return full_path
    
    # If no match found, return the first valid path if available
    for path in paths:
        if path and isinstance(path, str):
            full_path = get_full_image_path(path)
            if full_path and os.path.exists(full_path):
                return full_path
                
    return None

def format_currency(amount, currency='DZD'):
    """
    Format a number as a currency string.
    
    Args:
        amount (float): The amount to format
        currency (str): The currency code (default: 'DZD')
        
    Returns:
        str: Formatted currency string
    """
    try:
        amount = float(amount)
        if currency == 'DZD':
            return f"{amount:,.0f} {currency}".replace(",", " ")
        else:
            return f"{currency} {amount:,.2f}"
    except (ValueError, TypeError):
        return f"0 {currency}"

def calculate_discount(original_price, discount_percent):
    """
    Calculate the discounted price after applying a percentage discount.
    
    Args:
        original_price (float): Original price before discount
        discount_percent (float): Discount percentage (0-100)
        
    Returns:
        float: Price after discount
    """
    try:
        discount = float(original_price) * (float(discount_percent) / 100)
        return max(0, float(original_price) - discount)
    except (ValueError, TypeError):
        return original_price

def apply_tax(amount, tax_rate=19.0):
    """
    Calculate the tax amount and total including tax.
    
    Args:
        amount (float): Amount before tax
        tax_rate (float): Tax rate as a percentage (default: 19.0%)
        
    Returns:
        tuple: (tax_amount, total_with_tax)
    """
    try:
        tax = (float(amount) * float(tax_rate)) / 100
        return tax, float(amount) + tax
    except (ValueError, TypeError):
        return 0.0, amount

def get_current_user():
    """
    Get the currently logged-in user from the session state.
    
    Returns:
        dict: User information or None if not logged in
    """
    if 'user' in st.session_state:
        return st.session_state.user
    return None

def log_activity(action, details=None):
    """
    Log user activity to a log file.
    
    Args:
        action (str): Description of the action performed
        details (dict, optional): Additional details about the action
    """
    import logging
    logger = logging.getLogger('activity')
    logger.setLevel(logging.INFO)
    
    # Create file handler if it doesn't exist
    if not logger.handlers:
        os.makedirs('logs', exist_ok=True)
        fh = logging.FileHandler('logs/activity.log')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    
    # Get current user
    user = get_current_user()
    username = user.get('username', 'anonymous') if user else 'anonymous'
    
    # Format the log message
    log_msg = f"User: {username} - Action: {action}"
    if details:
        log_msg += f" - Details: {details}"
    
    logger.info(log_msg)

def get_system_stats():
    """
    Get basic system statistics.
    
    Returns:
        dict: Dictionary containing system statistics
    """
    import psutil
    import platform
    from datetime import datetime
    
    try:
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get system info
        system_info = {
            'os': f"{platform.system()} {platform.release()}",
            'python_version': platform.python_version(),
            'cpu_usage': f"{cpu_percent}%",
            'memory_used': f"{memory.used / (1024**3):.1f} GB",
            'memory_total': f"{memory.total / (1024**3):.1f} GB",
            'memory_percent': f"{memory.percent}%",
            'disk_used': f"{disk.used / (1024**3):.1f} GB",
            'disk_total': f"{disk.total / (1024**3):.1f} GB",
            'disk_percent': f"{disk.percent}%",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return system_info
    except Exception as e:
        print(f"Error getting system stats: {e}")
        return {}