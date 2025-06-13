#!/usr/bin/env python3
"""
Catafactu POS System - Enhanced Version

A comprehensive Point of Sale system with inventory management, client tracking,
and financial reporting capabilities. This enhanced version includes improved
error handling, responsive UI, and modern design elements.

Author: Haroun Boukhalfa
Version: 2.0.0
"""

import os
import sys
import json
import time
import bcrypt
import sqlite3
import logging
import threading
import pandas as pd
import streamlit as st
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.append(str(Path(__file__).parent))

# Import application modules
from modules.client_management import (
    initialize_clients_df, get_client_info, add_new_client,
    save_clients, update_client, backup_clients
)

from modules.product_management import (
    add_or_update_product, generate_excel_template, import_products_from_excel,
    load_products, mark_discontinued, permanently_delete, update_stock,
    restock_product, backup_products, get_product_categories
)

from modules.transaction_management import (
    record_transaction, record_expenditure, record_staff_payment,
    get_till_balance, fetch_df_from_db, backup_transactions
)

from modules.pdf_generator import generate_receipt_pdf, generate_proforma_pdf

# Import page modules
from modules.pos import pos_page
from modules.proforma import proforma_page
from modules.restock import restock_page
from modules.bon_de_commande import bon_de_commande_page

from modules.product_management import load_products
from modules.utils import (
    validate_email, validate_phone, find_image_path_for_color,
    get_full_image_path, get_db_connection, format_currency,
    calculate_discount, apply_tax, get_current_user, log_activity,
    get_system_stats
)

# Constants
CONFIG = {
    'USERS_FILE': 'data/users.json',
    'DB_FILE': 'data/pos_system.db',
    'BACKUP_DIR': 'backups',
    'SESSION_TIMEOUT': 3600,  # 1 hour in seconds
    'ITEMS_PER_PAGE': 20,
    'DEFAULT_CURRENCY': 'DZD',
    'TAX_RATE': 0.19,  # 19% VAT
    'COMPANY_NAME': 'Catafactu',
    'COMPANY_ADDRESS': '123 Business St, City, Country',
    'COMPANY_PHONE': '+213 XX XX XX XX',
    'COMPANY_EMAIL': 'contact@catafactu.dz'
}

