#pdf_generator.py
from fpdf import FPDF
import os
import json
from datetime import datetime
from .utils import get_full_image_path, calculate_image_dimensions, truncate_text
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
from .client_management import get_client_info, add_new_client, save_clients
from .transaction_management import record_transaction
import qrcode

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
                         delivery_days=5, notes="", deposit_amount=0, remaining_amount=0):
    output_dir = "generated_pdfs"
    os.makedirs(output_dir, exist_ok=True)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    logo_path = get_full_image_path("logo.png")
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=30)

    pdf.set_font("Arial", "B", 20)
    pdf.set_y(10)
    pdf.cell(0, 10, "Facture Proforma - Takideco", 0, 1, 'C')

    pdf.set_font("Arial", size=10)
    transaction_line = (
        f"N° Proforma: {transaction_info['transaction_number']}  |  "
        f"Date: {transaction_info['transaction_date']}  |  "
        f"Préparé par: {transaction_info['performed_by']}"
    )
    pdf.cell(0, 6, transaction_line, 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(90, 8, "Client:", 0, 1)
    pdf.set_font("Arial", size=10)
    
    client_fields = [
        f"Nom: {client_info.get('nom_client', '')} {client_info.get('prenom_client', '')}",
        f"Entreprise: {client_info.get('entreprise_client', '')}",
        f"Tél: {client_info.get('telephone_client', '')}",
        # f"Email: {client_info.get('email_client', '')}",
        f"Adresse: {client_info.get('address_client', '')}"
    ]
    
    line_height = 6
    pdf.set_x(10)
    for field in client_fields:
        pdf.cell(90, line_height, field, 0, 1)

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

    col_widths = [22, 58, 25, 25, 25, 35]
    headers = ["Image", "Description", "Réf.", "Couleur", "Qté", "Prix (DZD)"]
    pdf.set_y(40 + (len(client_fields) * line_height) + 10)
    
    pdf.set_font("Arial", "B", 11)
    for width, header in zip(col_widths, headers):
        pdf.cell(width, 10, header, border=1, align='C')
    pdf.ln()

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

    subtotal = sum(item['Price'] * item['Quantity'] for item in items)
    discount = subtotal * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
    taxable = subtotal - discount
    tva_amount = taxable * 0.19 if apply_tva else 0
    total = taxable + tva_amount

    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Sous-total: {subtotal:,.2f} DZD", 0, 1, 'R')
    if discount > 0:
        pdf.cell(0, 8, f"Remise ({discount_type}): -{discount:,.2f} DZ", 0, 1, "R")
    if apply_tva:
        pdf.cell(0, 8, f"TVA 19%: {tva_amount:,.2f} DZD", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Total Général: {total:,.2f} DZD", 0, 1, 'R')
    
    pdf.set_font("Arial", 'I', 10)
    total_int = int(total)
    total_dec = int(round((total - total_int) * 100))
    amount_words = num2words(total_int, lang='fr').replace('et', '').replace('-', ' ') + " Dinars Algériens"
    if total_dec > 0:
        amount_words += f" et {num2words(total_dec, lang='fr').replace('et', '').replace('-', ' ')} centimes"
    pdf.cell(0, 6, f"Montant en lettres: {amount_words}", 0, 1)

    pdf.set_font("Arial", size=10)
    legal_terms = [
        f"Délai de réalisation: La commande sera prête dans un délai de {delivery_days} jours à compter de la date de réception de l'acompte.",
        "Frais d'expédition: Les frais d'expédition sont à la charge du client. L'expédition peut être organisée par le client ou coordonnée par notre société, avec les frais facturés séparément.",
        "Mode de règlement: Virement bancaire ou chèque.",
        f"Acompte: Un acompte de {deposit_amount:,.2f} DZD a été reçu. Reste à payer: {remaining_amount:,.2f} DZD"
    ]
    
    pdf.ln(10)
    for term in legal_terms:
        pdf.multi_cell(0, 5, term)
        pdf.ln(3)

    client_name = client_info.get('nom_client', 'Unknown')
    date_str = transaction_info['transaction_date'].replace('/', '')
    filename = f"Proforma-{client_name}-{transaction_info['transaction_number']}-{date_str}.pdf"
    pdf_path = os.path.join(output_dir, filename)
    pdf.output(pdf_path)
    
    return pdf_path

def generate_receipt_pdf(
    transaction_info,
    items,
    subtotal,
    discount_amount,
    tva_amount,
    total,
    payment_details="",
    client_info=None,
    tva_enabled=False,
    language="French",
    notes="",
    deposit_amount=0.0,
    remaining_amount=0.0
):
    output_dir = "generated_pdfs"
    os.makedirs(output_dir, exist_ok=True)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_fill_color(144, 238, 144)
    pdf.rect(0, 0, 210, 10, 'F')
    logo_path = get_full_image_path("logo.png")
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=12, w=30)

    # Watermark based on payment status
    payment_dict = json.loads(payment_details)
    total_paid = sum(payment_dict.values())
    if total_paid >= total:
        pdf.set_font("Arial", "B", 50)
        pdf.set_text_color(0, 255, 0)
        pdf.rotate(45, x=105, y=150)
        pdf.set_xy(50, 100)
        pdf.cell(0, 0, "PAYÉ" if language == "French" else "مدفوع", 0, 0, 'C')
    elif total_paid > 0:
        pdf.set_font("Arial", "B", 40)
        pdf.set_text_color(255, 0, 0)
        pdf.rotate(45, x=105, y=150)
        pdf.set_xy(30, 100)
        pdf.cell(0, 0, "ACOMPTE" if language == "French" else "دفعة أولية", 0, 0, 'C')
    pdf.rotate(0)
    pdf.set_text_color(0, 0, 0)

    # Title and Transaction Info
    pdf.set_font("Arial", "B", 20)
    pdf.set_y(40)
    pdf.cell(0, 10, "Facture - Takideco" if language == "French" else "فاتورة - تاكيديكو", 0, 1, 'C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"N° Facture: {transaction_info['transaction_number']}  |  Date: {transaction_info['transaction_date']}  |  Vendeur: {transaction_info['performed_by']}", 0, 1, 'C')
    pdf.ln(10)

    # Client Info
    if client_info:
        pdf.set_y(60)
        pdf.set_font("Arial", "B", 12)
        pdf.set_x(10)
        pdf.cell(90, 8, "Client:" if language == "French" else "العميل:", 0, 1)
        pdf.set_font("Arial", size=10)
        client_fields = [
            f"Nom: {client_info.get('nom_client', '')} {client_info.get('prenom_client', '')}",
            f"Entreprise: {client_info.get('entreprise_client', '')}",
            f"Tél: {client_info.get('telephone_client', '')}",
            f"Adresse: {client_info.get('address_client', '')}"
        ]
        for field in client_fields:
            pdf.cell(90, 6, field, 0, 1)

    # Company Info
    pdf.set_y(60)
    pdf.set_x(120)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(80, 8, "Takideco" if language == "French" else "تاكيديكو", 0, 1, 'R')
    pdf.set_font("Arial", size=10)
    pdf.set_x(120)
    takideco_info = (
        "Tél: 0542918226 | 0698077751\n"
        "Adresse: Cité El Houari, El Eulma\n"
        "Email: contact@takideco.dz"
    ) if language == "French" else (
        "الهاتف: 0542918226 | 0698077751\n"
        "العنوان: مدينة الهواري، العلمة\n"
        "البريد الإلكتروني: contact@takideco.dz"
    )
    pdf.multi_cell(80, 6, takideco_info, align='R')

    # Items Table
    col_widths = [22, 58, 25, 25, 25, 35]
    headers = ["Image", "Description", "Réf.", "Couleur", "Qté", "Prix (DZD)"] if language == "French" else ["صورة", "الوصف", "المرجع", "اللون", "الكمية", "السعر (دج)"]
    pdf.set_y(100)
    pdf.set_font("Arial", "B", 11)
    for width, header in zip(col_widths, headers):
        pdf.cell(width, 10, header, border=1, align='C')
    pdf.ln()

    pdf.set_font("Arial", size=10)
    for item in items:
        row_height = 20
        start_x = pdf.get_x()
        if item.get('Image'):
            full_img_path = get_full_image_path(item['Image'])
            if full_img_path and os.path.exists(full_img_path):
                img_width, img_height = calculate_image_dimensions(full_img_path, max_width_mm=22, max_height_mm=20)
                row_height = max(row_height, img_height + 2)
                x = start_x + (col_widths[0] - img_width) / 2
                y = pdf.get_y() + (row_height - img_height) / 2
                pdf.image(full_img_path, x=x, y=y, w=img_width, h=img_height)
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

    # Summary
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Sous-total: {subtotal:,.2f} DZD" if language == "French" else f"المجموع الفرعي: {subtotal:,.2f} دج", 0, 1, 'R')
    if discount_amount > 0:
        pdf.cell(0, 8, f"Remise: -{discount_amount:,.2f} DZD" if language == "French" else f"الخصم: -{discount_amount:,.2f} دج", 0, 1, 'R')
    if tva_enabled:
        pdf.cell(0, 8, f"TVA 19%: {tva_amount:,.2f} DZD" if language == "French" else f"ضريبة القيمة المضافة 19%: {tva_amount:,.2f} دج", 0, 1, 'R')
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Total Général: {total:,.2f} DZD" if language == "French" else f"المجموع العام: {total:,.2f} دج", 0, 1, 'R')

    # Payment Details
    pdf.ln(5)
    pdf.set_font("Arial", size=10)
    if payment_dict:
        pdf.cell(0, 6, "Paiement:" if language == "French" else "الدفع:", 0, 1)
        for method, amount in payment_dict.items():
            if amount > 0:
                method_ar = {"Espèces": "نقداً", "Virement": "تحويل بنكي", "CCP": "CCP"}.get(method, method)
                pdf.cell(50, 6, f"{method if language == 'French' else method_ar}: {amount:,.2f} DZD", 0, 1)
    
    # Deposit and Remaining Amount
    if deposit_amount > 0:
        pdf.cell(0, 6, f"Acompte Payé: {deposit_amount:,.2f} DZD" if language == "French" else f"الدفعة المقدمة: {deposit_amount:,.2f} دج", 0, 1)
        pdf.cell(0, 6, f"Reste à Payer: {remaining_amount:,.2f} DZD" if language == "French" else f"المتبقي للدفع: {remaining_amount:,.2f} دج", 0, 1)

    # Amount in Words
    total_int = int(total)
    total_dec = int(round((total - total_int) * 100))
    if language == "French":
        amount_words = num2words(total_int, lang='fr').replace('et', '').replace('-', ' ') + " Dinars Algériens"
        if total_dec > 0:
            amount_words += f" et {num2words(total_dec, lang='fr').replace('et', '').replace('-', ' ')} centimes"
    else:
        amount_words = num2words(total_int, lang='ar') + " دينار جزائري"
        if total_dec > 0:
            amount_words += f" و {num2words(total_dec, lang='ar')} سنتيم"
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 6, f"Montant en lettres: {amount_words}" if language == "French" else f"المبلغ بالحروف: {amount_words}", 0, 1)

    # Notes and Footer
    if notes:
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 5, f"Notes: {notes}" if language == "French" else f"ملاحظات: {notes}")
    
    pdf.set_y(-40)
    pdf.set_font("Arial", "I", 9)
    footer_text = (
        "Livraison: Les articles seront livrés sous 5 jours ouvrables à compter de la date de paiement complet, sauf accord contraire.\n"
        "Merci de choisir Takideco ! Nous apprécions votre confiance et espérons vous revoir bientôt.\n"
        "Pour toute question, contactez-nous à contact@takideco.dz ou au 0542918226."
    ) if language == "French" else (
        "التسليم: سيتم تسليم المواد خلال 5 أيام عمل من تاريخ الدفع الكامل، ما لم يتم الاتفاق على خلاف ذلك.\n"
        "شكرًا لاختياركم تاكيديكو! نحن نقدر ثقتكم ونأمل أن نراكم مجددًا قريبًا.\n"
        "لأي استفسار، تواصلوا معنا على contact@takideco.dz أو 0542918226."
    )
    pdf.multi_cell(0, 5, footer_text, align='C')

    pdf.set_fill_color(144, 238, 144)
    pdf.rect(0, 287, 210, 10, 'F')

    # File Naming and Output
    client_name = client_info.get('nom_client', 'Unknown') if client_info else 'Unknown'
    date_str = transaction_info['transaction_date'].replace('/', '')
    pdf_filename = f"Facture-{client_name}-{transaction_info['transaction_number']}-{date_str}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    pdf.output(pdf_path)
    return pdf_path


    output_dir = "generated_pdfs"
    os.makedirs(output_dir, exist_ok=True)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_fill_color(144, 238, 144)
    pdf.rect(0, 0, 210, 10, 'F')
    pdf.set_font("Arial", "B", 20)
    pdf.set_y(10)
    pdf.cell(0, 10, "Bon de Commande - Takideco" if language == "French" else "أمر شراء - تاكيديكو", 0, 1, 'C')

    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"N° Commande: {transaction_info['transaction_number']}  |  Date: {transaction_info['transaction_date']}  |  Préparé par: {transaction_info['performed_by']}", 0, 1, 'C')
    pdf.ln(10)

    if client_info:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(90, 8, "Client:" if language == "French" else "العميل:", 0, 1)
        pdf.set_font("Arial", size=10)
        client_fields = [
            f"Nom: {client_info.get('nom_client', '')} {client_info.get('prenom_client', '')}",
            f"Entreprise: {client_info.get('entreprise_client', '')}",
            f"Tél: {client_info.get('telephone_client', '')}",
            # f"Email: {client_info.get('email_client', '')}"
        ]
        for field in client_fields:
            pdf.cell(90, 6, field, 0, 1)

    col_widths = [22, 78, 25, 25, 40]
    headers = ["Image", "Description", "Réf.", "Couleur", "Quantité"] if language == "French" else ["صورة", "الوصف", "المرجع", "اللون", "الكمية"]
    pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    for width, header in zip(col_widths, headers):
        pdf.cell(width, 10, header, border=1, align='C')
    pdf.ln()

    pdf.set_font("Arial", size=10)
    for item in items:
        row_height = 20
        start_x = pdf.get_x()
        if item.get('Image'):
            full_img_path = get_full_image_path(item['Image'])
            if full_img_path and os.path.exists(full_img_path):
                img_width, img_height = calculate_image_dimensions(full_img_path, max_width_mm=22, max_height_mm=20)
                row_height = max(row_height, img_height + 2)
                x = start_x + (col_widths[0] - img_width) / 2
                y = pdf.get_y() + (row_height - img_height) / 2
                pdf.image(full_img_path, x=x, y=y, w=img_width, h=img_height)
            else:
                pdf.cell(col_widths[0], row_height, "No Image", border=1, align='C')
        else:
            pdf.cell(col_widths[0], row_height, "", border=1)
        
        pdf.set_xy(start_x + col_widths[0], pdf.get_y())
        pdf.cell(col_widths[1], row_height, truncate_text(item['denomination'], 45), border=1, align='L')
        pdf.cell(col_widths[2], row_height, item['reference'], border=1, align='C')
        pdf.cell(col_widths[3], row_height, item.get('Color', ''), border=1, align='C')
        pdf.cell(col_widths[4], row_height, str(item['Quantity']), border=1, align='C')
        pdf.ln(row_height)

    if notes:
        pdf.ln(10)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 5, f"Notes: {notes}" if language == "French" else f"ملاحظات: {notes}")

    pdf.set_y(-40)
    pdf.set_font("Arial", "I", 9)
    footer_text = "Merci pour votre commande chez Takideco !" if language == "French" else "شكرًا لطلبكم من تاكيديكو!"
    pdf.cell(0, 5, footer_text, 0, 1, 'C')
    pdf.set_fill_color(144, 238, 144)
    pdf.rect(0, 287, 210, 10, 'F')

    client_name = client_info.get('nom_client', 'Unknown') if client_info else 'Unknown'
    date_str = transaction_info['transaction_date'].replace('/', '')
    pdf_filename = f"Bon-de-commande-{transaction_info['transaction_number']}-{date_str}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    pdf.output(pdf_path)
    return pdf_path

