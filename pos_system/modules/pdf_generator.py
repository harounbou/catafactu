# modules/pdf_generator.py
from fpdf import FPDF
import streamlit as st
from .utils import sanitize_text, calculate_image_dimensions, truncate_text, get_full_image_path, find_image_path_for_color
from num2words import num2words
from datetime import datetime

def generate_proforma_pdf(items, price_type, client_info, transaction_info, apply_tva, discount_type, discount_value, show_onama, delivery_days, notes=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.image(get_full_image_path("logo.png"), x=10, y=8, w=30)
    pdf.set_font("Arial", size=24, style='B')
    pdf.cell(200, 15, txt=sanitize_text("Facture Proforma Takideco"), ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=10)
    pdf.cell(200, 5, txt=sanitize_text("Taki Deco"), ln=True, align='C')
    pdf.cell(200, 5, txt=sanitize_text("0542918226 | 0698077751" if not show_onama else "0542310057 | 0542918226 | 0698077751"), ln=True, align='C')
    pdf.cell(200, 5, txt=sanitize_text("www.takideco.com | email: takidecommercial@gmail.com"), ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, txt=sanitize_text(f"Nom du client : {client_info.get('nom_client', '')}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"N° de transaction : {transaction_info['transaction_number']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Nom de l’entreprise : {client_info.get('entreprise_client', '')}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Date de transaction : {transaction_info['transaction_date']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Adresse : {client_info.get('address_client', '')}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"ID Client : {transaction_info['client_id']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Téléphone : {client_info.get('telephone_client', '')}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Effectué par : {transaction_info['performed_by']}"), ln=1, align='R')
    pdf.ln(10)
    
    total_amount = sum(item['Quantity'] * item['Price'] for item in items)
    discount_amount = total_amount * (discount_value / 100) if discount_type == "Pourcentage" else discount_value
    total_amount_after_discount = total_amount - discount_amount
    tva_amount = total_amount_after_discount * 0.19 if apply_tva else 0
    total_amount_with_tva = total_amount_after_discount + tva_amount

    items_by_category = {}
    for item in items:
        category = item.get('category', 'Sans Catégorie')
        items_by_category.setdefault(category, []).append(item)

    for category, category_items in sorted(items_by_category.items()):
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(0, 10, txt=sanitize_text(f"Catégorie : {category}"), ln=1)
        pdf.ln(5)
        pdf.set_font("Arial", size=12, style='B')
        col_widths = [60, 30, 30, 30, 30, 30]
        headers = ["Article", "Image", "Référence", "Quantité", "Prix", "Total"]
        for w, h in zip(col_widths, headers):
            pdf.cell(w, 10, txt=h, border=1)
        pdf.ln()
        pdf.set_font("Arial", size=12)
        row_height = 30
        for item in category_items:
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
            pdf.cell(col_widths[4], row_height, txt=f"{item['Price']:.2f}", border=1)
            pdf.cell(col_widths[5], row_height, txt=f"{item_total:.2f}", border=1)
            pdf.ln(row_height)
            pdf.ln(3)
        pdf.ln(5)

    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(160, 10, txt=sanitize_text("Montant Total (HT) :"), border=0)
    pdf.cell(30, 10, txt=sanitize_text(f"{total_amount:.2f}"), border=1, ln=True)
    pdf.cell(160, 10, txt=sanitize_text(f"Remise ({discount_value}{'%' if discount_type=='Pourcentage' else 'DZD'}) :"), border=0)
    pdf.cell(30, 10, txt=sanitize_text(f"{discount_amount:.2f}"), border=1, ln=True)
    pdf.cell(160, 10, txt=sanitize_text("Montant Total Après Remise (HT) :"), border=0)
    pdf.cell(30, 10, txt=sanitize_text(f"{total_amount_after_discount:.2f}"), border=1, ln=True)
    if apply_tva:
        pdf.cell(160, 10, txt=sanitize_text("TVA (19%) :"), border=0)
        pdf.cell(30, 10, txt=sanitize_text(f"{tva_amount:.2f}"), border=1, ln=True)
        pdf.cell(160, 10, txt=sanitize_text("Montant Total (TTC) :"), border=0)
        pdf.cell(30, 10, txt=sanitize_text(f"{total_amount_with_tva:.2f}"), border=1, ln=True)
    
    total_amount_words = num2words(int(total_amount_with_tva), lang='fr') if total_amount_with_tva <= 999999 else "Montant très élevé"
    pdf.ln(10)
    pdf.set_font("Arial", size=10, style='I')
    pdf.cell(200, 10, txt=sanitize_text(f"Arrêter la présente facture proforma à la somme de : {total_amount_words} dinars."), ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", size=8)
    pdf.set_text_color(0, 0, 128)
    default_terms = (
        "Mode de règlement :\n"
        "Espèces, Virement bancaire ou Chèque (à remettre par le client à nos bureaux de Constantine dans un délai maximum de 48 heures suivant la commande).\n"
        "Acompte :\n"
        "Un acompte de 50 % est exigé au moment de placer la commande.\n"
        "Délai de réalisation :\n" +
        (f"La commande sera prête dans un délai de {delivery_days} jours à compter de la date de réception de l’acompte."
         if delivery_days > 0 else "La commande sera prête dans un délai de 7 à 10 jours.") +
        "\nFrais d’expédition :\n"
        "Les frais d’expédition sont à la charge du client."
    )
    pdf.multi_cell(0, 5, txt=sanitize_text(default_terms))
    
    if notes:
        pdf.ln(5)
        pdf.set_font("Arial", size=8, style='I')
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 5, txt=sanitize_text(f"Notes personnalisées :\n{notes}"))

    pdf_filename = f"Proforma-{client_info.get('nom_client', 'Client')}-{datetime.now().strftime('%d%m%Y')}.pdf"
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