# Ensure necessary directories exist
os.makedirs(CONFIG['BACKUP_DIR'], exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('generated_pdfs', exist_ok=True)

# Set page configuration
st.set_page_config(
    page_title=f"{CONFIG['COMPANY_NAME']} - POS System",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI with enhanced typography
st.markdown("""
    <style>
    /* Import Google Fonts - Roboto for body, Poppins for headings */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Poppins:wght@400;500;600;700&display=swap');
    
    /* Base styles with improved typography */
    html, body, .stApp {
        font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        line-height: 1.6;
        color: #2d3436;
        background-color: #f8f9fa;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        font-weight: 600;
        line-height: 1.3;
        margin-bottom: 0.75em;
        color: #1a1a1a;
    }
    
    h1 { font-size: 2.2rem; }
    h2 { font-size: 1.8rem; }
    h3 { font-size: 1.5rem; }
    h4 { font-size: 1.3rem; }
    h5 { font-size: 1.1rem; }
    
    p, li, td, th, label, input, textarea, select, button {
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Header */
    .stApp > header {
        background-color: #2c3e50;
        color: white;
        padding: 1.2rem 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        letter-spacing: 0.3px;
        padding: 0.5rem 1.25rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        font-family: 'Poppins', sans-serif;
    }
    
    .stButton > button:disabled {
        opacity: 0.7;
        cursor: not-allowed;
    }
    
    button[kind="primary"] {
        background-color: #3498db !important;
        border-color: #2980b9 !important;
        color: white !important;
        font-weight: 600 !important;
    }
    
    button[kind="primary"]:hover:not(:disabled) {
        background-color: #2980b9 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(41, 128, 185, 0.3) !important;
    }
    
    button[kind="secondary"] {
        background-color: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        color: #495057 !important;
        font-weight: 500 !important;
    }
    
    button[kind="secondary"]:hover:not(:disabled) {
        background-color: #e9ecef !important;
        transform: translateY(-2px);
        box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
    }
    
    /* Form elements - General Styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div,
    .stDateInput > div > div > input,
    .stMultiSelect > div > div > div,
    .stTextInput > div > div > input[type="text"],
    .stTextInput > div > div > input[type="password"],
    .stTextInput > div > div > input[type="email"],
    .stTextInput > div > div > input[type="number"],
    .stTextInput > div > div > input[type="tel"],
    .stTextInput > div > div > input[type="url"],
    .stTextInput > div > div > input[type="search"],
    .stTextInput > div > div > input[type="date"],
    .stTextInput > div > div > input[type="time"],
    .stTextInput > div > div > input[type="datetime-local"] {
        border-radius: 8px !important;
        border: 1px solid #d1d5db !important;
        padding: 0.65rem 1rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        font-size: 0.95rem;
        background-color: #ffffff !important;
        color: #1f2937 !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    
    /* Focus states */
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > div:focus,
    .stMultiSelect > div > div > div:focus,
    .stDateInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
        outline: 2px solid transparent !important;
        outline-offset: 2px !important;
    }
    
    /* Placeholder text */
    ::placeholder {
        color: #9ca3af !important;
        opacity: 1;
    }
    
    /* Checkboxes and Radio Buttons */
    .stCheckbox > div > label,
    .stRadio > div > label,
    .stCheckbox > div > div > label,
    .stRadio > div > div > label {
        color: #374151 !important;
        font-weight: 500;
    }
    
    /* Checkbox custom styling */
    .stCheckbox > div > div[role="checkbox"] {
        border-color: #d1d5db !important;
        border-radius: 4px !important;
        width: 20px !important;
        height: 20px !important;
        margin-right: 8px !important;
    }
    
    .stCheckbox > div > div[role="checkbox"][aria-checked="true"] {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
    }
    
    /* Select dropdown */
    .stSelectbox > div > div > div,
    .stMultiSelect > div > div > div {
        min-height: 44px;
        display: flex;
        align-items: center;
    }
    
    /* Textarea */
    .stTextArea > div > div > textarea {
        min-height: 100px;
        line-height: 1.5;
    }
    
    /* Date input */
    .stDateInput > div > div > input {
        padding-right: 2.5rem !important;
    }
    
    /* Labels */
    .stTextInput > label,
    .stNumberInput > label,
    .stTextArea > label,
    .stSelectbox > label,
    .stDateInput > label,
    .stCheckbox > label,
    .stRadio > label,
    .stMultiSelect > label {
        font-weight: 600 !important;
        color: #374151 !important;
        margin-bottom: 0.5rem !important;
        display: block;
        font-size: 0.95rem;
    }
    
    /* Required field indicator */
    .stTextInput > label:after,
    .stNumberInput > label:after,
    .stTextArea > label:after,
    .stSelectbox > label:after,
    .stDateInput > label:after,
    .required:after {
        content: " *";
        color: #ef4444;
    }
    
    /* Cards */
    .card {
        background: #ffffff;
        border-radius: 12px;
        padding: 1.75rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 1.75rem;
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    /* Tables */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid #e9ecef;
    }
    
    .stDataFrame th {
        background-color: #f8f9fa !important;
        font-weight: 600 !important;
        color: #2c3e50 !important;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.5px;
    }
    
    .stDataFrame td {
        padding: 0.75rem 1rem !important;
        vertical-align: middle;
    }
    
    /* Status indicators */
    .status-success {
        color: #27ae60;
        font-weight: 600;
    }
    
    .status-warning {
        color: #f39c12;
        font-weight: 600;
    }
    
    .status-error {
        color: #e74c3c;
        font-weight: 600;
    }
    
    /* Alerts and notifications */
    .stAlert {
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e9ecef;
        padding: 1.5rem 0.75rem;
    }
    
    /* Sidebar Navigation */
    .sidebar .sidebar-content {
        padding: 0.5rem 0;
    }
    
    .sidebar .sidebar-content .block-container {
        padding: 0;
    }
    
    .sidebar .sidebar-content .stRadio > div {
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .sidebar .sidebar-content .stRadio > div > label {
        margin: 0;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        color: #4b5563;
    }
    
    .sidebar .sidebar-content .stRadio > div > label:hover {
        background-color: #f1f5f9;
        color: #1e40af;
    }
    
    .sidebar .sidebar-content .stRadio > div > label > div:first-child {
        margin-right: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
    }
    
    .sidebar .sidebar-content .stRadio > div > label > div:last-child {
        flex: 1;
    }
    
    .sidebar .sidebar-content .stRadio > div > [data-baseweb="radio"] {
        display: none;
    }
    
    .sidebar .sidebar-content .stRadio > div > [data-baseweb="radio"]:checked + label {
        background-color: #eff6ff;
        color: #1e40af;
        font-weight: 600;
    }
    
    /* Icons */
    .sidebar-icon {
        font-size: 1.25rem;
        margin-right: 0.75rem;
        opacity: 0.8;
    }
    
    /* User info in sidebar */
    .user-info {
        padding: 1.25rem 1rem;
        margin: 0 -0.75rem 1rem;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .user-name {
        font-weight: 600;
        margin-bottom: 0.25rem;
        color: #1f2937;
    }
    
    .user-role {
        font-size: 0.85rem;
        color: #6b7280;
        background-color: #f3f4f6;
        padding: 0.15rem 0.5rem;
        border-radius: 12px;
        display: inline-block;
    }
    
    /* Main content area */
    .main .block-container {
        padding: 2rem 2.5rem;
        max-width: 1400px;
    }
    
    /* Page headers */
    .main h1 {
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #e5e7eb;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .main h1 .icon {
        background-color: #eff6ff;
        color: #3b82f6;
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
    }
    
    /* Cards and sections */
    .section-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 1.5rem;
    }
    
    .section-card h2 {
        font-size: 1.25rem;
        margin-top: 0;
        margin-bottom: 1.25rem;
        color: #1f2937;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1.25rem;
        }
        
        .stApp > header {
            padding: 1rem 1.25rem;
        }
        
        .card, .section-card {
            padding: 1.25rem;
            border-radius: 10px;
        }
        
        h1 { 
            font-size: 1.8rem; 
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
        }
        
        h1 .icon {
            width: 40px;
            height: 40px;
            font-size: 1.25rem;
        }
        
        h2 { 
            font-size: 1.5rem; 
        }
        
        h3 { 
            font-size: 1.3rem; 
        }
        
        /* Stack columns on mobile */
        .st-cq, .st-cr, .st-cs, .st-ct, .st-cu, .st-cv, .st-cw, .st-cx, .st-cy, .st-cz {
            width: 100% !important;
        }
    
    /* Login Page Styling */
    .login-container {
        max-width: 500px;
        margin: 4rem auto;
        padding: 2.5rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        border: 1px solid #e5e7eb;
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .login-logo {
        width: 80px;
        height: 80px;
        margin: 0 auto 1.5rem;
        background-color: #eff6ff;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        color: #3b82f6;
    }
    
    .login-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    
    .login-subtitle {
        color: #6b7280;
        margin-bottom: 0;
    }
    
    .login-form .stTextInput,
    .login-form .stButton {
        margin-bottom: 1.25rem;
    }
    
    .login-footer {
        text-align: center;
        margin-top: 2rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e5e7eb;
        color: #6b7280;
        font-size: 0.9rem;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
    
    /* Print styles */
    @media print {
        .no-print {
            display: none !important;
        }
        
        .card, .section-card {
            box-shadow: none !important;
            border: 1px solid #ddd !important;
            page-break-inside: avoid;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    """Initialize the session state variables if they don't exist."""
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()
    if 'notifications' not in st.session_state:
        st.session_state.notifications = []
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False

# Call the initialization function
initialize_session_state()

# Fix for dark backgrounds with dark text
st.markdown("""
    <style>
    .stMarkdown, .stMarkdown p, .stMarkdown span {
        color: #000000 !important;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: #000000 !important;
    }
    .stMarkdown code {
        color: #000000 !important;
        background-color: #f0f0f0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Fix for charts
st.markdown("""
    <style>
    .vega-embed .marks .background {
        fill: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# Fix for proforma text
st.markdown("""
    <style>
    .proforma-text {
        color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.7) !important;
        padding: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

import bcrypt
import json
import os
import pandas as pd
import time
import schedule
from modules.utils import fetch_df_from_db
from modules.product_management import backup_database as backup_products_db
from modules.transaction_management import backup_transactions
from modules.client_management import backup_clients
from modules.product_management import load_products
from modules.transaction_management import get_till_balance, record_expenditure, record_staff_payment
from modules.client_management import initialize_clients_df

def load_users(force_reset=False):
    default_users = {
        "users": [
            {"username": "admin", "password": bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode(), "role": "admin", "access": ["🏠 Dashboard", "📋 Proforma", "🛒 POS", "📦 Restock", "👥 Clients", "📚 Articles", "💸 Expenditures", "👨‍💼 Staff Payments", "💰 Till", "🔒 Access Control", "📜 Invoice History", "📋 Activity Log", "📝 Bon de Commande"]},
            {"username": "eulma", "password": bcrypt.hashpw("eulma".encode(), bcrypt.gensalt()).decode(), "role": "operator", "access": ["📋 Proforma", "🛒 POS", "👥 Clients", "📚 Articles"]},
            {"username": "alger", "password": bcrypt.hashpw("alger".encode(), bcrypt.gensalt()).decode(), "role": "operator", "access": ["📋 Proforma", "🛒 POS", "👥 Clients", "📚 Articles"]},
            {"username": "constantine", "password": bcrypt.hashpw("constantine".encode(), bcrypt.gensalt()).decode(), "role": "operator", "access": ["📋 Proforma", "🛒 POS", "👥 Clients", "📚 Articles"]}
        ],
        "access_control_enabled": False
    }
    users_file = CONFIG['USERS_FILE']
    os.makedirs(os.path.dirname(users_file), exist_ok=True)
    if force_reset or not os.path.exists(users_file):
        with open(users_file, 'w') as f:
            json.dump(default_users, f)
        return default_users
    with open(users_file, 'r') as f:
        return json.load(f)

def save_users(users_data):
    users_file = CONFIG['USERS_FILE']
    os.makedirs(os.path.dirname(users_file), exist_ok=True)
    with open(users_file, 'w') as f:
        json.dump(users_data, f, indent=2)

def login():
    if st.session_state.get('logged_in', False):
        return True
    st.session_state.setdefault('logged_in', False)
    st.session_state.setdefault('user', None)
    users_data = load_users()
    access_control_enabled = users_data.get("access_control_enabled", False)
    if not access_control_enabled:
        st.session_state['logged_in'] = True
        admin_user = next(u for u in users_data["users"] if u["username"] == "admin")
        st.session_state['user'] = admin_user
        return True
    st.title("Connexion")
    username = st.text_input("Nom d'utilisateur", key="login_username")
    password = st.text_input("Mot de passe", type="password", key="login_password")
    if st.button("Se connecter"):
        user = next((u for u in users_data["users"] if u["username"] == username), None)
        if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
            st.session_state['logged_in'] = True
            st.session_state['user'] = user
            st.success(f"Bienvenue, {username} !")
            st.rerun()
            return True
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect.")
    return False

def initialize_session_state():
    if 'transaction_number' not in st.session_state:
        transactions_df = fetch_df_from_db('transactions')
        st.session_state['transaction_number'] = transactions_df["transaction_id"].max() + 1 if not transactions_df.empty else 1000
    if 'recent_clients' not in st.session_state:
        st.session_state['recent_clients'] = []
    st.session_state['clients_df'] = initialize_clients_df()  # Always refresh from DB

def expenditure_page():
    st.title("Dépenses")
    username = st.session_state['user']['username']
    description = st.text_input("Description de la dépense")
    amount = st.number_input("Montant (DZD)", min_value=0.0)
    if st.button("Enregistrer la dépense", key="expenditure_save_button"):
        record_expenditure(description, amount, username)
        st.success("Dépense enregistrée !")

def staff_payment_page():
    st.title("Paiements du personnel")
    username = st.session_state['user']['username']
    staff_name = st.text_input("Nom du personnel")
    amount = st.number_input("Montant (DZD)", min_value=0.0)
    note = st.text_area("Note", placeholder="Ajoutez une note (optionnel)")
    if st.button("Enregistrer le paiement", key="staff_payment_save_button"):
        if staff_name and amount > 0:
            record_staff_payment(staff_name, amount, username, note)
            st.success("Paiement du personnel enregistré !")
        else:
            st.error("Veuillez remplir le nom et le montant.")

def till_page():
    st.title("État de la caisse")
    balance = get_till_balance()
    st.write(f"**Solde actuel de la caisse :** {balance:.2f} DZD")

def dashboard_page():
    st.title("Tableau de Bord")
    transactions_df = fetch_df_from_db('transactions')
    products_df = load_products()

    if transactions_df.empty:
        st.info("Aucune transaction enregistrée pour le moment.")
    else:
        # Use 'final_amount' instead of 'payment_amount'
        total_sales = transactions_df[transactions_df['status'] == "completed"]['final_amount'].sum()
        st.write(f"**Ventes Totales :** {total_sales:,.2f} DZD")
        
        completed_items = []
        for items in transactions_df[transactions_df['status'] == "completed"]['items']:
            if isinstance(items, list):  # items is already a list from safe_json_loads
                for item in items:
                    if isinstance(item, dict) and 'denomination' in item and 'Quantity' in item:
                        completed_items.append(item)
            else:
                try:
                    items_list = json.loads(items)
                    for item in items_list:
                        if isinstance(item, dict) and 'denomination' in item and 'Quantity' in item:
                            completed_items.append(item)
                except:
                    st.warning(f"Unexpected items format: {items}")
        
        if completed_items:
            top_items = pd.DataFrame(completed_items).groupby('denomination')['Quantity'].sum().nlargest(5)
            st.write("**Top 5 Articles Vendus :**")
            st.dataframe(top_items)
        else:
            st.write("**Top 5 Articles Vendus :** Aucun article vendu trouvé.")
    
    till_balance = get_till_balance()
    st.write(f"**Solde de la Caisse :** {till_balance:,.2f} DZD")

def invoice_history_page():
    st.title("Historique des Factures")
    transactions_df = fetch_df_from_db('transactions')
    
    if transactions_df.empty:
        st.info("Aucune transaction enregistrée.")
        return
    
    # Sort transactions by date in descending order (newest first)
    if 'transaction_date' in transactions_df.columns:
        transactions_df = transactions_df.sort_values('transaction_date', ascending=False)
    
    # Create a more informative display for the dropdown
    transactions_df['display'] = transactions_df.apply(
        lambda x: f"#{x['transaction_id']} - " + 
                 (pd.to_datetime(x['transaction_date']).strftime('%Y-%m-%d %H:%M') if pd.notna(x.get('transaction_date')) else 'Date inconnue') + 
                 f" - {x.get('total_amount', 0):.2f} DZD - {x.get('performed_by', 'N/A')}", 
        axis=1
    )
    
    # Create selectbox with formatted display
    selected_display = st.selectbox(
        "Sélectionnez une transaction",
        options=transactions_df['display'],
        format_func=lambda x: x
    )
    
    # Get the selected transaction
    selected_transaction = transactions_df[transactions_df['display'] == selected_display].iloc[0]
    
    # Display transaction details in a card
    with st.container():
        st.subheader(f"Détails de la transaction #{selected_transaction['transaction_id']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Montant Total", f"{selected_transaction.get('total_amount', 0):.2f} DZD")
            if 'client_id' in selected_transaction and pd.notna(selected_transaction['client_id']):
                st.write(f"**Client ID :** {selected_transaction['client_id']}")
        
        with col2:
            transaction_date = selected_transaction.get('transaction_date')
            if pd.notna(transaction_date):
                try:
                    # Try to format the date if it's a valid date
                    formatted_date = pd.to_datetime(transaction_date).strftime('%d/%m/%Y %H:%M')
                    st.write(f"**Date :** {formatted_date}")
                except:
                    st.write(f"**Date :** {transaction_date}")
            else:
                st.write("**Date :** Non spécifiée")
        
        # Payment details
        st.write("---")
        st.write("**Détails de paiement :**")
        st.write(f"- **Montant payé :** {selected_transaction.get('payment_amount', 0):.2f} DZD")
        st.write(f"- **Mode de paiement :** {selected_transaction.get('payment_details', 'Non spécifié')}")
        st.write(f"- **Effectué par :** {selected_transaction.get('performed_by', 'N/A')}")
        
        # Display items
        st.write("---")
        st.write("**Articles :**")
        items = selected_transaction.get('items', [])
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except:
                items = []
        
        if items:
            for item in items:
                st.write(f"- {item.get('denomination', 'Article inconnu')} "
                        f"({item.get('reference', 'N/A')}) - "
                        f"{item.get('Quantity', 0)} x {item.get('Price', 0):.2f} DZD")
        else:
            st.info("Aucun détail d'article disponible pour cette transaction.")
        
        # PDF download button
        transaction_id = selected_transaction['transaction_id']
        pdf_filename = f"Receipt-{transaction_id}.pdf"
        
        # Try to find the PDF file with or without date in the name
        pdf_found = False
        if os.path.exists(pdf_filename):
            pdf_found = True
        else:
            # Try alternative filename with date
            alt_pdf_filename = f"Receipt-{transaction_id}-{pd.to_datetime(transaction_date).strftime('%Y%m%d') if pd.notna(transaction_date) else ''}.pdf"
            if os.path.exists(alt_pdf_filename):
                pdf_filename = alt_pdf_filename
                pdf_found = True
        
        if pdf_found:
            with open(pdf_filename, "rb") as file:
                st.download_button(
                    "📄 Télécharger le reçu", 
                    file, 
                    pdf_filename, 
                    mime="application/pdf", 
                    key=f"history_download_{transaction_id}",
                    use_container_width=True
                )
        else:
            st.warning("Le fichier PDF de cette transaction n'est pas disponible.")

def activity_log_page():
    st.title("Journal d'Activité")
    transactions_df = fetch_df_from_db('transactions')
    if not transactions_df.empty:
        st.write("### Toutes les actions enregistrées")
        users = [str(u) if u is not None else "Inconnu" for u in transactions_df['performed_by'].unique()]
        filter_user = st.selectbox("Filtrer par utilisateur", ["Tous"] + sorted(users), key="filter_user")
        filter_type = st.selectbox("Filtrer par type", ["Tous", "proforma", "completed", "restock", "expenditure", "staff_payment"], key="filter_type")
        filtered_df = transactions_df
        if filter_user != "Tous":
            filtered_df = filtered_df[filtered_df['performed_by'] == filter_user]
        if filter_type != "Tous":
            filtered_df = filtered_df[filtered_df['status'] == filter_type]
        display_df = filtered_df[['transaction_id', 'transaction_date', 'performed_by', 'status', 'payment_amount', 'client_id']].rename(columns={
            'transaction_id': 'ID Transaction',
            'transaction_date': 'Date',
            'performed_by': 'Effectué par',
            'status': 'Type',
            'payment_amount': 'Montant (DZD)',
            'client_id': 'ID Client'
        })
        display_df['Type'] = display_df['Type'].replace({
            'proforma': 'Proforma',
            'completed': 'Vente',
            'restock': 'Restock',
            'expenditure': 'Dépense',
            'staff_payment': 'Paiement Personnel'
        })
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("Aucune activité enregistrée.")

def change_password_page():
    st.title("Changer le mot de passe")
    current_password = st.text_input("Mot de passe actuel", type="password", key="current_password")
    new_password = st.text_input("Nouveau mot de passe", type="password", key="new_password")
    confirm_password = st.text_input("Confirmer le nouveau mot de passe", type="password", key="confirm_password")
    if st.button("Changer le mot de passe"):
        users_data = load_users()
        user = next(u for u in users_data["users"] if u["username"] == st.session_state['user']['username'])
        if bcrypt.checkpw(current_password.encode(), user["password"].encode()):
            if new_password == confirm_password:
                user["password"] = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                save_users(users_data)
                st.success("Mot de passe changé avec succès !")
            else:
                st.error("Les nouveaux mots de passe ne correspondent pas.")
        else:
            st.error("Mot de passe actuel incorrect.")

def clients_page():
    st.title("Gestion des Clients")
    clients_df = fetch_df_from_db('clients')
    edited_df = st.data_editor(clients_df, use_container_width=True)
    if st.button("Sauvegarder", key="clients_save_button"):
        conn = get_db_connection()
        edited_df.to_sql('clients', conn, if_exists='replace', index=False)
        st.session_state['clients_df'] = edited_df
        conn.close()
        st.success("Clients mis à jour !")

def initialize_products_table():
    """Initialize the products table in the database if it doesn't exist."""
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                reference TEXT PRIMARY KEY,
                denomination TEXT,
                quantite_initiale REAL DEFAULT 0,
                quantite_restockee REAL DEFAULT 0,
                quantite_vendue INTEGER DEFAULT 0,
                quantite_actuelle INTEGER DEFAULT 0,
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
                discontinued BOOLEAN DEFAULT 0
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Failed to create products table: {e}")
    finally:
        conn.close()

def articles_page():
    """Render the Product Management page with tabs for listing, editing, importing, and managing products."""
    # Permissions check
    if 'role' not in st.session_state.user or st.session_state.user['role'] not in ['admin', 'inventory_manager']:
        st.error("You need elevated privileges to access this page!")
        return
    
    # Initialize products table on first load
    if 'products_initialized' not in st.session_state:
        initialize_products_table()
        st.session_state.products_initialized = True
    
    # Page title
    st.title("📚 Product Management")
    
    # Load products data
    products_df = load_products()
    is_admin = st.session_state.user['role'] == 'admin' 
    if products_df.empty:
        st.warning("No active products found in the database.")
        return
    
    # Define tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["List & Edit", "Import from Excel", "Add New", "Manage Discontinued", "Backup"])
    
    # Tab 1: List & Edit
    with tab1:
        st.subheader("Product List")
        all_columns = [
            'reference', 'denomination', 'quantite_initiale', 'quantite_restockee', 'quantite_vendue',
            'quantite_actuelle', 'couleurs-dispo-usine', 'images', 'prix-super-gros', 'prix-gros',
            'prix-détail', 'uni_colour', 'default_colour', 'brown', 'brown_deg', 'blue', 'white',
            'black', 'green_bottle', 'red', 'grey', 'grey_deg', 'beige', 'yellow', 'orange',
            'garnet', 'golden', 'green', 'rose', 'note', 'category', 'quantite_vendu_actue',
            'last_updated', 'discontinued'
        ]
        
        # Configure columns with better display names
        column_config = {
            "reference": st.column_config.TextColumn("Reference", width="medium"),
            "denomination": st.column_config.TextColumn("Name", width="large"),
            "quantite_actuelle": st.column_config.NumberColumn("Current Qty", width="small", disabled=True),
            "prix-détail": st.column_config.NumberColumn("Retail Price", format="%.2f"),
            "prix-super-gros": st.column_config.NumberColumn("Super Gros Price", format="%.2f"),
            "prix-gros": st.column_config.NumberColumn("Gros Price", format="%.2f"),
        }
        
        edited_df = st.data_editor(
            products_df[all_columns],
            use_container_width=True,
            column_config=column_config,
            key="product_list_full"
        )

def access_control_page():
    st.title("Contrôle d'accès")
    if st.session_state['user']['role'] != "admin":
        st.error("Accès réservé à l'administrateur.")
        return
    users_data = load_users()
    if 'temp_users_data' not in st.session_state:
        st.session_state['temp_users_data'] = users_data.copy()
    temp_users_data = st.session_state['temp_users_data']
    st.write("### Gestion des utilisateurs")
    access_enabled = st.checkbox("Activer le contrôle d'accès", value=temp_users_data["access_control_enabled"], key="access_control_toggle")
    temp_users_data["access_control_enabled"] = access_enabled
    for i, user in enumerate(temp_users_data["users"]):
        with st.expander(f"Utilisateur: {user['username']} ({user['role']})", expanded=False):
            new_username = st.text_input("Nom d'utilisateur", value=user["username"], key=f"username_{i}")
            new_password = st.text_input("Nouveau mot de passe", type="password", key=f"password_{i}")
            new_role = st.selectbox("Rôle", ["admin", "operator"], index=0 if user["role"] == "admin" else 1, key=f"role_{i}")
            access_options = [
                "🏠 Dashboard", "📋 Proforma", "🛒 POS", "📦 Restock",
                "👥 Clients", "📚 Articles", "💸 Expenditures",
                "👨‍💼 Staff Payments", "💰 Till", "🔒 Access Control",
                "📜 Invoice History", "📋 Activity Log", "📝 Bon de Commande"
            ]
            new_access = st.multiselect("Accès", access_options, default=user["access"], key=f"access_{i}")
            temp_users_data["users"][i]["username"] = new_username
            if new_password:
                temp_users_data["users"][i]["password"] = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            temp_users_data["users"][i]["role"] = new_role
            temp_users_data["users"][i]["access"] = new_access
            if st.button("Supprimer", key=f"delete_{i}"):
                if user["username"] != "admin":
                    temp_users_data["users"].pop(i)
                    st.success(f"Utilisateur supprimé !")
                    st.rerun()
                else:
                    st.error("Impossible de supprimer l'utilisateur admin.")
    with st.expander("Ajouter un nouvel utilisateur", expanded=False):
        new_username = st.text_input("Nouveau nom d'utilisateur", key="new_username")
        new_password = st.text_input("Mot de passe", type="password", key="new_password")
        new_role = st.selectbox("Rôle", ["admin", "operator"], key="new_role")
        new_access = st.multiselect("Accès", access_options, key="new_access")
        if st.button("Ajouter utilisateur", key="add_user"):
            if new_username and new_password:
                if any(u["username"] == new_username for u in temp_users_data["users"]):
                    st.error("Ce nom d'utilisateur existe déjà.")
                else:
                    new_user = {
                        "username": new_username,
                        "password": bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode(),
                        "role": new_role,
                        "access": new_access
                    }
                    temp_users_data["users"].append(new_user)
                    st.success(f"Utilisateur {new_username} ajouté !")
                    st.rerun()
            else:
                st.error("Veuillez remplir tous les champs.")
    if st.button("Sauvegarder", key="save_access_control"):
        save_users(temp_users_data)
        st.session_state['temp_users_data'] = temp_users_data.copy()
        st.success("Modifications sauvegardées !")

def run_scheduled_tasks():
    """Run scheduled tasks in a background thread."""
    # Schedule daily backups at midnight
    schedule.every().day.at("00:00").do(backup_products_db)
    schedule.every().day.at("00:00").do(backup_transactions)
    schedule.every().day.at("00:00").do(backup_clients)
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Error in scheduled task: {e}")

def main():
    if not login():
        return
    user = st.session_state['user']
    menu_options = user.get("access", [])
    
    # Validate menu_options
    if not isinstance(menu_options, list) or not all(isinstance(opt, str) for opt in menu_options):
        st.error("Erreur: Les options de menu de l'utilisateur sont invalides.")
        st.write("Données utilisateur:", user)
        return
    
    st.sidebar.title(f"Menu - {user['username']} ({user['role'].capitalize()})")
    if st.sidebar.button("Déconnexion", key="logout_button"):
        st.session_state['logged_in'] = False
        st.session_state['user'] = None
        st.rerun()
    
    page = st.sidebar.radio("Aller à", menu_options + ["🔑 Changer le mot de passe"], key="sidebar_menu")
    
    initialize_session_state()
    products_df = load_products()
    clients_df = st.session_state['clients_df']
    
    if page == "🏠 Dashboard":
        dashboard_page()
    elif page == "📋 Proforma":
        proforma_page(products_df, clients_df)
    elif page == "🛒 POS":
        pos_page(products_df, clients_df)
    elif page == "📦 Restock":
        restock_page()
    elif page == "👥 Clients":
        clients_page()
    elif page == "📚 Articles":
        articles_page()
    elif page == "💸 Expenditures":
        expenditure_page()
    elif page == "👨‍💼 Staff Payments":
        staff_payment_page()
    elif page == "💰 Till":
        till_page()
    elif page == "🔒 Access Control":
        access_control_page()
    elif page == "📜 Invoice History":
        invoice_history_page()
    elif page == "📋 Activity Log":
        activity_log_page()
    elif page == "📝 Bon de Commande":
        bon_de_commande_page(products_df)
    elif page == "🔑 Changer le mot de passe":
        change_password_page()
    else:
        st.error(f"Page '{page}' non reconnue. Veuillez sélectionner une option valide.")

if __name__ == "__main__":
    main()