def truncate_text(text, max_length=35):

    return (text[:max_length] + '...') if len(text) > max_length else text 

def generate_order_pdf(
    order_info,
    items,
    subtotal,
    total,
    supplier_info=None,
    language="French",
    notes=""
):
    """Generate a purchase order PDF for supplier orders."""
    output_dir = "generated_pdfs"
    os.makedirs(output_dir, exist_ok=True)
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_fill_color(144, 238, 144)
    pdf.rect(0, 0, 210, 10, 'F')
    logo_path = get_full_image_path("logo.png")
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=12, w=30)

    # Title and Order Info
    pdf.set_font("Arial", "B", 20)
    pdf.set_y(40)
    pdf.cell(0, 10, "Bon de Commande - Takideco" if language == "French" else "أمر شراء - تاكيديكو", 0, 1, 'C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"N° Commande: {order_info['order_number']}  |  Date: {order_info['order_date']}  |  Émise par: {order_info['performed_by']}", 0, 1, 'C')
    pdf.ln(10)

    # Supplier Info
    if supplier_info:
        pdf.set_y(60)
        pdf.set_font("Arial", "B", 12)
        pdf.set_x(10)
        pdf.cell(90, 8, "Fournisseur:" if language == "French" else "المورد:", 0, 1)
        pdf.set_font("Arial", size=10)
        supplier_fields = [
            f"Nom: {supplier_info.get('name', '')}",
            f"Entreprise: {supplier_info.get('company', '')}",
            f"Tél: {supplier_info.get('phone', '')}",
            f"Adresse: {supplier_info.get('address', '')}"
        ]
        for field in supplier_fields:
            pdf.cell(90, 6, field, 0, 1)

    # Company Info
    pdf.set_y(60)
    pdf.set_x(120)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(80, 8, "Takideco" if language == "French" else "تاكيديكو", 0, 1, 'R')
    pdf.set_font("Arial", size=10)
    pdf.set_x(120)
    takideco_info = (
        "Tél: 0542918226 | 0698077751\n"
        "Adresse: Cité El Houari, El Eulma\n"
        "Email: contact@takideco.dz"
    ) if language == "French" else (
        "الهاتف: 0542918226 | 0698077751\n"
        "العنوان: مدينة الهواري، العلمة\n"
        "البريد الإلكتروني: contact@takideco.dz"
    )
    pdf.multi_cell(80, 6, takideco_info, align='R')

    # Items Table
    col_widths = [22, 58, 25, 25, 35]
    headers = ["Image", "Description", "Réf.", "Qté", "Prix (DZD)"] if language == "French" else ["صورة", "الوصف", "المرجع", "الكمية", "السعر (دج)"]
    pdf.set_y(100)
    pdf.set_font("Arial", "B", 11)
    for width, header in zip(col_widths, headers):
        pdf.cell(width, 10, header, border=1, align='C')
    pdf.ln()

    pdf.set_font("Arial", size=10)
    for item in items:
        row_height = 20
        start_x = pdf.get_x()
        if item.get('Image'):
            full_img_path = get_full_image_path(item['Image'])
            if full_img_path and os.path.exists(full_img_path):
                img_width, img_height = calculate_image_dimensions(full_img_path, max_width_mm=22, max_height_mm=20)
                row_height = max(row_height, img_height + 2)
                x = start_x + (col_widths[0] - img_width) / 2
                y = pdf.get_y() + (row_height - img_height) / 2
                pdf.image(full_img_path, x=x, y=y, w=img_width, h=img_height)
            else:
                pdf.cell(col_widths[0], row_height, "No Image", border=1, align='C')
        else:
            pdf.cell(col_widths[0], row_height, "", border=1)
        
        pdf.set_xy(start_x + col_widths[0], pdf.get_y())
        pdf.cell(col_widths[1], row_height, truncate_text(item['denomination'], 35), border=1, align='L')
        pdf.cell(col_widths[2], row_height, item['reference'], border=1, align='C')
        pdf.cell(col_widths[3], row_height, str(item['Quantity']), border=1, align='C')
        price_total = item['Price'] * item['Quantity']
        pdf.cell(col_widths[4], row_height, f"{price_total:,.2f}", border=1, align='R')
        pdf.ln(row_height)

    # Summary
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Sous-total: {subtotal:,.2f} DZD" if language == "French" else f"المجموع الفرعي: {subtotal:,.2f} دج", 0, 1, 'R')
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Total Général: {total:,.2f} DZD" if language == "French" else f"المجموع العام: {total:,.2f} دج", 0, 1, 'R')

    # Amount in Words
    total_int = int(total)
    total_dec = int(round((total - total_int) * 100))
    if language == "French":
        amount_words = num2words(total_int, lang='fr').replace('et', '').replace('-', ' ') + " Dinars Algériens"
        if total_dec > 0:
            amount_words += f" et {num2words(total_dec, lang='fr').replace('et', '').replace('-', ' ')} centimes"
    else:
        amount_words = num2words(total_int, lang='ar') + " دينار جزائري"
        if total_dec > 0:
            amount_words += f" و {num2words(total_dec, lang='ar')} سنتيم"
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 6, f"Montant en lettres: {amount_words}" if language == "French" else f"المبلغ بالحروف: {amount_words}", 0, 1)

    # Notes and Footer
    if notes:
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 5, f"Notes: {notes}" if language == "French" else f"ملاحظات: {notes}")
    
    pdf.set_y(-40)
    pdf.set_font("Arial", "I", 9)
    footer_text = (
        "Merci de confirmer la réception et la disponibilité des articles.\n"
        "Pour toute question, contactez-nous à contact@takideco.dz ou au 0542918226."
    ) if language == "French" else (
        "يرجى تأكيد الاستلام وتوافر المواد.\n"
        "لأي استفسار، تواصلوا معنا على contact@takideco.dz أو 0542918226."
    )
    pdf.multi_cell(0, 5, footer_text, align='C')

    pdf.set_fill_color(144, 238, 144)
    pdf.rect(0, 287, 210, 10, 'F')

    # File Naming and Output
    supplier_name = supplier_info.get('name', 'Unknown') if supplier_info else 'Unknown'
    date_str = order_info['order_date'].replace('/', '')
    pdf_filename = f"Order-{supplier_name}-{order_info['order_number']}-{date_str}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    pdf.output(pdf_path)
    return pdf_path