# modules/pdf_generator.py
from fpdf import FPDF
import streamlit as st
from .utils import sanitize_text, calculate_image_dimensions, truncate_text, get_full_image_path, find_image_path_for_color
from num2words import num2words
from datetime import datetime

def generate_proforma_pdf(items, price_type, client_info, transaction_info, apply_tva=False, discount_type="Pourcentage", discount_value=0.0, show_onama=False, delivery_days=7, notes=""):
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
    pdf.ln(10)

    # Table Header
    col_widths = [10, 60, 30, 20, 30, 30]  # N°, Désignation, Référence, Quantité, Prix Unitaire, Montant
    pdf.set_font("Arial", "B", 10)
    pdf.cell(col_widths[0], 10, "N°", 1)
    pdf.cell(col_widths[1], 10, "Désignation", 1)
    pdf.cell(col_widths[2], 10, "Référence", 1)
    pdf.cell(col_widths[3], 10, "Quantité", 1)
    pdf.cell(col_widths[4], 10, "Prix Unitaire", 1)
    pdf.cell(col_widths[5], 10, "Montant", 1)
    pdf.ln()

    # Table Content with Improved Page Break Handling
    pdf.set_font("Arial", size=10)
    line_height = 10
    page_bottom_margin = pdf.h - pdf.b_margin - 80  # Increased to ensure footer fits
    
    for i, item in enumerate(items, 1):
        # Check if the next row will fit entirely on the current page
        if pdf.get_y() + line_height > page_bottom_margin:
            pdf.add_page()
            pdf.set_font("Arial", "B", 10)
            pdf.cell(col_widths[0], 10, "N°", 1)
            pdf.cell(col_widths[1], 10, "Désignation", 1)
            pdf.cell(col_widths[2], 10, "Référence", 1)
            pdf.cell(col_widths[3], 10, "Quantité", 1)
            pdf.cell(col_widths[4], 10, "Prix Unitaire", 1)
            pdf.cell(col_widths[5], 10, "Montant", 1)
            pdf.ln()
            pdf.set_font("Arial", size=10)
        
        # Write the row at the current position
        start_x = pdf.l_margin
        start_y = pdf.get_y()
        pdf.set_xy(start_x, start_y)
        pdf.cell(col_widths[0], line_height, str(i), 1)
        pdf.set_xy(start_x + col_widths[0], start_y)
        pdf.cell(col_widths[1], line_height, truncate_text(item['denomination'], 60), 1)
        pdf.set_xy(start_x + col_widths[0] + col_widths[1], start_y)
        pdf.cell(col_widths[2], line_height, item['reference'], 1)
        pdf.set_xy(start_x + col_widths[0] + col_widths[1] + col_widths[2], start_y)
        pdf.cell(col_widths[3], line_height, str(item['Quantity']), 1)
        pdf.set_xy(start_x + col_widths[0] + col_widths[1] + col_widths[2] + col_widths[3], start_y)
        pdf.cell(col_widths[4], line_height, f"{item['Price']:.2f}", 1)
        pdf.set_xy(start_x + col_widths[0] + col_widths[1] + col_widths[2] + col_widths[3] + col_widths[4], start_y)
        pdf.cell(col_widths[5], line_height, f"{item['Price'] * item['Quantity']:.2f}", 1)
        pdf.set_xy(start_x, start_y + line_height)  # Move to next line manually

    # Footer with Totals and Additional Info
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    subtotal = sum(item['Price'] * item['Quantity'] for item in items)
    discount_amount = subtotal * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
    taxable_amount = subtotal - discount_amount
    tax_rate = 19 if apply_tva else 0
    tax_amount = taxable_amount * (tax_rate / 100)
    grand_total = taxable_amount + tax_amount

    # Ensure footer fits on the page
    if pdf.get_y() + 60 > page_bottom_margin:  # 60mm for footer
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
    amount_in_words = num2words(grand_total, lang='fr').replace("virgule", "et") + " Dinars Algériens"
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
    """Générer un PDF pour un Bon de Commande."""
    pdf = FPDF()
    pdf.add_page()
    pdf.image(get_full_image_path("logo.png"), x=10, y=8, w=30)
    pdf.set_font("Arial", size=24, style='B')
    pdf.cell(200, 15, txt=sanitize_text(f"Bon de Commande #{order_id} - Takideco"), ln=True, align='C')
    pdf.ln(10)

    # Header info
    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, txt=sanitize_text(f"Ville : {city}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Date de Commande : {order_date}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Adresse de Livraison : {delivery_address or 'Non spécifiée'}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Créé par : {created_by}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Méthode de Livraison : {shipping_method}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Option de Paiement : {payment_option}"), ln=1, align='R')
    pdf.ln(10)

    # Items table
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

    # Footer terms
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