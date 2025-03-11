# modules/utils.py
import sqlite3
import os
import re
from PIL import Image
import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_REGEX = r'^\d{10}$'

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Points to pos_system/
DB_PATH = os.path.join(BASE_DIR, "data", "pos_system.db")

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
    IMAGE_FOLDER = os.path.join(BASE_DIR, "images")
    if pd.notna(image_path):
        image_path = image_path.lstrip('/').lstrip('./').lstrip('images/').strip()
        base_path = os.path.join(IMAGE_FOLDER, image_path)
        base, ext = os.path.splitext(base_path)
        extensions_to_try = [ext.lower(), '.png', '.jpg', '.jpeg', '.webp']
        for extension in extensions_to_try:
            test_path = f"{base}{extension}"
            if os.path.exists(test_path):
                return test_path
        dir_path, file_name = os.path.split(base_path)
        if os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.lower().startswith(os.path.splitext(file_name)[0].lower()):
                    return os.path.join(dir_path, f)
        st.warning(f"Image path not found: {base_path}*")
    return None

def find_image_path_for_color(images_str, selected_color):
    if pd.notna(images_str) and selected_color:
        image_paths = [path.strip() for path in images_str.split(',')]
        selected_color_lower = selected_color.lower()
        for path in image_paths:
            if selected_color_lower in path.lower():
                return path
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

def send_email(to_email, subject, body, attachment_path=None):
    """Send an email with optional attachment."""
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
        return False