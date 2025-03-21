# modules/proforma.py
import streamlit as st
import pandas as pd
from datetime import datetime
from .client_management import get_client_info, add_new_client, save_clients, update_client
from .transaction_management import record_transaction, get_proformas
from .pdf_generator import generate_proforma_pdf
from .utils import validate_email, validate_phone, find_image_path_for_color, get_full_image_path
from .pos import stock_checker_section
from .product_management import check_stock
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

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

def proforma_page(products_df, clients_df):
    st.title("📄 Générateur de Facture Proforma")
    username = st.session_state['user']['username']
    
    # Initialize session state
    if 'proforma_items' not in st.session_state:
        st.session_state.proforma_items = []
    if 'proforma_client' not in st.session_state:
        st.session_state.proforma_client = None
    if 'generated_pdf' not in st.session_state:
        st.session_state.generated_pdf = None

    # Stock Checker Section
    with st.expander("🔍 Vérificateur de Stock", expanded=False):
        stock_checker_section(products_df, "proforma_")

    # Proforma Configuration
    with st.expander("⚙️ Configuration de la Proforma", expanded=True):
        cols = st.columns([1, 1, 2])
        with cols[0]:
            price_type = st.radio("Type de prix", ["prix-super-gros", "prix-gros", "prix-détail"],
                                  horizontal=True, help="Sélectionnez le niveau de prix approprié")
        with cols[1]:
            discount_type = st.selectbox("Type de remise", ["Pourcentage", "Montant fixe"])
            discount_value = st.number_input("Valeur Remise", min_value=0.0, format="%.2f", step=0.5)
        with cols[2]:
            st.markdown("**Options Avancées**")
            col21, col22 = st.columns(2)
            with col21:
                apply_tva = st.checkbox("Appliquer TVA 19%")
                delivery_days = st.slider("Délai Livraison (jours)", 0, 30, 7)
            with col22:
                show_onama = st.checkbox("Format ONAMA")
                custom_notes = st.text_area("Notes", height=80)

    # Client Management
    with st.expander("👤 Gestion Client", expanded=True):
        client_action = st.radio("Action", ["Nouveau Client", "Client Existant"],
                                 horizontal=True, label_visibility="collapsed")
        
        if client_action == "Client Existant":
            search_input = st.text_input("Recherche Client (2+ caractères)",
                                         placeholder="Nom, entreprise ou téléphone",
                                         help="Commencez à taper pour filtrer les clients")
            
            if len(search_input) >= 2:
                filtered_clients = clients_df[
                    (clients_df['nom_client'].str.contains(search_input, case=False)) |
                    (clients_df['entreprise_client'].str.contains(search_input, case=False)) |
                    (clients_df['telephone_client'].str.contains(search_input))
                ]
                if not filtered_clients.empty:
                    selected_client = st.selectbox("Sélectionnez Client",
                                                   filtered_clients['nom_client'],
                                                   format_func=lambda x: f"{x} ({filtered_clients[filtered_clients['nom_client'] == x]['entreprise_client'].iloc[0]})")
                    if st.button("🔍 Charger Client", type="primary"):
                        client_id = filtered_clients[filtered_clients['nom_client'] == selected_client].iloc[0]['id_client']
                        client_info = get_client_info(clients_df, client_id, "ID Client")
                        if client_info:
                            st.session_state.proforma_client = client_info
                            st.success("Client chargé avec succès!")
                else:
                    st.info("Aucun client trouvé")
        else:
            with st.form("new_client_form"):
                cols = st.columns(2)
                new_client = {
                    'nom_client': cols[0].text_input("Nom*", key="new_nom"),
                    'prenom_client': cols[1].text_input("Prénom", key="new_prenom"),
                    'entreprise_client': cols[0].text_input("Entreprise", key="new_entreprise"),
                    'telephone_client': cols[1].text_input("Téléphone", key="new_telephone"),
                    'email_client': cols[0].text_input("Email*", key="new_email"),
                    'address_client': cols[1].text_input("Adresse", key="new_address")
                }
                if st.form_submit_button("📩 Enregistrer Nouveau Client", type="primary"):
                    if new_client['nom_client'] and new_client['email_client']:
                        clients_df = add_new_client(clients_df, new_client)
                        save_clients(clients_df)
                        st.session_state.proforma_client = clients_df.iloc[-1].to_dict()
                        st.success("Client enregistré avec succès!")

    # Item Selection
    with st.expander("🛒 Sélection d'Articles", expanded=True):
        search_cols = st.columns([3, 1])
        with search_cols[0]:
            search_term = st.text_input("Recherche Articles", placeholder="Référence ou dénomination")
        with search_cols[1]:
            if st.button("🔎 Rechercher", use_container_width=True):
                filtered = products_df[
                    (products_df['reference'].str.contains(search_term, case=False, na=False)) |
                    (products_df['denomination'].str.contains(search_term, case=False, na=False))
                ]
                st.session_state.proforma_filtered = filtered if not filtered.empty else None

        if 'proforma_filtered' in st.session_state and st.session_state.proforma_filtered is not None:
            selected_product = st.selectbox(
                "Articles Disponibles",
                st.session_state.proforma_filtered['denomination'],
                format_func=lambda x: f"{x} ({st.session_state.proforma_filtered[st.session_state.proforma_filtered['denomination'] == x]['reference'].iloc[0]})"
            )
            product = st.session_state.proforma_filtered[
                st.session_state.proforma_filtered['denomination'] == selected_product
            ].iloc[0]
            
            colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
            color = None
            full_selected_path = None
            
            if colors:
                color_cols = st.columns([2, 1])
                with color_cols[0]:
                    color = st.selectbox("Couleur", colors, format_func=lambda x: f"⬤ {x}")
                with color_cols[1]:
                    if color:
                        full_selected_path = find_image_path_for_color(product['images'], color)
                        if full_selected_path:
                            st.image(get_full_image_path(full_selected_path), caption=color, width=80)

            qty = st.number_input("Quantité", min_value=1, value=1, format="%d")
            
            if st.button("➕ Ajouter au Panier", type="primary", use_container_width=True):
                item = {
                    "reference": product['reference'],
                    "denomination": product['denomination'],
                    "Quantity": qty,
                    "Price": product[price_type],
                    "Color": color,
                    "Image": get_full_image_path(full_selected_path) if full_selected_path else None
                }
                st.session_state.proforma_items.append(item)
                st.success("Article ajouté au panier!")

    # Cart Display
    if st.session_state.proforma_items:
        with st.expander(f"📦 Articles Sélectionnés ({len(st.session_state.proforma_items)})", expanded=True):
            for idx, item in enumerate(st.session_state.proforma_items):
                cols = st.columns([1, 3, 1, 1])
                with cols[0]:
                    if item['Image'] and os.path.exists(item['Image']):
                        st.image(item['Image'], width=60)
                with cols[1]:
                    st.markdown(f"**{item['denomination']}**  \nRéf: `{item['reference']}`  \nCouleur: {item['Color']}")
                with cols[2]:
                    st.markdown(f"**{item['Quantity']}x**  \n{item['Price']:.2f} DZD")
                with cols[3]:
                    st.button("🗑️", key=f"del_{idx}", on_click=lambda idx=idx: st.session_state.proforma_items.pop(idx))
            
            st.markdown("---")
            subtotal = sum(item['Price'] * item['Quantity'] for item in st.session_state.proforma_items)
            
            btn_cols = st.columns([1, 1, 2])
            with btn_cols[0]:
                if st.button("🧹 Vider Panier", type="secondary"):
                    st.session_state.proforma_items = []
                    st.rerun()
            with btn_cols[2]:
                if st.button("📄 Générer Proforma", type="primary", disabled=not st.session_state.proforma_client):
                    try:
                        subtotal = sum(item['Price'] * item['Quantity'] for item in st.session_state.proforma_items)
                        discount = subtotal * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
                        taxable = subtotal - discount
                        tva_amount = taxable * 0.19 if apply_tva else 0
                        total = taxable + tva_amount  # Total due, but not paid yet for proforma

                        transaction_id = record_transaction(
                            client_info=st.session_state.proforma_client,
                            items=st.session_state.proforma_items,
                            total_amount=subtotal,  # Subtotal before discount/tax
                            payment_details="Proforma",
                            final_amount=0,         # No payment made for proforma
                            status="proforma",
                            performed_by=username,
                            tva_applied=apply_tva,  # Whether TVA is applied
                            tva_amount=tva_amount   # Amount of TVA if applied
                        )
                        transaction_info = {
                            "transaction_number": transaction_id,
                            "transaction_date": datetime.now().strftime("%d/%m/%Y"),
                            "client_id": st.session_state.proforma_client.get('id_client'),
                            "performed_by": username
                        }
                        pdf_path = generate_proforma_pdf(
                            items=st.session_state.proforma_items,
                            price_type=price_type,
                            client_info=st.session_state.proforma_client,
                            transaction_info=transaction_info,
                            apply_tva=apply_tva,
                            discount_type=discount_type,
                            discount_value=discount_value,
                            show_onama=show_onama,
                            delivery_days=delivery_days,
                            notes=custom_notes
                        )
                        st.session_state.generated_pdf = pdf_path
                        st.success(f"Proforma {transaction_id} générée avec succès!")
                    except Exception as e:
                        st.error(f"Erreur lors de la génération: {str(e)}")

    # PDF Actions
    if st.session_state.get('generated_pdf'):
        pdf_path = st.session_state.generated_pdf
        cols = st.columns([1, 1, 1, 2])
        with cols[0]:
            with open(pdf_path, "rb") as f:
                st.download_button("💾 Télécharger PDF", f,
                                   file_name=os.path.basename(pdf_path),
                                   key="proforma_download")
        with cols[1]:
            st.markdown(f'<a href="file://{pdf_path}" target="_blank"><button>🖨️ Imprimer PDF</button></a>',
                        unsafe_allow_html=True)
        with cols[2]:
            client_email = st.session_state.proforma_client.get('email_client', '')
            if client_email and validate_email(client_email):
                if st.button("📧 Envoyer par email", type="primary"):
                    subject = f"Facture Proforma #{transaction_id}"
                    body = f"""Bonjour {st.session_state.proforma_client.get('nom_client', '')},
                    
Voici votre facture proforma #{transaction_id}.
Montant total: {total:.2f} DZD
Effectué par: {username}

Cordialement,
Takideco"""
                    if send_email(client_email, subject, body, pdf_path):
                        st.success("Email envoyé avec succès!")