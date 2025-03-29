# app.py
import streamlit as st
import pandas as pd
import json
import os
import sqlite3
import bcrypt
from datetime import datetime
import shutil
import threading
import schedule
import time

from modules.client_management import (
    initialize_clients_df,
    get_client_info,
    add_new_client,
    save_clients,
    update_client
)

from modules.product_management import (
    add_or_update_product,
    generate_excel_template,
    import_products_from_excel,
    load_products,
    mark_discontinued,
    permanently_delete,
    update_stock,
    restock_product,
    backup_database
)

from modules.transaction_management import (
    record_transaction,
    record_expenditure,
    record_staff_payment,
    get_till_balance,
    fetch_df_from_db
)

from modules.pdf_generator import (
    generate_receipt_pdf,
    generate_proforma_pdf
)

from modules.proforma import proforma_page
from modules.pos import pos_page
from modules.restock import restock_page
from modules.bon_de_commande import bon_de_commande_page

from modules.utils import (
    validate_email,
    validate_phone,
    find_image_path_for_color,
    get_full_image_path,
    #send_email,
    get_db_connection
)


USERS_FILE = "data/users.json"
DB_FILE = "data/pos_system.db"  # Assuming this is your DB path
BACKUP_DIR = "backups"

# Global CSS styling (unchanged)
st.markdown(
    """
    <style>
    .stApp { 
        background-color: #f0f0f0;
    }
    button[kind="primary"] { 
        background-color: #90EE90 !important; 
        color: black !important; 
    }
    button[kind="secondary"] { 
        background-color: #90EE90 !important; 
        color: black !important; 
    }
    div[data-baseweb="input"] > div {
        background-color: #e6e6e6;
        border: 1px solid #333;
        border-radius: 4px;
    }
    div[data-baseweb="select"] > div {
        background-color: #e6e6e6;
        border: 1px solid #333;
        border-radius: 4px;
    }
    input::placeholder {
        color: #555;
        opacity: 1;
    }
    input, div[data-baseweb="select"] {
        color: #000 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
    os.makedirs("data", exist_ok=True)
    if force_reset or not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump(default_users, f)
        return default_users
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users_data):
    with open(USERS_FILE, 'w') as f:
        json.dump(users_data, f)

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
    if not transactions_df.empty:
        selected_transaction = st.selectbox("Sélectionnez une transaction", transactions_df['transaction_id'])
        transaction = transactions_df[transactions_df['transaction_id'] == selected_transaction].iloc[0]
        st.write(f"**Client ID :** {transaction['client_id']}")
        st.write(f"**Date :** {transaction['transaction_date']}")
        st.write(f"**Montant Payé :** {transaction['payment_amount']:.2f} DZD")
        st.write(f"**Mode de paiement :** {transaction['payment_details']}")
        st.write(f"**Effectué par :** {transaction['performed_by']}")
        items = json.loads(transaction['items'])
        st.write("**Articles :**")
        for item in items:
            st.write(f"- {item['denomination']} ({item['reference']}) - {item['Quantity']} x {item['Price']:.2f}")
        pdf_filename = f"Receipt-{selected_transaction}-{transaction['transaction_date'].replace('/', '')}.pdf"
        if os.path.exists(pdf_filename):
            with open(pdf_filename, "rb") as file:
                st.download_button("Télécharger le reçu", file, pdf_filename, mime="application/pdf", key=f"history_download_{selected_transaction}")
        else:
            st.warning("Le fichier PDF de cette transaction n'est pas disponible.")
    else:
        st.info("Aucune transaction enregistrée.")

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

def backup_database():
    """Create a backup of the database with a timestamp."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.sqlite")
    shutil.copy2(DB_FILE, backup_path)
    return backup_path

def run_scheduled_tasks():
    """Run scheduled tasks in a background thread."""
    schedule.every().day.at("00:00").do(backup_database)
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

import streamlit as st
import pandas as pd
import os
from datetime import datetime

