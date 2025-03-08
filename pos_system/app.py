import streamlit as st
import pandas as pd
import json
import os
import bcrypt
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from modules.client_management import initialize_clients_df, get_client_info, add_new_client, save_clients, update_client
from modules.product_management import load_products, update_stock, restock_product
from modules.transaction_management import record_transaction, record_expenditure, record_staff_payment, get_till_balance
from modules.pdf_generator import generate_receipt_pdf, generate_proforma_pdf
from modules.proforma import proforma_page
from modules.utils import validate_email, validate_phone, fetch_df_from_db, find_image_path_for_color, get_full_image_path

# Paths
USERS_FILE = "data/users.json"
DB_PATH = "/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db"

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

# Email sending function
def send_email(to_email, subject, body, attachment_path=None):
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

def load_users(force_reset=False):
    default_users = {
        "users": [
            {"username": "admin", "password": bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode(), "role": "admin", "access": ["Proforma", "POS", "Restock", "Expenditures", "Staff Payments", "Till", "Access Control", "Dashboard", "Invoice History", "Activity Log"]},
            {"username": "eulma", "password": bcrypt.hashpw("eulma".encode(), bcrypt.gensalt()).decode(), "role": "operator", "access": ["Proforma", "POS"]},
            {"username": "alger", "password": bcrypt.hashpw("alger".encode(), bcrypt.gensalt()).decode(), "role": "operator", "access": ["Proforma", "POS"]},
            {"username": "constantine", "password": bcrypt.hashpw("constantine".encode(), bcrypt.gensalt()).decode(), "role": "operator", "access": ["Proforma", "POS"]}
        ],
        "access_control_enabled": False
    }
    
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
    initialize_clients_df()

def stock_checker_section(products_df, section_key_prefix=""):
    with st.expander("Vérificateur de Stock", expanded=False):
        search_term = st.text_input("Rechercher par nom ou référence", placeholder="Tapez le nom ou la référence", key=f"{section_key_prefix}stock_search")
        if st.button("Vérifier", key=f"{section_key_prefix}stock_check"):
            filtered_df = products_df[
                products_df['denomination'].str.contains(search_term, case=False, na=False) |
                products_df['reference'].str.contains(search_term, case=False, na=False)
            ]
            if not filtered_df.empty:
                for _, row in filtered_df.iterrows():
                    st.write(f"**{row['denomination']} ({row['reference']})**")
                    st.write(f"- Stock Total: {int(row['quantite_actuelle'])} unités")
                    colors = [color.strip() for color in row['couleurs-dispo-usine'].split(',')] if pd.notna(row['couleurs-dispo-usine']) else []
                    for color in colors:
                        color_lower = color.lower()
                        if color_lower in row.index and pd.notna(row[color_lower]):
                            stock = int(row[color_lower])
                            image_path = get_full_image_path(find_image_path_for_color(row['images'], color))
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                if image_path:
                                    st.image(image_path, width=50)
                                else:
                                    st.write("Image non disponible")
                            with col2:
                                st.write(f"- {color}: {stock} unités")
                                if stock <= 5:
                                    st.warning(f"Alerte: Stock faible pour {color} ({stock} unités restantes)")
                    if row['quantite_actuelle'] <= 5:
                        st.warning(f"Alerte: Stock total faible ({int(row['quantite_actuelle'])} unités restantes)")
            else:
                st.error("Aucun article trouvé.")

