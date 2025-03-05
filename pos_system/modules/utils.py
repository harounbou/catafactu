import pandas as pd
import os
import re
from PIL import Image
import streamlit as st

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_REGEX = r'^\d{10}$'

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Points to pos_system/

def read_local_excel(file_path):
    full_path = os.path.join(BASE_DIR, file_path)
    try:
        df = pd.read_excel(full_path)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Échec de la lecture du fichier Excel local : {e}")
        return None

def save_excel(df, file_path):
    full_path = os.path.join(BASE_DIR, file_path)
    try:
        df.to_excel(full_path, index=False)
        return True
    except Exception as e:
        st.error(f"Échec de la sauvegarde du fichier {file_path} : {e}")
        return False

def read_csv(file_path):
    full_path = os.path.join(BASE_DIR, file_path)
    return pd.read_csv(full_path) if os.path.exists(full_path) else pd.DataFrame()

def save_csv(df, file_path):
    full_path = os.path.join(BASE_DIR, file_path)
    df.to_csv(full_path, index=False)

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