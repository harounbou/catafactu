import streamlit as st
import pandas as pd
from datetime import datetime
from .client_management import get_client_info, add_new_client, save_clients, update_client
from .transaction_management import record_transaction, get_proformas
from .pdf_generator import generate_proforma_pdf
from .utils import validate_email, validate_phone, find_image_path_for_color, get_full_image_path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib
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
    st.title("Générateur de Facture Proforma")
    username = st.session_state['user']['username']

    # Initialize session state
    if 'proforma_items' not in st.session_state:
        st.session_state.proforma_items = []
    if 'proforma_client' not in st.session_state:
        st.session_state.proforma_client = None
    if 'show_onama' not in st.session_state:
        st.session_state.show_onama = False
    if 'generated_pdf' not in st.session_state:
        st.session_state.generated_pdf = None

    with st.expander("Configuration de la Proforma", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            price_type = st.radio("Type de prix", 
                ["prix-super-gros", "prix-gros", "prix-détail"])
            apply_tva = st.checkbox("Appliquer TVA 19%")
            show_onama = st.checkbox("Basculer à l’ONAMA")
            st.session_state.show_onama = show_onama
        with col2:
            discount_type = st.selectbox("Type de remise", 
                ["Pourcentage", "Montant fixe"])
            discount_value = st.number_input("Valeur", min_value=0.0)
        
        delivery_days = st.slider("Délai de livraison (jours)", 0, 30, 7)
        custom_notes = st.text_area("Notes personnalisées")

    # Client management
    with st.expander("Gestion Client", expanded=True):
        client_action = st.radio("Action Client", 
            ["Nouveau Client", "Client Existant"])
        
        if client_action == "Client Existant":
            client_search_value = st.text_input("Rechercher par nom ou ID", placeholder="Tapez le nom ou l'ID du client")
            if st.button("Rechercher Client"):
                if client_search_value:
                    # Try searching by ID first
                    try:
                        client_id = int(client_search_value)
                        client_info = get_client_info(clients_df, client_search_value, "ID Client")
                    except ValueError:
                        # If not an ID, search by name
                        client_info = get_client_info(clients_df, client_search_value, "Nom du client")
                    
                    if client_info:
                        st.session_state.proforma_client = client_info
                        st.success("Client trouvé!")
                        # Display client details
                        st.write("#### Détails du client")
                        for key, value in client_info.items():
                            if pd.notna(value) and key != 'index':
                                st.write(f"{key}: {value}")
                    else:
                        st.error("Client non trouvé")
        
        else:
            new_client = {
                'nom_client': st.text_input("Nom"),
                'prenom_client': st.text_input("Prénom"),
                'entreprise_client': st.text_input("Entreprise"),
                'telephone_client': st.text_input("Téléphone"),
                'email_client': st.text_input("Email")
            }
            if st.button("Enregistrer Nouveau Client"):
                if new_client['nom_client']:
                    clients_df = add_new_client(clients_df, new_client)
                    save_clients(clients_df)
                    st.session_state.proforma_client = clients_df.iloc[-1].to_dict()
                    st.session_state.proforma_client['index'] = len(clients_df) - 1
                    st.success("Client enregistré!")
                    # Display new client details
                    st.write("#### Détails du client")
                    for key, value in st.session_state.proforma_client.items():
                        if pd.notna(value) and key != 'index':
                            st.write(f"{key}: {value}")

    # Item selection
    with st.expander("Sélection d'Articles", expanded=True):
        search_term = st.text_input("Recherche par référence/nom")
        if st.button("Rechercher Articles"):
            filtered = products_df[
                (products_df['reference'].str.contains(search_term, case=False, na=False)) |
                (products_df['denomination'].str.contains(search_term, case=False, na=False))
            ]
            st.session_state.proforma_filtered = filtered if not filtered.empty else None

        if 'proforma_filtered' in st.session_state and st.session_state.proforma_filtered is not None:
            selected_product = st.selectbox("Articles Disponibles", 
                st.session_state.proforma_filtered['denomination'])
            
            product = st.session_state.proforma_filtered[
                st.session_state.proforma_filtered['denomination'] == selected_product
            ].iloc[0]

            # Color selection
            colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
            color = st.selectbox("Couleur", colors) if colors else None
            
            # Show item image
            image_path = get_full_image_path(find_image_path_for_color(product['images'], color)) if color else None
            if image_path:
                st.image(image_path, caption=f"Aperçu ({color})", width=150)

            qty = st.number_input("Quantité", min_value=1, value=1)
            
            if st.button("Ajouter au Panier"):
                item = {
                    "reference": product['reference'],
                    "denomination": product['denomination'],
                    "Quantity": qty,
                    "Price": product[price_type],
                    "Color": color,
                    "Image": image_path
                }
                st.session_state.proforma_items.append(item)
                st.success("Article ajouté!")

    # Current items
    if st.session_state.proforma_items:
        with st.expander("Articles Sélectionnés", expanded=True):
            for idx, item in enumerate(st.session_state.proforma_items):
                cols = st.columns([1, 4, 1])
                with cols[0]:
                    if item.get('Image'):
                        st.image(item['Image'], width=50)
                with cols[1]:
                    st.write(f"{item['denomination']} ({item['reference']}) - {item['Quantity']}x {item['Price']:.2f} DZD")
                with cols[2]:
                    if st.button("Supprimer", key=f"del_{idx}"):
                        del st.session_state.proforma_items[idx]
                        st.rerun()

    # Generate proforma
    if st.button("Générer Proforma"):
        if not st.session_state.proforma_items:
            st.error("Ajoutez des articles avant de générer!")
            return
        
        if not st.session_state.proforma_client:
            st.error("Sélectionnez ou créez un client!")
            return

        try:
            total = sum(item['Price'] * item['Quantity'] for item in st.session_state.proforma_items)
            
            # Record transaction (fixed keyword argument from 'client' to 'client_info')
            transaction_id = record_transaction(
                client_info=st.session_state.proforma_client,
                items=st.session_state.proforma_items,
                payment_details="Proforma",
                payment_amount=0,
                total_amount=total,
                status="proforma",
                performed_by=username
            )

            # Transaction info for PDF
            transaction_info = {
                "transaction_number": transaction_id,
                "transaction_date": datetime.now().strftime("%d/%m/%Y"),
                "client_id": st.session_state.proforma_client.get('id_client'),
                "performed_by": username
            }

            # Generate PDF
            pdf_path = generate_proforma_pdf(
                items=st.session_state.proforma_items,
                price_type=price_type,
                client_info=st.session_state.proforma_client,
                transaction_info=transaction_info,
                apply_tva=apply_tva,
                discount_type=discount_type,
                discount_value=discount_value,
                show_onama=st.session_state.show_onama,
                delivery_days=delivery_days,
                notes=custom_notes
            )

            # Success handling
            st.session_state.generated_pdf = pdf_path
            st.success(f"Proforma {transaction_id} générée!")

        except Exception as e:
            st.error(f"Erreur: {str(e)}")
            return

    # Post-generation actions
    if st.session_state.get('generated_pdf'):
        pdf_path = st.session_state.generated_pdf
        col1, col2, col3 = st.columns(3)
        
        with col1:
            with open(pdf_path, "rb") as f:
                st.download_button("Télécharger PDF", f, file_name=os.path.basename(pdf_path), key="proforma_download")
        
        with col2:
            st.markdown(f'<a href="file://{pdf_path}" target="_blank"><button>Imprimer PDF</button></a>', unsafe_allow_html=True)
        
        with col3:
            client_email = st.session_state.proforma_client.get('email_client', '')
            if client_email and validate_email(client_email):
                if st.button("Envoyer par email", key="proforma_email"):
                    subject = f"Facture Proforma #{transaction_id}"
                    body = f"Bonjour {st.session_state.proforma_client.get('nom_client', '')},\n\nVoici votre facture proforma #{transaction_id}.\nMontant total: {total:.2f} DZD\nEffectué par: {username}\n\nCordialement,\nTakideco"
                    if send_email(client_email, subject, body, pdf_path):
                        st.success("Proforma envoyée par email !")
            else:
                st.warning("Email client non valide ou non fourni.")