def articles_page():
    # Permissions check
    if 'role' not in st.session_state.user or st.session_state.user['role'] not in ['admin', 'inventory_manager']:
        st.error("You need elevated privileges to access this page!")
        return
    
    st.write(f"Debug: User role = {st.session_state.user['role']}")  # Confirm role
    
    # Initialize table (should already exist since data is present)
    if 'products_initialized' not in st.session_state:
        initialize_products_table()
        st.session_state.products_initialized = True
        st.write("Debug: Products table initialized")
    
    st.title("📚 Product Management")
    products_df = load_products()
    st.write(f"Debug: Loaded {len(products_df)} products")  # Check row count
    st.write("Debug: Products DataFrame preview:", products_df.head())  # Inspect data
    
    if products_df.empty:
        st.warning("No products loaded from the database.")
        return
    
    is_admin = st.session_state.user['role'] == 'admin'
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["List & Edit", "Import from Excel", "Add New", "Manage Discontinued", "Backup"])
    
    with tab1:
        st.subheader("Product List")
        #st.write("Debug: Rendering Tab 1")  # Confirm tab rendering
        all_columns = [
            'reference', 'denomination', 'quantite_initiale', 'quantite_restockee', 'quantite_vendue', 
            'quantite_actuelle', 'couleurs-dispo-usine', 'images', 'prix-super-gros', 'prix-gros', 
            'prix-détail', 'uni_colour', 'default_colour', 'brown', 'brown_deg', 'blue', 'white', 
            'black', 'green_bottle', 'red', 'grey', 'grey_deg', 'beige', 'yellow', 'orange', 
            'garnet', 'golden', 'green', 'rose', 'note', 'category', 'quantite_vendu_actue', 
            'last_updated', 'discontinued'
        ]
        edited_df = st.data_editor(
            products_df[all_columns],
            use_container_width=True,
            key="product_list_full",
            column_config={
                "reference": st.column_config.TextColumn("Reference", width="medium"),
                "denomination": st.column_config.TextColumn("Name", width="large"),
                "quantite_actuelle": st.column_config.NumberColumn("Current Qty", width="small", disabled=True),
                "prix-détail": st.column_config.NumberColumn("Retail Price", format="%.2f"),
            }
        )
       
    # Permissions check
    if 'role' not in st.session_state.user or st.session_state.user['role'] not in ['admin', 'inventory_manager']:
        st.error("You need elevated privileges to access this page!")
        return
    
    # Database schema enforcement

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
        
        # Configure columns with original database names
        column_config = {
            col: st.column_config.Column(width="medium") 
            for col in all_columns
        }
        # Special configurations
        column_config.update({
            "quantite_actuelle": st.column_config.NumberColumn("quantite_actuelle", disabled=True),
            "prix-super-gros": st.column_config.NumberColumn(format="%.2f"),
            "prix-gros": st.column_config.NumberColumn(format="%.2f"),
            "prix-détail": st.column_config.NumberColumn(format="%.2f"),
        })
        
        edited_df = st.data_editor(
            products_df[all_columns],
            use_container_width=True,
            column_config=column_config,
            key="product_list_full"
        )
        column_config={
                "reference": st.column_config.TextColumn("Reference", width="medium"),
                "denomination": st.column_config.TextColumn("Name", width="large"),
                "quantite_actuelle": st.column_config.NumberColumn("Current Qty", width="small", disabled=True),
                "prix-détail": st.column_config.NumberColumn("Retail Price", format="%.2f"),
            }
        
        st.write("### Select Product to Edit")
        search_query = st.text_input(
            "Search by Reference or Name",
            placeholder="Type reference or name...",
            key="product_search_input"
        )
        
        if search_query:
            filtered_products = products_df[
                products_df['reference'].str.contains(search_query, case=False, na=False) |
                products_df['denomination'].str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_products = products_df
        
        product_options = [
            f"{row['reference']} - {row['denomination']}"
            for _, row in filtered_products.iterrows()
        ]
        
        selected_product_display = st.selectbox(
            "Matching Products",
            options=["Select a product..."] + product_options,
            key="edit_product_select",
            index=0
        )
        
        if selected_product_display != "Select a product..." and selected_product_display:
            selected_ref = selected_product_display.split(" - ")[0]
            product = products_df[products_df['reference'] == selected_ref].iloc[0]
            with st.expander("Edit Product", expanded=True):
                color_fields = [
                    'uni_colour', 'default_colour', 'brown', 'brown_deg', 'blue', 'white', 'black',
                    'green_bottle', 'red', 'grey', 'grey_deg', 'beige', 'yellow', 'orange',
                    'garnet', 'golden', 'green', 'rose'
                ]
                updated_data = {
                    "reference": selected_ref,
                    "denomination": st.text_input("Name", product['denomination']),
                    "quantite_initiale": st.number_input(
                        "Initial Quantity",
                        min_value=0,
                        value=int(product['quantite_initiale']) if pd.notna(product['quantite_initiale']) else 0,
                        format="%d"
                    ),
                    "quantite_restockee": st.number_input(
                        "Restocked Quantity",
                        min_value=0,
                        value=int(product['quantite_restockee']) if pd.notna(product['quantite_restockee']) else 0,
                        format="%d"
                    ),
                    "quantite_vendue": st.number_input(
                        "Sold Quantity",
                        min_value=0,
                        value=int(product['quantite_vendue']) if pd.notna(product['quantite_vendue']) else 0,
                        format="%d"
                    ),
                    "couleurs-dispo-usine": st.text_input("Available Colors", product['couleurs-dispo-usine'] or ""),
                    "images": product['images'] or "",
                    "prix-super-gros": st.number_input(
                        "Super Gros Price",
                        min_value=0.0,
                        value=float(product['prix-super-gros']) if pd.notna(product['prix-super-gros']) else 0.0
                    ),
                    "prix-gros": st.number_input(
                        "Gros Price",
                        min_value=0.0,
                        value=float(product['prix-gros']) if pd.notna(product['prix-gros']) else 0.0
                    ),
                    "prix-détail": st.number_input(
                        "Retail Price",
                        min_value=0.0,
                        value=float(product['prix-détail']) if pd.notna(product['prix-détail']) else 0.0
                    )
                }
                
                # Color quantities
                for color in color_fields:
                    updated_data[color] = st.number_input(
                        color.replace("_", " ").title(),
                        min_value=0,
                        value=int(product[color]) if pd.notna(product[color]) else 0,
                        format="%d",
                        key=f"{color}_{selected_ref}"
                    )
                
                # Calculate and display current quantity
                quantite_actuelle = sum(updated_data[color] for color in color_fields)
                st.write(f"**Current Quantity**: {quantite_actuelle}")
                updated_data["quantite_actuelle"] = quantite_actuelle
                
                # Additional fields
                updated_data.update({
                    "note": st.text_area("Note", product['note'] or ""),
                    "category": st.text_input("Category", product['category'] or ""),
                    "quantite_vendu_actue": st.number_input(
                        "Current Sold Qty",
                        min_value=0,
                        value=int(product['quantite_vendu_actue']) if pd.notna(product['quantite_vendu_actue']) else 0,
                        format="%d"
                    ),
                    "last_updated": product['last_updated'] or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "discontinued": product['discontinued']
                })
                
                # Image handling
                current_images = [img.strip() for img in updated_data['images'].split(',')] if updated_data['images'] else []
                if current_images:
                    st.write("### Current Images")
                    cols = st.columns(min(len(current_images), 4))
                    for idx, img in enumerate(current_images):
                        img_path = os.path.abspath(img)
                        if os.path.exists(img_path):
                            with cols[idx % 4]:
                                st.image(img_path, width=100, caption=os.path.basename(img_path))
                                if st.button(f"Remove {os.path.basename(img_path)}", key=f"rm_{idx}_{selected_ref}"):
                                    current_images.remove(img)
                                    updated_data['images'] = ','.join(current_images)
                                    add_or_update_product(updated_data, is_update=True)
                                    st.rerun()
                        else:
                            with cols[idx % 4]:
                                st.warning(f"Image not found: {img_path}")
                
                available_colors = [c.strip() for c in updated_data['couleurs-dispo-usine'].split(',')] if updated_data['couleurs-dispo-usine'] else []
                selected_color = st.selectbox("Select Color for New Image", available_colors, key=f"color_select_{selected_ref}") if available_colors else None
                
                new_images = st.file_uploader("Add Images", ['jpg', 'png', 'jpeg'], accept_multiple_files=True, key=f"up_{selected_ref}")
                if new_images and selected_color:
                    category = updated_data['category'] or "CHAIR"
                    denomination = updated_data['denomination'].replace(" ", "_")
                    folder_path = os.path.abspath(os.path.join("images", category, denomination))
                    os.makedirs(folder_path, exist_ok=True)
                    
                    for img in new_images:
                        ext = os.path.splitext(img.name)[1].lower()
                        base_name = f"{selected_ref}_{selected_color.upper()}"
                        existing_images_for_color = [i for i in current_images if selected_color.upper() in os.path.basename(i).upper()]
                        new_img_name = f"{base_name}{ext}" if not existing_images_for_color else f"{base_name}-{len(existing_images_for_color) + 1}{ext}"
                        new_img_path = os.path.join(folder_path, new_img_name)
                        with open(new_img_path, "wb") as f:
                            f.write(img.getbuffer())
                        current_images.append(new_img_path)
                        st.success(f"Added {new_img_name}")
                    updated_data['images'] = ','.join(current_images)
                
                if st.button("Save Changes", key=f"save_{selected_ref}"):
                    add_or_update_product(updated_data, is_update=True)
                    st.rerun()
    
    # Tab 2: Import from Excel
    with tab2:
        st.subheader("Import Products")
        uploaded_file = st.file_uploader("Upload Excel File", ['xlsx', 'xls'])
        if uploaded_file and st.button("Import"):
            import_products_from_excel(uploaded_file)
            st.rerun()
        st.download_button(
            "Download Template",
            generate_excel_template(),
            "product_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Tab 3: Add New

    

    with tab3:
        st.subheader("Add New Product")
        new_data = {}  # Collect form data
        
        # Required fields
        cols = st.columns(3)
        new_data['reference'] = cols[0].text_input("Reference*", key="new_ref")
        new_data['denomination'] = cols[1].text_input("Name*", key="new_name")
        new_data['category'] = cols[2].text_input("Category*", key="new_category")
        
        # Validation
        errors = validate_product_data(new_data)
        if errors:
            for error in errors:
                st.error(error)
            return
        
        # Color quantities
        color_fields = [c for c in COLOR_STYLES.keys() if c not in ['default', 'uni_colour']]
        color_quantities = {}
        st.write("### Color Quantities")
        cols = st.columns(4)
        for idx, color in enumerate(color_fields):
            with cols[idx % 4]:
                color_quantities[color] = st.number_input(
                    color.replace("_", " ").title(),
                    min_value=0,
                    value=0,
                    key=f"new_{color}"
                )
        new_data.update(color_quantities)
        
        # Image handling
        st.write("### Product Images")
        selected_color = st.selectbox("Select color for images", color_fields)
        new_images = st.file_uploader("Upload product images", 
                                    type=['jpg', 'png', 'jpeg'],
                                    accept_multiple_files=True)
        
        if new_images:
            try:
                image_paths = handle_product_images(
                    new_data['reference'],
                    new_data['category'],
                    new_data['denomination'],
                    new_images,
                    selected_color
                )
                new_data['images'] = ','.join(image_paths)
            except Exception as e:
                st.error(f"Image upload failed: {str(e)}")
                return
        
        if st.button("Add Product"):
            if add_or_update_product(new_data):
                update_product_stock(new_data['reference'])
                st.success("Product added successfully!")
                st.rerun()

    # Edit Product Section
    with tab1:
        # ... existing product selection ...
        
        if selected_product_display != "Select a product...":
            # Color quantity editing
            st.write("### Stock Management")
            for color in available_colors:
                db_column = get_db_color_name(color)
                current_qty = product.get(db_column, 0)
                updated_qty = st.number_input(
                    f"{color} Stock",
                    value=int(current_qty),
                    min_value=0,
                    key=f"edit_{db_column}"
                )
                updated_data[db_column] = updated_qty
            
            # Automatic stock recalculation
            if st.button("Recalculate Total Stock"):
                update_product_stock(selected_ref)
                st.rerun()
            
            # Image management
            st.write("### Image Management")
            current_images = [img.strip() for img in product['images'].split(',')] if product['images'] else []
            
            # Display images with delete options
            cols = st.columns(4)
            for idx, img_path in enumerate(current_images):
                with cols[idx % 4]:
                    st.image(img_path, width=100)
                    if st.button(f"Delete", key=f"del_img_{idx}"):
                        try:
                            os.remove(img_path)
                            current_images.remove(img_path)
                            add_or_update_product(
                                {"reference": selected_ref, "images": ','.join(current_images)},
                                is_update=True
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {str(e)}")
            
            # Add new images
            new_images = st.file_uploader("Add new images", 
                                         accept_multiple_files=True,
                                         key=f"add_images_{selected_ref}")
            if new_images:
                try:
                    new_paths = handle_product_images(
                        selected_ref,
                        product['category'],
                        product['denomination'],
                        new_images,
                        selected_color
                    )
                    current_images.extend(new_paths)
                    add_or_update_product(
                        {"reference": selected_ref, "images": ','.join(current_images)},
                        is_update=True
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Image upload failed: {str(e)}")


    # Tab 4: Manage Discontinued
    with tab4:
        st.subheader("Discontinued Products")
        discontinued_df = load_products(active_only=False)
        discontinued_df = discontinued_df[discontinued_df['discontinued'] == 1]
        st.dataframe(discontinued_df[['reference', 'denomination', 'last_updated']])
        
        to_discontinue = st.multiselect("Mark as Discontinued", products_df['reference'], key="disc_select")
        if st.button("Mark Selected", key="disc_btn"):
            for ref in to_discontinue:
                mark_discontinued(ref)
            st.rerun()
        
        if is_admin:
            to_delete = st.multiselect("Permanently Delete", discontinued_df['reference'], key="del_select")
            if st.button("Delete Selected", key="del_btn"):
                for ref in to_delete:
                    permanently_delete(ref)
                st.rerun()
    
    # Tab 5: Backup
    with tab5:
        st.subheader("Database Backup")
        if st.button("Create Manual Backup", key="manual_backup"):
            backup_path = backup_database()
            st.success(f"Backup created: {backup_path}")
            with open(backup_path, "rb") as f:
                st.download_button("Download Backup", f, os.path.basename(backup_path), mime="application/octet-stream")
        st.info("Automatic backups are scheduled daily at 00:00.")
    
    # Display confirmation message
    if "add_confirmation" in st.session_state:
        st.success(st.session_state.add_confirmation, icon="✅")
        if st.button("OK", key="clear_add_confirmation"):
            del st.session_state.add_confirmation
            st.rerun()


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
    
    # Start background scheduler
    if 'scheduler_started' not in st.session_state:
        st.session_state['scheduler_started'] = True
        threading.Thread(target=run_scheduled_tasks, daemon=True).start()
    
    initialize_session_state()
    products_df = load_products()
    clients_df = st.session_state['clients_df']
    
    if page == "🏠 Dashboard":
        dashboard_page()
    elif page == "📋 Proforma":
        proforma_page(products_df, clients_df)
    elif page == "🛒 POS":
        pos_page(products_df, clients_df)  # Fixed here
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