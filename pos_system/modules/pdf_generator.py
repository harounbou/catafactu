# modules/pdf_generator.py
from fpdf import FPDF
import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from num2words import num2words
from .utils import sanitize_text, calculate_image_dimensions, truncate_text, get_full_image_path, find_image_path_for_color
from .client_management import get_client_info, add_new_client, save_clients
from .transaction_management import record_transaction
from .utils import validate_email

def send_email(to_email, subject, body, attachment_path=None):
    """Send an email with an optional PDF attachment using Gmail SMTP."""
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
    """Generate a proforma invoice interactively in Streamlit."""
    st.title("Générateur de Facture Proforma")
    username = st.session_state['user']['username']
    if 'proforma_items' not in st.session_state:
        st.session_state.proforma_items = []
    if 'proforma_client' not in st.session_state:
        st.session_state.proforma_client = None
    if 'show_onama' not in st.session_state:
        st.session_state.show_onama = False
    if 'generated_pdf' not in st.session_state:
        st.session_state.generated_pdf = None

    # Stock Checker
    with st.expander("Vérificateur de Stock", expanded=False):
        stock_search = st.text_input("Rechercher un article pour vérifier le stock", key="stock_search_proforma")
        if stock_search:
            filtered_products = products_df[
                (products_df['reference'].str.contains(stock_search, case=False, na=False)) |
                (products_df['denomination'].str.contains(stock_search, case=False, na=False))
            ]
            if not filtered_products.empty:
                for _, product in filtered_products.iterrows():
                    st.write(f"**{product['denomination']} ({product['reference']})**")
                    st.write(f"Stock Total: {product['quantite_actuelle']}")
                    colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
                    for color in colors:
                        color_lower = color.lower()
                        st.write(f"{color.capitalize()}: {product.get(color_lower, 'N/A')}")
            else:
                st.warning("Aucun article trouvé.")

    # Proforma Configuration
    with st.expander("Configuration de la Proforma", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            price_type = st.radio("Type de prix", ["prix-super-gros", "prix-gros", "prix-détail"], key="proforma_price_type")
            apply_tva = st.checkbox("Appliquer TVA 19%", key="proforma_tva")
            show_onama = st.checkbox("Basculer à l’ONAMA", key="proforma_onama")
            st.session_state.show_onama = show_onama
        with col2:
            discount_type = st.selectbox("Type de remise", ["Pourcentage", "Montant fixe"], key="proforma_discount_type")
            discount_value = st.number_input("Valeur", min_value=0.0, key="proforma_discount_value")
        delivery_days = st.slider("Délai de livraison (jours)", 0, 30, 7, key="proforma_delivery_days")
        custom_notes = st.text_area("Notes personnalisées", key="proforma_notes")

    # Client Management
    with st.expander("Gestion Client", expanded=True):
        client_action = st.radio("Action Client", ["Nouveau Client", "Client Existant"], key="proforma_client_action")
        if client_action == "Client Existant":
            search_input = st.text_input(
                "Rechercher par nom (autocomplétion)",
                placeholder="Tapez 2+ caractères",
                key="proforma_client_search"
            )
            if len(search_input) >= 2:
                filtered_clients = clients_df[clients_df['nom_client'].str.lower().str.startswith(search_input.lower())]
                client_options = [f"{row['nom_client']} {row['prenom_client']} (ID: {row['id_client']})" for _, row in filtered_clients.iterrows()]
            else:
                client_options = ["Commencez à taper pour voir les options..."]
            selected_client = st.selectbox("Sélectionnez un client", client_options, key="proforma_client_select")
            if st.button("Charger Client", key="proforma_load_client"):
                if selected_client and "ID:" in selected_client:
                    client_id = int(selected_client.split("ID: ")[1].strip(")"))
                    client_info = get_client_info(clients_df, client_id, "ID Client")
                    if client_info:
                        st.session_state.proforma_client = client_info
                        st.success("Client chargé!")
                        st.write("#### Détails du client", client_info)
        else:
            new_client = {
                'nom_client': st.text_input("Nom", key="proforma_new_nom"),
                'prenom_client': st.text_input("Prénom", key="proforma_new_prenom"),
                'entreprise_client': st.text_input("Entreprise", key="proforma_new_entreprise"),
                'telephone_client': st.text_input("Téléphone", key="proforma_new_phone"),
                'email_client': st.text_input("Email", key="proforma_new_email"),
                'address_client': st.text_input("Adresse", key="proforma_new_address")
            }
            if st.button("Enregistrer Nouveau Client", key="proforma_save_client"):
                if new_client['nom_client']:
                    clients_df = add_new_client(clients_df, new_client)
                    save_clients(clients_df)
                    st.session_state.proforma_client = clients_df.iloc[-1].to_dict()
                    st.success("Client enregistré!")
                    st.write("#### Détails du client", st.session_state.proforma_client)

    # Item Selection
    with st.expander("Sélection d'Articles", expanded=True):
        search_term = st.text_input("Recherche par référence/nom", key="proforma_item_search")
        if st.button("Rechercher Articles", key="proforma_search_items"):
            filtered = products_df[
                (products_df['reference'].str.contains(search_term, case=False, na=False)) |
                (products_df['denomination'].str.contains(search_term, case=False, na=False))
            ]
            st.session_state.proforma_filtered = filtered if not filtered.empty else None
        if 'proforma_filtered' in st.session_state and st.session_state.proforma_filtered is not None:
            selected_product = st.selectbox("Articles Disponibles", st.session_state.proforma_filtered['denomination'], key="proforma_product_select")
            product = st.session_state.proforma_filtered[st.session_state.proforma_filtered['denomination'] == selected_product].iloc[0]
            colors = [c.strip() for c in product['couleurs-dispo-usine'].split(',')] if pd.notna(product['couleurs-dispo-usine']) else []
            color = st.selectbox("Couleur", colors, key="proforma_color_select") if colors else None
            image_path = get_full_image_path(find_image_path_for_color(product['images'], color)) if color else None
            if image_path:
                st.image(image_path, caption=f"Aperçu ({color})", width=150)
            qty = st.number_input("Quantité", min_value=1, value=1, max_value=10000, key=f"proforma_qty_{search_term}")
            if st.button("Ajouter au Panier", key="proforma_add_item"):
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

    # Selected Items
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
                    if st.button("Supprimer", key=f"proforma_del_{idx}"):
                        del st.session_state.proforma_items[idx]
                        st.rerun()
            if st.button("Vider le Panier", key="proforma_clear_items"):
                st.session_state.proforma_items = []
                st.rerun()
            subtotal = sum(item['Price'] * item['Quantity'] for item in st.session_state.proforma_items)
            st.write(f"**Total estimé (HT):** {subtotal:.2f} DZD")

    # Generate Proforma
    if st.button("Générer Proforma", key="proforma_generate"):
        if not st.session_state.proforma_items:
            st.error("Ajoutez des articles avant de générer!")
            return
        if not st.session_state.proforma_client:
            st.error("Sélectionnez ou créez un client!")
            return
        total = sum(item['Price'] * item['Quantity'] for item in st.session_state.proforma_items)
        transaction_id = record_transaction(
            client_info=st.session_state.proforma_client,
            items=st.session_state.proforma_items,
            payment_details="Proforma",
            payment_amount=0,
            total_amount=total,
            status="proforma",
            performed_by=username
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
            show_onama=st.session_state.show_onama,
            delivery_days=delivery_days,
            notes=custom_notes
        )
        st.session_state.generated_pdf = pdf_path
        st.success(f"Proforma {transaction_id} générée!")

    # PDF Actions
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
                        st.success("Proforma envoyée par email!")
            else:
                st.warning("Email client non valide ou non fourni.")

def generate_proforma_pdf(items, price_type, client_info, transaction_info, apply_tva=False, discount_type="Pourcentage", discount_value=0.0, show_onama=False, delivery_days=7, notes=""):
    """Generate a proforma invoice PDF."""
    pdf = FPDF()
    pdf.add_page()
    effective_page_width = pdf.w - 2 * pdf.l_margin

    # Header
    pdf.set_font("Arial", "B", 16)
    title = "Proforma Invoice" if not show_onama else "ONAMA Proforma"
    pdf.cell(effective_page_width, 10, title, ln=True, align="C")
    pdf.set_font("Arial", size=12)
    pdf.cell(effective_page_width, 10, f"Proforma ID: {transaction_info['transaction_number']}", ln=True)
    pdf.cell(effective_page_width, 10, f"Date: {transaction_info['transaction_date']}", ln=True)
    pdf.cell(effective_page_width, 10, f"Performed by: {transaction_info['performed_by']}", ln=True)
    pdf.ln(10)

    # Client Information
    pdf.set_font("Arial", "B", 12)
    pdf.cell(effective_page_width, 10, "Client Information", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(effective_page_width, 8, f"Name: {client_info.get('nom_client', '')} {client_info.get('prenom_client', '')}", ln=True)
    pdf.cell(effective_page_width, 8, f"Phone: {client_info.get('telephone_client', '')}", ln=True)
    pdf.cell(effective_page_width, 8, f"Email: {client_info.get('email_client', '')}", ln=True)
    pdf.cell(effective_page_width, 8, f"Company: {client_info.get('entreprise_client', '')}", ln=True)
    pdf.cell(effective_page_width, 8, f"Address: {client_info.get('address_client', 'N/A')}", ln=True)
    pdf.ln(10)

    # Items Table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(effective_page_width, 10, "Items", ln=True)
    pdf.set_font("Arial", "B", 10)
    col_widths = [70, 30, 30, 30, 30]
    headers = ["Description", "Reference", "Color", "Quantity", "Price (DZD)"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 10, h, border=1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for item in items:
        pdf.cell(col_widths[0], 10, sanitize_text(truncate_text(item['denomination'])), border=1)
        pdf.cell(col_widths[1], 10, sanitize_text(truncate_text(item['reference'])), border=1)
        pdf.cell(col_widths[2], 10, item.get('Color', 'N/A'), border=1)
        pdf.cell(col_widths[3], 10, str(item['Quantity']), border=1)
        pdf.cell(col_widths[4], 10, f"{item['Price'] * item['Quantity']:.2f}", border=1)
        pdf.ln()

    # Footer with Totals and Additional Info
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    subtotal = sum(item['Price'] * item['Quantity'] for item in items)
    discount_amount = subtotal * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
    taxable_amount = subtotal - discount_amount
    tax_rate = 19 if apply_tva else 0
    tax_amount = taxable_amount * (tax_rate / 100)
    grand_total = taxable_amount + tax_amount

    page_bottom_margin = pdf.h - pdf.b_margin - 10
    if pdf.get_y() + 60 > page_bottom_margin:
        pdf.add_page()

    pdf.cell(150, 10, "Subtotal:", 0)
    pdf.cell(40, 10, f"{subtotal:.2f} DZD", 0, ln=True, align="R")
    if discount_amount > 0:
        discount_label = f"Discount ({discount_value}%)" if discount_type == "Pourcentage" else "Discount (Fixed)"
        pdf.cell(150, 10, discount_label, 0)
        pdf.cell(40, 10, f"-{discount_amount:.2f} DZD", 0, ln=True, align="R")
    if tax_rate > 0:
        pdf.cell(150, 10, f"TVA ({tax_rate}%):", 0)
        pdf.cell(40, 10, f"{tax_amount:.2f} DZD", 0, ln=True, align="R")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(150, 10, "Grand Total:", 0)
    pdf.cell(40, 10, f"{grand_total:.2f} DZD", 0, ln=True, align="R")

    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    grand_total_float = float(min(grand_total, 1e15))
    amount_in_words = (
        num2words(grand_total_float, lang='fr').replace("virgule", "et") + " Dinars Algériens"
        if grand_total_float <= 9999999
        else "Montant trop élevé pour conversion en lettres"
    )
    pdf.cell(0, 10, f"Montant en lettres: {amount_in_words}", ln=True)
    pdf.cell(0, 10, f"Délai de livraison: {delivery_days} jours", ln=True)
    if notes:
        pdf.cell(0, 10, f"Notes: {notes}", ln=True)
    pdf.ln(20)
    pdf.cell(0, 10, "Signature: ___________________________", ln=True, align="R")

    pdf_filename = f"Proforma-{transaction_info['transaction_number']}.pdf"
    pdf.output(pdf_filename)
    return pdf_filename

def generate_receipt_pdf(transaction_info, items, payment_amount, discount_amount=0.0, payment_details=""):
    """Generate a receipt PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.image(get_full_image_path("logo.png"), x=10, y=8, w=30)
    pdf.set_font("Arial", size=24, style='B')
    pdf.cell(200, 15, txt=sanitize_text("Reçu Takideco"), ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt=sanitize_text(f"ID de Transaction : {transaction_info['transaction_number']}"), ln=1)
    pdf.cell(0, 10, txt=sanitize_text(f"Date : {transaction_info['transaction_date']}"), ln=1)
    pdf.cell(0, 10, txt=sanitize_text(f"ID Client : {transaction_info['client_id']}"), ln=1)
    pdf.cell(0, 10, txt=sanitize_text(f"Effectué par : {transaction_info['performed_by']}"), ln=1)
    pdf.ln(10)

    total_amount = sum(item['Quantity'] * item['Price'] for item in items)
    pdf.cell(0, 10, txt=sanitize_text(f"Montant Total (HT) : {total_amount:.2f} DZD"), ln=1)
    if discount_amount > 0:
        pdf.cell(0, 10, txt=sanitize_text(f"Remise : {discount_amount:.2f} DZD"), ln=1)
    pdf.cell(0, 10, txt=sanitize_text(f"Montant Payé : {payment_amount:.2f} DZD"), ln=1)
    pdf.cell(0, 10, txt=sanitize_text(f"Mode de paiement : {payment_details}"), ln=1)
    pdf.ln(10)

    pdf.set_font("Arial", size=12, style='B')
    col_widths = [60, 30, 30, 30, 30]
    headers = ["Article", "Image", "Référence", "Quantité", "Total"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 10, txt=h, border=1)
    pdf.ln()
    pdf.set_font("Arial", size=12)
    row_height = 30

    for item in items:
        item_total = item['Quantity'] * item['Price']
        y_before = pdf.get_y()
        pdf.cell(col_widths[0], row_height, txt=sanitize_text(truncate_text(item['denomination'])), border=1)
        x_image = pdf.get_x()
        image_path = item.get('Image')
        if image_path:
            try:
                scaled_width_mm, scaled_height_mm = calculate_image_dimensions(image_path, col_widths[1], row_height)
                x_offset = (col_widths[1] - scaled_width_mm) / 2
                y_offset = (row_height - scaled_height_mm) / 2
                pdf.image(image_path, x=x_image + x_offset, y=y_before + y_offset, w=scaled_width_mm, h=scaled_height_mm)
            except Exception:
                pdf.set_xy(x_image, y_before)
                pdf.cell(col_widths[1], row_height, txt="Pas d'image", border=1)
        else:
            pdf.set_xy(x_image, y_before)
            pdf.cell(col_widths[1], row_height, txt="Pas d'image", border=1)
        pdf.set_xy(x_image + col_widths[1], y_before)
        pdf.cell(col_widths[2], row_height, txt=sanitize_text(truncate_text(item['reference'])), border=1)
        pdf.cell(col_widths[3], row_height, txt=str(item['Quantity']), border=1)
        pdf.cell(col_widths[4], row_height, txt=f"{item_total:.2f}", border=1)
        pdf.ln(row_height)
        pdf.ln(3)

    pdf.ln(10)
    pdf.set_font("Arial", size=10, style='I')
    total_amount_words = num2words(int(payment_amount), lang='fr') if payment_amount <= 999999 else "Montant très élevé"
    pdf.cell(0, 10, txt=sanitize_text(f"Arrêté à la somme de : {total_amount_words} dinars."), ln=1)

    pdf_filename = f"Reçu-{transaction_info['transaction_number']}-{transaction_info['transaction_date'].replace('/', '')}.pdf"
    pdf.output(pdf_filename)
    return pdf_filename

def generate_order_pdf(order_id, city, order_date, delivery_address, items, shipping_method, payment_option, created_by):
    """Generate an order PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.image(get_full_image_path("logo.png"), x=10, y=8, w=30)
    pdf.set_font("Arial", size=24, style='B')
    pdf.cell(200, 15, txt=sanitize_text(f"Bon de Commande #{order_id} - Takideco"), ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, txt=sanitize_text(f"Ville : {city}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Date de Commande : {order_date}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Adresse de Livraison : {delivery_address or 'Non spécifiée'}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Créé par : {created_by}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Méthode de Livraison : {shipping_method}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Option de Paiement : {payment_option}"), ln=1, align='R')
    pdf.ln(10)

    pdf.set_font("Arial", size=12, style='B')
    col_widths = [60, 30, 30, 30]
    headers = ["Article", "Image", "Référence", "Quantité"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 10, txt=h, border=1)
    pdf.ln()
    pdf.set_font("Arial", size=12)
    row_height = 30

    for item in items:
        y_before = pdf.get_y()
        pdf.cell(col_widths[0], row_height, txt=sanitize_text(truncate_text(item['denomination'])), border=1)
        x_image = pdf.get_x()
        image_path = get_full_image_path(find_image_path_for_color(item.get('images', ''), item.get('color')))
        if image_path:
            try:
                scaled_width_mm, scaled_height_mm = calculate_image_dimensions(image_path, col_widths[1], row_height)
                x_offset = (col_widths[1] - scaled_width_mm) / 2
                y_offset = (row_height - scaled_height_mm) / 2
                pdf.image(image_path, x=x_image + x_offset, y=y_before + y_offset, w=scaled_width_mm, h=scaled_height_mm)
            except Exception:
                pdf.set_xy(x_image, y_before)
                pdf.cell(col_widths[1], row_height, txt="Pas d'image", border=1)
        else:
            pdf.set_xy(x_image, y_before)
            pdf.cell(col_widths[1], row_height, txt="Pas d'image", border=1)
        pdf.set_xy(x_image + col_widths[1], y_before)
        pdf.cell(col_widths[2], row_height, txt=sanitize_text(truncate_text(item['reference'])), border=1)
        pdf.cell(col_widths[3], row_height, txt=str(item['quantity']), border=1)
        pdf.ln(row_height)
        pdf.ln(3)

    pdf.ln(10)
    pdf.set_font("Arial", size=8)
    pdf.set_text_color(0, 0, 128)
    default_terms = (
        "Conditions :\n"
        "Les articles listés ci-dessus seront fabriqués selon les spécifications indiquées.\n"
        "Délai de réalisation : 7 à 10 jours ouvrables après confirmation, sauf indication contraire.\n"
        "Frais d’expédition : À la charge du client, sauf pour le retrait à Onama."
    )
    pdf.multi_cell(0, 5, txt=sanitize_text(default_terms))

    pdf_filename = f"BonDeCommande-{order_id}-{order_date.replace('/', '')}.pdf"
    pdf.output(pdf_filename)
    return pdf_filename