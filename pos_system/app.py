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
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from modules.product_management import (
    handle_product_images, add_or_update_product, load_products,
    generate_excel_template, import_products_from_excel, mark_discontinued,
    permanently_delete, update_product_stock, update_products_schema,
    update_stock, restock_product, validate_product_data
)
from modules.client_management import (
    initialize_clients_df, get_client_info, add_new_client, save_clients, update_client
)
from modules.transaction_management import (
    record_transaction, record_expenditure, record_staff_payment,
    get_till_balance, fetch_df_from_db, initialize_db
)
from modules.pdf_generator import generate_receipt_pdf, generate_proforma_pdf
from modules.proforma import proforma_page
from modules.pos import pos_page
from modules.restock import get_db_color_name, restock_page
from modules.bon_de_commande import bon_de_commande_page
from modules.utils import (
    COLOR_STYLES, validate_email, validate_phone, find_image_path_for_color,
    get_full_image_path, get_db_connection
)

USERS_FILE = "data/users.json"
DB_FILE = "data/pos_system.db"
BACKUP_DIR = "backups"

# Global CSS styling
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
    st.session_state['clients_df'] = initialize_clients_df()

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
        total_sales = transactions_df[transactions_df['status'] == "completed"]['final_amount'].sum()
        st.write(f"**Ventes Totales :** {total_sales:,.2f} DZD")
        
        completed_items = []
        for items in transactions_df[transactions_df['status'] == "completed"]['items']:
            if isinstance(items, list):
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
        time.sleep(60)

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
    st.title("📚 Gestion des Articles")
    
    # Define tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Liste des Produits", "➕ Ajouter un Produit", "✏️ Modifier un Produit", "📤 Importer Excel"])
    
    # Tab 1: Liste des Produits (including delete functionality)
    with tab1:
        st.subheader("Liste des Produits")
        products_df = load_products(active_only=False)  # Show all products, including discontinued
        
        # Display editable table with image previews
        edited_df = st.data_editor(
            products_df,
            column_config={
                "images": st.column_config.ImageColumn("Aperçu", help="Double-cliquez pour agrandir"),
                "reference": st.column_config.TextColumn("Référence", width="medium"),
                "denomination": st.column_config.TextColumn("Dénomination", width="large"),
                "category": st.column_config.TextColumn("Catégorie", width="medium"),
                "quantite_actuelle": st.column_config.NumberColumn("Stock Actuel", min_value=0),
                "prix-détail": st.column_config.NumberColumn("Prix Détail", min_value=0.0, format="%.2f DZD"),
                "discontinued": st.column_config.CheckboxColumn("Discontinué", default=False)
            },
            use_container_width=True,
            height=500,
            num_rows="dynamic"  # Allows adding rows directly in the table
        )
        
        if st.button("Sauvegarder Modifications", key="save_table_changes"):
            conn = get_db_connection()
            try:
                edited_df.to_sql('products', conn, if_exists='replace', index=False)
                conn.commit()
                st.success("Modifications sauvegardées dans la base de données!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Échec de la sauvegarde: {str(e)}")
            finally:
                conn.close()
        
        # Delete product functionality
        with st.expander("Supprimer un Produit", expanded=False):
            ref_to_delete = st.selectbox("Référence à supprimer", products_df['reference'], key="delete_product_select")
            if st.button("Supprimer Définitivement", key="delete_button"):
                if permanently_delete(ref_to_delete):
                    st.success(f"Produit {ref_to_delete} supprimé définitivement!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Échec de la suppression. Vérifiez si des transactions sont associées.")

    # Tab 2: Ajouter un Nouveau Produit
    with tab2:
        st.subheader("Ajouter un Nouveau Produit")
        with st.form("add_product_form"):
            reference = st.text_input("Référence", key="add_ref")
            denomination = st.text_input("Dénomination", key="add_denom")
            category = st.text_input("Catégorie", key="add_cat")
            couleurs_dispo = st.text_input("Couleurs Disponibles (séparées par des virgules)", key="add_colors")
            selected_color = st.selectbox("Couleur pour les images", ["Red", "Blue", "Green", "Default"], key="add_color")
            new_images = st.file_uploader("Images", accept_multiple_files=True, type=["jpg", "png"], key="add_images")
            submit = st.form_submit_button("Ajouter")
            
            if submit:
                if not reference or not denomination:
                    st.error("Référence et Dénomination sont obligatoires.")
                else:
                    product_data = {
                        'reference': reference,
                        'denomination': denomination,
                        'category': category,
                        'couleurs-dispo-usine': couleurs_dispo,
                        'selected_color': selected_color,
                        'new_images': new_images
                    }
                    try:
                        images = handle_product_images(reference, category, denomination, new_images, selected_color)
                        product_data['images'] = images
                        if add_or_update_product(product_data, is_update=False):
                            st.success("Produit ajouté avec succès!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Échec de l'ajout du produit.")
                    except Exception as e:
                        st.error(f"Erreur lors de l'ajout: {str(e)}")

    # Tab 3: Modifier un Produit

    with tab3:
        st.subheader("Modifier un Produit")
        products = load_products(active_only=False)
        selected_ref = st.selectbox("Sélectionner un produit à modifier", products['reference'], key="edit_product_select")
        if selected_ref:
            product = products[products['reference'] == selected_ref].iloc[0]
            with st.form("edit_product_form"):
                reference = st.text_input("Référence", value=product['reference'], disabled=True, key="edit_ref")
                denomination = st.text_input("Dénomination", value=product['denomination'], key="edit_denom")
                category = st.text_input("Catégorie", value=product['category'], key="edit_cat")
                couleurs_dispo = st.text_input("Couleurs Disponibles", value=product['couleurs-dispo-usine'], key="edit_colors")
                selected_color = st.selectbox("Couleur pour les images", ["Red", "Blue", "Green", "Default"], key="edit_color")
                new_images = st.file_uploader("Nouvelles Images", accept_multiple_files=True, type=["jpg", "png"], key="edit_images")
                delete_existing = st.checkbox("Remplacer les images existantes", key="edit_delete_images")
                submit = st.form_submit_button("Mettre à jour")
                
                if submit:
                    product_data = {
                        'reference': reference,
                        'denomination': denomination,
                        'category': category,
                        'couleurs-dispo-usine': couleurs_dispo,
                        'selected_color': selected_color,
                        'new_images': new_images,
                        'images': product['images']  # Preserve existing unless replaced
                    }
                    try:
                        images = handle_product_images(reference, category, denomination, new_images, selected_color, delete_existing)
                        product_data['images'] = images if images else product['images']
                        if add_or_update_product(product_data, is_update=True):
                            st.success("Produit mis à jour avec succès!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Échec de la mise à jour du produit.")
                    except Exception as e:
                        st.error(f"Erreur lors de la mise à jour: {str(e)}")

    # Tab 4: Importer Excel
    with tab4:
        st.subheader("Importer depuis Excel")
        uploaded_file = st.file_uploader("Télécharger fichier Excel", type=["xlsx"], key="excel_upload")
        if uploaded_file:
            if st.button("Importer", key="import_button"):
                if import_products_from_excel(uploaded_file):
                    st.success("Importation réussie!")
                    st.rerun()
                else:
                    st.error("Échec de l'importation. Vérifiez le fichier et réessayez.")
        st.download_button(
            "Télécharger Modèle",
            generate_excel_template(),
            "modele_produits.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_template"
        )

def access_control_page():
    st.title("Contrôle d'accès")
    if st.session_state['user']['role'] != "admin":
        st.error("Accès réservé à l'administrateur.")
        return
    if 'schema_updated' not in st.session_state:
        st.session_state['schema_updated'] = False
    if st.button("Update Database Schema") and not st.session_state['schema_updated']:
        update_products_schema()
        st.session_state['schema_updated'] = True
        st.success("Database schema updated!")
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
    initialize_db()
    if not login():
        return
    user = st.session_state['user']
    if not user:
        st.error("User session not initialized. Please log in again.")
        return
    menu_options = user.get("access", [])
    
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