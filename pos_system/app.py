# app.py
import streamlit as st
import pandas as pd
import json
import os
import bcrypt
from datetime import datetime
from modules.client_management import initialize_clients_df, get_client_info, add_new_client, save_clients, update_client
from modules.product_management import load_products, update_stock, restock_product
from modules.transaction_management import record_transaction, record_expenditure, record_staff_payment, get_till_balance, fetch_df_from_db
from modules.pdf_generator import generate_receipt_pdf, generate_proforma_pdf, generate_order_pdf
from modules.proforma import proforma_page
from modules.pos import pos_page
from modules.restock import restock_page
from modules.bon_de_commande import bon_de_commande_page
from modules.utils import validate_email, validate_phone, find_image_path_for_color, get_full_image_path, send_email
from modules.utils import get_db_connection


# Paths
USERS_FILE = "data/users.json"

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

    # Check if transactions_df is empty
    if transactions_df.empty:
        st.info("Aucune transaction enregistrée pour le moment.")
    else:
        total_sales = transactions_df[transactions_df['status'] == "completed"]['payment_amount'].sum()
        st.write(f"**Ventes Totales :** {total_sales:.2f} DZD")
        completed_items = []
        for items_json in transactions_df[transactions_df['status'] == "completed"]['items']:
            try:
                items = json.loads(items_json)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and 'denomination' in item and 'Quantity' in item:
                            completed_items.append(item)
            except json.JSONDecodeError as e:
                st.warning(f"Failed to parse items JSON: {e}")
        if completed_items:
            top_items = pd.DataFrame(completed_items).groupby('denomination')['Quantity'].sum().nlargest(5)
            st.write("**Top 5 Articles Vendus :**")
            st.dataframe(top_items)
        else:
            st.write("**Top 5 Articles Vendus :** Aucun article vendu trouvé.")
    
    till_balance = get_till_balance()
    st.write(f"**Solde de la Caisse :** {till_balance:.2f} DZD")

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

def articles_page():
    st.title("Gestion des Articles")
    products_df = load_products()
    
    # Ensure 'couleurs-dispo-usine' is always included and formatted
    if 'couleurs-dispo-usine' not in products_df.columns:
        products_df['couleurs-dispo-usine'] = ''
    
    # Display all columns, including available colors
    edited_df = st.data_editor(
        products_df[['reference', 'denomination', 'quantite_actuelle', 'couleurs-dispo-usine', 'golden', 'white', 'black']],
        column_config={
            "couleurs-dispo-usine": st.column_config.TextColumn("Couleurs Disponibles", width="medium")
        },
        use_container_width=True,
        key="articles_editor"
    )
    
    selected_product = st.selectbox(
        "Sélectionner un produit pour gérer les couleurs",
        products_df['denomination'],
        key="articles_select_product"
    )
    product = products_df[products_df['denomination'] == selected_product].iloc[0]
    colors = st.text_input(
        "Couleurs disponibles (séparées par des virgules)",
        value=product['couleurs-dispo-usine'],
        key="articles_colors_input"
    )
    
    if st.button("Mettre à jour les couleurs", key="articles_update_colors"):
        conn = get_db_connection()
        conn.execute("UPDATE products SET `couleurs-dispo-usine` = ? WHERE reference = ?", (colors, product['reference']))
        conn.commit()
        conn.close()
        st.success("Couleurs mises à jour !")
        st.rerun()
    
    if st.button("Sauvegarder", key="articles_save"):
        conn = get_db_connection()
        edited_df.to_sql('products', conn, if_exists='replace', index=False)
        conn.close()
        st.success("Articles mis à jour !")
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
    if st.sidebar.button("Déconnexion", key="logout_button"):  # Added unique key
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
        pos_page()
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