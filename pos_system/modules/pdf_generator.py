# modules/pdf_generator.py
from fpdf import FPDF
import os
from num2words import num2words
from modules.utils import (
    get_full_image_path,
    calculate_image_dimensions,
    sanitize_text,
    truncate_text,
    find_image_path_for_color,
    validate_email,
    fetch_df_from_db
)
import streamlit as st
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from barcode import Code128
from barcode.writer import ImageWriter
from .client_management import get_client_info, add_new_client, save_clients
from .transaction_management import record_transaction
import qrcode

def generate_barcode(reference):
    """Generate a barcode image for a given reference."""
    barcode = Code128(reference, writer=ImageWriter())
    filename = f"barcode_{reference}"
    barcode.save(filename)
    return f"{filename}.png"

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

def generate_proforma_pdf(items, price_type, client_info, transaction_info, apply_tva=False, 
                         discount_type="Pourcentage", discount_value=0.0, show_onama=False, 
                         delivery_days=5, notes=""):
    # Create output directory if needed
    output_dir = "generated_pdfs"
    os.makedirs(output_dir, exist_ok=True)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Logo Above Client
    logo_path = get_full_image_path("logo.png")
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30)

    # Header
    pdf.set_font("Arial", "B", 20)
    pdf.set_y(10)
    pdf.cell(0, 10, "Facture Proforma - Takideco", 0, 1, 'C')

    # Transaction Info
    pdf.set_font("Arial", size=10)
    transaction_line = (
        f"N° Proforma: {transaction_info['transaction_number']}  |  "
        f"Date: {transaction_info['transaction_date']}  |  "
        f"Préparé par: {transaction_info['performed_by']}"
    )
    pdf.cell(0, 6, transaction_line, 0, 1, 'C')
    pdf.ln(10)

    # Client Information (Left Column)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(90, 8, "Client:", 0, 1)
    pdf.set_font("Arial", size=10)
    
    client_fields = [
        f"Nom: {client_info.get('nom_client', '')} {client_info.get('prenom_client', '')}",
        f"Entreprise: {client_info.get('entreprise_client', '')}",
        f"Tél: {client_info.get('telephone_client', '')}",
        f"Email: {client_info.get('email_client', '')}",
        f"Adresse: {client_info.get('address_client', '')}"
    ]
    
    line_height = 6
    pdf.set_x(10)
    for field in client_fields:
        pdf.cell(90, line_height, field, 0, 1)

    # Company Information (Right Column, Opposite Client)
    pdf.set_y(30)
    pdf.set_x(120)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(80, 8, "Takideco", 0, 1, 'R')
    pdf.set_font("Arial", size=10)
    pdf.set_x(120)
    if show_onama:
        pdf.multi_cell(80, line_height,
            "Tél: 0542918226 | 0698077751 | 0542310057\n"
            "Adresse: Cité El Houari, El Eulma\n"
            "Email: contact@takideco.dz",
            align='R')
    else:
        pdf.multi_cell(80, line_height,
            "Tél: 0542918226 | 0698077751\n"
            "Adresse: Cité El Houari, El Eulma\n"
            "Email: contact@takideco.dz",
            align='R')

    # Items Table
    col_widths = [22, 58, 25, 25, 25, 35]
    headers = ["Image", "Description", "Réf.", "Couleur", "Qté", "Prix (DZD)"]
    pdf.set_y(40 + (len(client_fields) * line_height) + 10)
    
    # Table Header
    pdf.set_font("Arial", "B", 11)
    for width, header in zip(col_widths, headers):
        pdf.cell(width, 10, header, border=1, align='C')
    pdf.ln()

    # Table Rows
    pdf.set_font("Arial", size=10)
    for item in items:
        row_height = 20
        start_x = pdf.get_x()
        
        if item.get('Image'):
            full_img_path = get_full_image_path(item['Image'])
            if full_img_path and os.path.exists(full_img_path):
                try:
                    img_width, img_height = calculate_image_dimensions(full_img_path, max_width_mm=22, max_height_mm=20)
                    row_height = max(row_height, img_height + 2)
                    x = start_x + (col_widths[0] - img_width) / 2
                    y = pdf.get_y() + (row_height - img_height) / 2
                    pdf.image(full_img_path, x=x, y=y, w=img_width, h=img_height)
                except Exception:
                    pdf.cell(col_widths[0], row_height, "Image N/A", border=1, align='C')
            else:
                pdf.cell(col_widths[0], row_height, "No Image", border=1, align='C')
        else:
            pdf.cell(col_widths[0], row_height, "", border=1)
        
        pdf.set_xy(start_x + col_widths[0], pdf.get_y())
        pdf.cell(col_widths[1], row_height, truncate_text(item['denomination'], 35), border=1, align='L')
        pdf.cell(col_widths[2], row_height, item['reference'], border=1, align='C')
        pdf.cell(col_widths[3], row_height, item.get('Color', ''), border=1, align='C')
        pdf.cell(col_widths[4], row_height, str(item['Quantity']), border=1, align='C')
        price_total = item['Price'] * item['Quantity']
        pdf.cell(col_widths[5], row_height, f"{price_total:,.2f}", border=1, align='R')
        pdf.ln(row_height)

    # Calculations
    subtotal = sum(item['Price'] * item['Quantity'] for item in items)
    discount = subtotal * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
    taxable = subtotal - discount
    tva_amount = taxable * 0.19 if apply_tva else 0
    total = taxable + tva_amount

    # Total Section with Formatted Numbers
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Sous-total: {subtotal:,.2f} DZ", 0, 1, 'R')
    if discount > 0:
        pdf.cell(0, 8, f"Remise ({discount_type}): -{discount:,.2f} DZ", 0, 1, "R")
    if apply_tva:
        pdf.cell(0, 8, f"TVA 19%: {tva_amount:,.2f} DZ", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Total Général: {total:,.2f} DZ", 0, 1, 'R')
    
    # Amount in Words (Fixed)
    pdf.set_font("Arial", 'I', 10)
    total_int = int(total)  # Integer part
    total_dec = int(round((total - total_int) * 100))  # Decimal part (centimes)
    amount_words = num2words(total_int, lang='fr').replace('et', '').replace('-', ' ') + " Dinars Algériens"
    if total_dec > 0:
        amount_words += f" et {num2words(total_dec, lang='fr').replace('et', '').replace('-', ' ')} centimes"
    pdf.cell(0, 6, f"Montant en lettres: {amount_words}", 0, 1)

    # Legal Terms Section
    pdf.set_font("Arial", size=10)
    legal_terms = [
        f"Délai de réalisation: La commande sera prête dans un délai de {delivery_days} jours à compter de la date de réception de l'acompte.",
        "Frais d'expédition: Les frais d'expédition sont à la charge du client. L'expédition peut être organisée par le client ou coordonnée par notre société, avec les frais facturés séparément.",
        "Mode de règlement: Virement bancaire ou chèque.",
        "Acompte: Un acompte de 50% est exigé au moment de placer la commande. La commande ne sera traitée qu'après réception de cet acompte."
    ]
    
    pdf.ln(10)
    for term in legal_terms:
        pdf.multi_cell(0, 5, term)
        pdf.ln(3)

    # Generate filename and save
    client_name = client_info.get('nom_client', 'Unknown')
    date_str = transaction_info['transaction_date'].replace('/', '')
    filename = f"Proforma-{client_name}-{transaction_info['transaction_number']}-{date_str}.pdf"
    pdf_path = os.path.join(output_dir, filename)
    pdf.output(pdf_path)
    
    return pdf_path

def generate_receipt_pdf(transaction_info, items, payment_amount, discount_amount=0.0, payment_details="", client_info=None, tva_enabled=False):
    """Generate a receipt PDF with barcode images."""
    pdf = FPDF()
    pdf.add_page()
    
    # Header - Two Columns
    pdf.set_font("Arial", size=10)
    pdf.set_xy(10, 20)
    pdf.multi_cell(90, 5, 
        f"Takideco\nTél: 0542918226 | 0698077751\nAdresse: Eulma\n"
        f"Reçu ID: {transaction_info['transaction_number']}\nDate: {transaction_info['transaction_date']}\nVendeur: {transaction_info['performed_by']}"
    )
    
    if client_info:
        pdf.set_xy(110, 20)
        pdf.multi_cell(90, 5,
            f"Client: {client_info.get('nom_client', '')} {client_info.get('prenom_client', '')}\n"
            f"Entreprise: {client_info.get('entreprise_client', '')}\n"
            f"Tél: {client_info.get('telephone_client', '')}\n"
            f"Email: {client_info.get('email_client', '')}\n"
            f"Adresse: {client_info.get('address_client', '')}"
        )

    # Items Table with Barcodes
    pdf.set_y(60)
    pdf.set_font("Arial", "B", 12)
    col_widths = [50, 20, 40, 20, 30]
    headers = ["Article", "Référence", "Code-barres", "Quantité", "Total"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 10, h, border=1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for item in items:
        pdf.cell(col_widths[0], 10, sanitize_text(truncate_text(item['denomination'])), border=1)
        pdf.cell(col_widths[1], 10, item['reference'], border=1)
        barcode_img = generate_barcode(item['reference'])
        pdf.image(barcode_img, x=pdf.get_x(), y=pdf.get_y(), w=35)
        pdf.set_xy(pdf.get_x() + col_widths[2], pdf.get_y())
        pdf.cell(col_widths[3], 10, str(item['Quantity']), border=1)
        pdf.cell(col_widths[4], 10, f"{item['Quantity'] * item['Price']:.2f}", border=1)
        pdf.ln()
        os.remove(barcode_img)

    # Totals Section
    pdf.set_y(pdf.get_y() + 10)
    total_amount = sum(item['Quantity'] * item['Price'] for item in items)
    if tva_enabled:
        tva_amount = total_amount * 0.19
        final_amount = total_amount + tva_amount - discount_amount
        pdf.cell(0, 10, f"Montant Total (HT): {total_amount:.2f} DZD", ln=1)
        pdf.cell(0, 10, f"TVA 19%: {tva_amount:.2f} DZD", ln=1)
        pdf.cell(0, 10, f"Remise: {discount_amount:.2f} DZD", ln=1)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Montant Total (TTC): {final_amount:.2f} DZD", ln=1)
    else:
        final_amount = total_amount - discount_amount
        pdf.cell(0, 10, f"Montant Total: {total_amount:.2f} DZD", ln=1)
        pdf.cell(0, 10, f"Remise: {discount_amount:.2f} DZD", ln=1)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Montant Payé: {final_amount:.2f} DZD", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Mode de paiement: {payment_details}", ln=1)
    
    # Footer
    pdf.set_y(pdf.get_y() + 15)
    pdf.set_font("Arial", "I", 10)
    total_amount_words = num2words(int(final_amount), lang='fr') if final_amount <= 999999 else "Montant très élevé"
    pdf.cell(0, 10, f"Arrêté à la somme de: {total_amount_words} dinars", ln=1)

    client_name = client_info.get('nom_client', 'Unknown') if client_info else 'Unknown'
    date_str = transaction_info['transaction_date'].replace('/', '')
    pdf_filename = f"Facture-{client_name}-{transaction_info['transaction_number']}-{date_str}.pdf"
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

    date_str = order_date.replace('/', '')
    pdf_filename = f"Bon-de-commande-{order_id}-{date_str}.pdf"
    pdf.output(pdf_filename)
    return pdf_filename

def truncate_text(text, max_length=35):
    """Truncate text with ellipsis if exceeds max length"""
    return (text[:max_length] + '...') if len(text) > max_length else text