def pos_page():
    st.title("Point de Vente (POS)")
    initialize_session_state()
    products_df = load_products()
    clients_df = st.session_state['clients_df']
    transactions_df = fetch_df_from_db('transactions')
    username = st.session_state['user']['username']

    stock_checker_section(products_df, "pos_")

    with st.expander("Gestion des clients", expanded=True):
        client_action = st.radio("Action", ["Client récent", "Rechercher un client", "Ajouter un nouveau client", "Modifier un client chargé", "Récupérer une proforma"], key="pos_client_action")
        if client_action == "Client récent":
            recent_clients = st.session_state['recent_clients']
            if recent_clients:
                st.write("#### Clients récents")
                for client_id in recent_clients:
                    client = clients_df[clients_df['id_client'] == client_id]
                    if not client.empty:
                        client_info = client.iloc[0].to_dict()
                        client_info['index'] = client.index[0]
                        client_name = client_info.get('nom_client', 'Inconnu')
                        if st.button(f"Charger {client_name} (ID: {client_id})", key=f"pos_recent_{client_id}"):
                            st.session_state["client_info_loaded"] = client_info
                            st.session_state["client_index"] = client_info['index']
                            st.success(f"Client {client_name} chargé !")
        elif client_action == "Rechercher un client":
            client_search_method = st.radio("Rechercher par", ["Nom du client", "ID Client"], key="pos_client_search_method")
            client_search_value = st.text_input("Valeur de recherche", placeholder="Tapez le nom du client ou ID", key="pos_client_search_value")
            if st.button("Rechercher client", key="pos_search_client"):
                if client_search_value:
                    client_info = get_client_info(clients_df, client_search_value, client_search_method)
                    if client_info:
                        st.session_state["client_info_loaded"] = client_info
                        st.session_state["client_index"] = client_info['index']
                        st.success(f"Client {client_info.get('nom_client', 'Inconnu')} chargé !")
                    else:
                        st.info("Aucun client trouvé.")
        elif client_action == "Ajouter un nouveau client":
            new_nom_client = st.text_input("Nom du client", placeholder="Tapez le nom du client", key="pos_new_nom_client")
            new_prenom_client = st.text_input("Prénom du client", placeholder="Tapez le prénom", key="pos_new_prenom_client")
            new_nom_entreprise = st.text_input("Nom de l’entreprise", placeholder="Tapez le nom de l’entreprise", key="pos_new_nom_entreprise")
            new_adresse = st.text_input("Adresse", placeholder="Tapez l’adresse", key="pos_new_adresse")
            new_telephone = st.text_input("Telephone", placeholder="Tapez le numéro de téléphone", key="pos_new_telephone")
            new_email = st.text_input("Email du client", placeholder="Tapez l’email", key="pos_new_email")
            if new_email and not validate_email(new_email):
                st.error("Format d'email invalide.")
            if new_telephone and not validate_phone(new_telephone):
                st.error("Le numéro de téléphone doit contenir 10 chiffres.")
            if st.button("Ajouter nouveau client", key="pos_add_new_client"):
                if new_nom_client:
                    new_client_info = {
                        "nom_client": new_nom_client,
                        "prenom_client": new_prenom_client,
                        "entreprise_client": new_nom_entreprise,
                        "address_client": new_adresse,
                        "telephone_client": new_telephone,
                        "email_client": new_email
                    }
                    clients_df = add_new_client(clients_df, new_client_info)
                    if save_clients(clients_df):
                        st.session_state['clients_df'] = clients_df
                        client_info = clients_df.iloc[-1].to_dict()
                        client_info['index'] = len(clients_df) - 1
                        st.session_state["client_info_loaded"] = client_info
                        st.session_state["client_index"] = client_info['index']
                        st.success("Nouveau client ajouté et chargé !")
                        st.session_state['recent_clients'].insert(0, client_info['id_client'])
                        if len(st.session_state['recent_clients']) > 5:
                            st.session_state['recent_clients'].pop()
        elif client_action == "Modifier un client chargé" and "client_info_loaded" in st.session_state:
            client_info = st.session_state["client_info_loaded"]
            edit_nom_client = st.text_input("Nom du client", value=client_info.get("nom_client", ""), placeholder="Tapez le nom du client", key="pos_edit_nom_client")
            edit_prenom_client = st.text_input("Prénom du client", value=client_info.get("prenom_client", ""), placeholder="Tapez le prénom", key="pos_edit_prenom_client")
            edit_nom_entreprise = st.text_input("Nom de l’entreprise", value=client_info.get("entreprise_client", ""), placeholder="Tapez le nom de l’entreprise", key="pos_edit_nom_entreprise")
            edit_adresse = st.text_input("Adresse", value=client_info.get("address_client", ""), placeholder="Tapez l’adresse", key="pos_edit_adresse")
            edit_telephone = st.text_input("Telephone", value=client_info.get("telephone_client", ""), placeholder="Tapez le numéro de téléphone", key="pos_edit_telephone")
            edit_email = st.text_input("Email du client", value=client_info.get("email_client", ""), placeholder="Tapez l’email", key="pos_edit_email")
            if st.button("Sauvegarder les modifications", key="pos_save_edit_client"):
                updated_client_info = {
                    "id_client": client_info["id_client"],
                    "nom_client": edit_nom_client,
                    "prenom_client": edit_prenom_client,
                    "entreprise_client": edit_nom_entreprise,
                    "address_client": edit_adresse,
                    "telephone_client": edit_telephone,
                    "email_client": edit_email
                }
                clients_df = update_client(clients_df, updated_client_info, st.session_state["client_index"])
                if save_clients(clients_df):
                    st.session_state['clients_df'] = clients_df
                    updated_client_info['index'] = st.session_state["client_index"]
                    st.session_state["client_info_loaded"] = updated_client_info
                    st.success("Client modifié avec succès !")
        elif client_action == "Récupérer une proforma":
            proforma_ids = transactions_df[transactions_df['status'] == "proforma"]["transaction_id"].tolist()
            if proforma_ids:
                selected_proforma_id = st.selectbox("Sélectionnez une proforma", proforma_ids, key="pos_proforma_select")
                if st.button("Charger la proforma", key="pos_load_proforma"):
                    proforma = transactions_df[transactions_df['transaction_id'] == selected_proforma_id].iloc[0]
                    client_id = proforma['client_id']
                    client_info = clients_df[clients_df['id_client'] == client_id].iloc[0].to_dict()
                    client_info['index'] = clients_df[clients_df['id_client'] == client_id].index[0]
                    st.session_state["client_info_loaded"] = client_info
                    st.session_state["client_index"] = client_info['index']
                    st.session_state['pos_items'] = json.loads(proforma['items'])
                    st.success(f"Proforma {selected_proforma_id} chargée !")
            else:
                st.info("Aucune proforma disponible.")
        if "client_info_loaded" in st.session_state:
            st.write("#### Client chargé")
            for key, value in st.session_state["client_info_loaded"].items():
                if pd.notna(value):
                    st.write(f"{key}: {value}")

    with st.expander("Articles", expanded=True):
        if 'pos_items' not in st.session_state:
            st.session_state['pos_items'] = []
        barcode = st.text_input("Scanner ou taper la référence", placeholder="Utilisez un scanner ou entrez la référence", key="pos_barcode")
        if barcode and st.button("Ajouter par référence"):
            filtered_df = products_df[products_df['reference'] == barcode]
            if not filtered_df.empty:
                st.session_state['pos_filtered'] = filtered_df
            else:
                st.error("Référence non trouvée.")
        
        search_term = st.text_input("Rechercher par nom ou référence", placeholder="Tapez le nom ou la référence", key="pos_search")
        if st.button("Rechercher"):
            filtered_df = products_df[
                products_df['denomination'].str.contains(search_term, case=False, na=False) |
                products_df['reference'].str.contains(search_term, case=False, na=False)
            ]
            if not filtered_df.empty:
                st.session_state['pos_filtered'] = filtered_df
            else:
                st.error("Aucun article trouvé.")
        
        if 'pos_filtered' in st.session_state:
            filtered_df = st.session_state['pos_filtered']
            selected_item = st.selectbox("Sélectionnez un article", filtered_df['denomination'], key="pos_selected")
            selected_row = filtered_df[filtered_df['denomination'] == selected_item].squeeze()
            price = selected_row['prix-détail'] if pd.notna(selected_row['prix-détail']) else 0.0
            st.write(f"**Prix détail :** {price:.2f} DZD")
            
            total_stock = selected_row.get('quantite_actuelle', 0)
            st.write(f"**Stock Total Disponible :** {int(total_stock)} unités")
            if total_stock <= 5:
                st.warning(f"Alerte: Stock total faible ({int(total_stock)} unités)")
            colors = [color.strip() for color in selected_row['couleurs-dispo-usine'].split(',')] if pd.notna(selected_row['couleurs-dispo-usine']) else []
            selected_color = st.selectbox("Choisissez une couleur", colors, key="pos_color_select") if colors else None
            
            color_stock = 0
            if selected_color:
                color_lower = selected_color.lower()
                if color_lower in selected_row.index and pd.notna(selected_row[color_lower]):
                    color_stock = int(selected_row[color_lower])
                    st.write(f"**Stock pour {selected_color} :** {color_stock} unités")
                    if color_stock <= 5:
                        st.warning(f"Alerte: Stock faible pour {selected_color} ({color_stock} unités)")
                else:
                    st.warning(f"Stock pour {selected_color} non défini.")
            
            image_path = get_full_image_path(find_image_path_for_color(selected_row['images'], selected_color)) if selected_color else None
            if image_path:
                st.image(image_path, caption=f"Aperçu ({selected_color})", width=150)
            
            quantity = st.number_input("Quantité", min_value=1, value=1, key="pos_quantity")
            can_add_item = True
            if selected_color and quantity > color_stock:
                st.error(f"La quantité demandée ({quantity}) dépasse le stock disponible pour {selected_color} ({color_stock}).")
                can_add_item = False
            elif not selected_color and quantity > total_stock:
                st.error(f"La quantité demandée ({quantity}) dépasse le stock total disponible ({int(total_stock)}).")
                can_add_item = False
            
            if st.button("Ajouter", disabled=not can_add_item):
                item_dict = {
                    "denomination": selected_row['denomination'],
                    "reference": selected_row['reference'],
                    "Quantity": quantity,
                    "Price": price,
                    "Color": selected_color,
                    "Image": image_path,
                    "category": selected_row.get('category', 'Sans Catégorie')
                }
                st.session_state['pos_items'].append(item_dict)
                st.success("Article ajouté !")
        
        if st.session_state['pos_items']:
            st.write("#### Articles sélectionnés")
            for i, item in enumerate(st.session_state['pos_items']):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{item['denomination']} - {item['reference']} - Couleur: {item['Color']} - {item['Quantity']} x {item['Price']:.2f}")
                    if item.get('Image'):
                        st.image(item['Image'], width=100)
                with col2:
                    if st.button(f"Supprimer {i+1}", key=f"pos_delete_{i}"):
                        st.session_state['pos_items'].pop(i)
                        st.rerun()

    with st.expander("Paiement", expanded=True):
        if 'pos_items' in st.session_state and st.session_state['pos_items']:
            total_amount = sum(item['Quantity'] * item['Price'] for item in st.session_state['pos_items'])
            discount_type = st.radio("Type de remise", ["Aucune", "Pourcentage", "Montant fixe"], key="pos_discount_type")
            discount_value = st.number_input("Valeur de la remise", min_value=0.0, value=0.0, key="pos_discount_value") if discount_type != "Aucune" else 0.0
            discount_amount = total_amount * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
            final_amount = total_amount - discount_amount
            st.write(f"**Total avant remise :** {total_amount:.2f} DZD")
            if discount_amount > 0:
                st.write(f"**Remise :** {discount_amount:.2f} DZD")
            st.write(f"**Total à payer :** {final_amount:.2f} DZD")

            # Initialize cash amount as the full total initially
            cash_amount = final_amount
            payments = {"Espèces": cash_amount, "Virement bancaire": 0.0, "Chèque": 0.0}

            # Display Montant en Espèces in a large light blue box
            st.markdown(
                f"""
                <div style="background-color: lightblue; padding: 20px; border-radius: 10px; text-align: center;">
                    <h3>Montant</h3>
                    <h1>{cash_amount:.2f} DZD</h1>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Optional payment methods with checkboxes
            use_virement = st.checkbox("Montant en Virement bancaire")
            if use_virement:
                virement_amount = st.number_input("Montant en Virement bancaire", min_value=0.0, value=0.0, key="pos_virement")
                payments["Virement bancaire"] = virement_amount
            else:
                payments["Virement bancaire"] = 0.0

            use_cheque = st.checkbox("Montant en Chèque")
            if use_cheque:
                cheque_amount = st.number_input("Montant en Chèque", min_value=0.0, value=0.0, key="pos_cheque")
                payments["Chèque"] = cheque_amount
            else:
                payments["Chèque"] = 0.0

            # Calculate remaining cash after other payments
            total_other_payments = payments["Virement bancaire"] + payments["Chèque"]
            if total_other_payments > final_amount:
                st.error("Le total des paiements (Virement + Chèque) dépasse le montant à payer !")
                cash_amount = 0.0
            else:
                cash_amount = final_amount - total_other_payments
                payments["Espèces"] = cash_amount

            # Update the displayed cash amount dynamically
            st.markdown(
                f"""
                <div style="background-color: lightblue; padding: 20px; border-radius: 10px; text-align: center;">
                    <h3>Montant à Payer</h3>
                    <h1>{cash_amount:.2f} DZD</h1>
                </div>
                """,
                unsafe_allow_html=True
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Process Sale"):
                    if total_other_payments > final_amount:
                        st.error("Le paiement dépasse le total à payer. Veuillez ajuster les montants.")
                    elif not st.session_state.get("client_info_loaded"):
                        st.error("Chargez un client !")
                    else:
                        if update_stock(products_df, st.session_state['pos_items']):
                            payment_details = "; ".join([f"{k}: {v:.2f}" for k, v in payments.items() if v > 0])
                            transaction_id = record_transaction(
                                st.session_state['client_info_loaded'],
                                st.session_state['pos_items'],
                                payment_details,
                                final_amount,
                                total_amount,
                                status="completed",
                                performed_by=username
                            )
                            transaction_info = {"transaction_number": transaction_id, "transaction_date": datetime.now().strftime("%d/%m/%Y"), "client_id": st.session_state['client_info_loaded']['id_client'], "performed_by": username}
                            pdf_filename = generate_receipt_pdf(transaction_info, st.session_state['pos_items'], final_amount, discount_amount, payment_details)
                            st.session_state['pos_pdf_filename'] = pdf_filename
                            st.session_state['pos_transaction_generated'] = True
                            st.session_state['recent_clients'].insert(0, st.session_state['client_info_loaded']['id_client'])
                            if len(st.session_state['recent_clients']) > 5:
                                st.session_state['recent_clients'].pop()
                            st.success("Vente terminée !")
                            st.rerun()

            if st.session_state.get('pos_transaction_generated', False):
                pdf_filename = st.session_state['pos_pdf_filename']
                with col2:
                    with open(pdf_filename, "rb") as file:
                        st.download_button("Télécharger le reçu", file, pdf_filename, mime="application/pdf", key="pos_download")
                with col3:
                    st.markdown(f'<a href="file://{pdf_filename}" target="_blank"><button>Imprimer le reçu</button></a>', unsafe_allow_html=True)

                client_email = st.session_state['client_info_loaded'].get('email_client', '')
                if client_email and validate_email(client_email):
                    if st.button("Envoyer par email", key="pos_email"):
                        subject = f"Reçu de vente #{transaction_info['transaction_number']}"
                        body = f"Bonjour {st.session_state['client_info_loaded'].get('nom_client', '')},\n\nVoici votre reçu pour la transaction #{transaction_info['transaction_number']}.\nMontant total: {final_amount:.2f} DZD\nEffectué par: {username}\n\nCordialement,\nTakideco"
                        if send_email(client_email, subject, body, pdf_filename):
                            st.success("Reçu envoyé par email !")

            with col2:
                if st.button("Effacer tout"):
                    if 'pos_items' in st.session_state:
                        del st.session_state['pos_items']
                    if 'pos_filtered' in st.session_state:
                        del st.session_state['pos_filtered']
                    if 'client_info_loaded' in st.session_state:
                        del st.session_state['client_info_loaded']
                    if 'pos_transaction_generated' in st.session_state:
                        del st.session_state['pos_transaction_generated']
                    if 'pos_pdf_filename' in st.session_state:
                        del st.session_state['pos_pdf_filename']
                    st.success("Tout effacé !")
                    st.rerun()
        else:
            st.info("Ajoutez des articles pour procéder au paiement.")

def restock_page():
    st.title("Re-stocking")
    products_df = load_products()
    username = st.session_state['user']['username']
    
    stock_checker_section(products_df, "restock_")
    
    with st.expander("Restocker un produit", expanded=True):
        search_term = st.text_input("Rechercher par nom ou référence", placeholder="Tapez le nom ou la référence", key="restock_search")
        if st.button("Rechercher", key="restock_search_btn"):
            filtered_df = products_df[
                products_df['denomination'].str.contains(search_term, case=False, na=False) |
                products_df['reference'].str.contains(search_term, case=False, na=False)
            ]
            if not filtered_df.empty:
                st.session_state['restock_filtered'] = filtered_df
            else:
                st.error("Aucun produit trouvé.")
        
        if 'restock_filtered' in st.session_state:
            filtered_df = st.session_state['restock_filtered']
            selected_item = st.selectbox("Sélectionnez un produit", filtered_df['denomination'], key="restock_selected")
            selected_row = filtered_df[filtered_df['denomination'] == selected_item].squeeze()
            st.write(f"**Référence :** {selected_row['reference']}")
            st.write(f"**Stock actuel :** {int(selected_row['quantite_actuelle'])} unités")
            
            colors = [color.strip() for color in selected_row['couleurs-dispo-usine'].split(',')] if pd.notna(selected_row['couleurs-dispo-usine']) else []
            selected_color = st.selectbox("Choisissez une couleur", colors, key="restock_color_select") if colors else None
            
            image_path = get_full_image_path(find_image_path_for_color(selected_row['images'], selected_color)) if selected_color else None
            if image_path:
                st.image(image_path, caption=f"Aperçu ({selected_color})", width=150)
            else:
                st.write("Image non disponible")
            
            quantity = st.number_input("Quantité à ajouter", min_value=1, key="restock_quantity")
            if st.button("Restocker", key="restock_btn"):
                total_cost = restock_product(products_df, selected_row['reference'], quantity, 0, selected_color)
                record_transaction(None, [{"denomination": selected_row['denomination'], "reference": selected_row['reference'], "Quantity": quantity, "Color": selected_color}], "Restock", 0, 0, "restock", username)
                st.success(f"{quantity} unités de {selected_row['denomination']} ({selected_color}) restockées !")
                del st.session_state['restock_filtered']
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
            access_options = ["Proforma", "POS", "Restock", "Expenditures", "Staff Payments", "Till", "Access Control", "Dashboard", "Invoice History", "Activity Log"]
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

def expenditure_page():
    st.title("Dépenses")
    username = st.session_state['user']['username']
    description = st.text_input("Description de la dépense")
    amount = st.number_input("Montant (DZD)", min_value=0.0)
    if st.button("Enregistrer la dépense"):
        record_expenditure(description, amount, username)
        st.success("Dépense enregistrée !")

def staff_payment_page():
    st.title("Paiements du personnel")
    username = st.session_state['user']['username']
    staff_name = st.text_input("Nom du personnel")
    amount = st.number_input("Montant (DZD)", min_value=0.0)
    note = st.text_area("Note", placeholder="Ajoutez une note (optionnel)")
    if st.button("Enregistrer le paiement"):
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
    
    total_sales = transactions_df[transactions_df['status'] == "completed"]['payment_amount'].sum()
    st.write(f"**Ventes Totales :** {total_sales:.2f} DZD")
    
    top_items = pd.DataFrame([json.loads(t['items']) for t in transactions_df[transactions_df['status'] == "completed"]['items']]).explode().groupby('denomination')['Quantity'].sum().nlargest(5)
    st.write("**Top 5 Articles Vendus :**")
    st.dataframe(top_items)
    
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
        filter_user = st.selectbox("Filtrer par utilisateur", ["Tous"] + sorted(transactions_df['performed_by'].unique().tolist()), key="filter_user")
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

def main():
    if not login():
        return

    user = st.session_state['user']
    menu_options = user["access"]
    st.sidebar.title(f"Menu - {user['username']} ({user['role'].capitalize()})")
    if st.sidebar.button("Déconnexion"):
        st.session_state['logged_in'] = False
        st.session_state['user'] = None
        st.rerun()
    page = st.sidebar.radio("Aller à", menu_options + ["Changer le mot de passe"])
    initialize_session_state()
    products_df = load_products()
    clients_df = st.session_state['clients_df']

    if page == "Proforma":
        proforma_page(products_df, clients_df)
    elif page == "POS":
        pos_page()
    elif page == "Restock":
        restock_page()
    elif page == "Expenditures":
        expenditure_page()
    elif page == "Staff Payments":
        staff_payment_page()
    elif page == "Till":
        till_page()
    elif page == "Access Control":
        access_control_page()
    elif page == "Dashboard":
        dashboard_page()
    elif page == "Invoice History":
        invoice_history_page()
    elif page == "Activity Log":
        activity_log_page()
    elif page == "Changer le mot de passe":
        change_password_page()

if __name__ == "__main__":
    main()