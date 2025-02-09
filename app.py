import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
from io import BytesIO
from num2words import num2words
from datetime import datetime
import random
import gdown

# Google Drive folder and file IDs
GOOGLE_DRIVE_FOLDER_ID = "1ElAUnwNUjnoaVUxH1yZKpNaAqcy9y3r3"
CATAFACTUAPP_FILE_ID = "1a5PgsZNj7fsfUtWHGpDgBQUBRLLlaun1"  # Replace with the actual file ID
PROFORMA_INVOICES_FILE_ID = "1FR0XjHqCJ98-hbMBCeh7ikzUgIqNEWSO"  # Replace with the actual file ID

# Function to download a file from Google Drive
def download_file_from_google_drive(file_id, output):
    """
    Download a file from Google Drive using its file ID.
    """
    try:
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, output, quiet=False)
        return True
    except Exception as e:
        st.error(f"Failed to download file from Google Drive: {e}")
        return False

# Cache the data loading process
@st.cache_data
def read_excel_from_google_drive(file_id, output_filename):
    """
    Download and read the Excel file from Google Drive.
    """
    if download_file_from_google_drive(file_id, output_filename):
        df = pd.read_excel(output_filename)
        df.columns = df.columns.str.strip()  # Strip leading/trailing spaces from column names
        return df
    else:
        return None

# Function to sanitize text for FPDF
def sanitize_text(text):
    """
    Replace unsupported characters in the text with supported ones.
    """
    # Replace curly apostrophes with straight ones
    text = text.replace("’", "'")
    # Add more replacements if needed (e.g., for other special characters)
    return text

# Function to generate and upload PDF invoice
def generate_pdf(items, price_type, client_info, transaction_info, apply_tva, discount_type, discount_value):
    pdf = FPDF()
    pdf.add_page()
    
    # Add logo
    pdf.image("logo.png", x=10, y=8, w=30)  # Replace "logo.png" with the path to your logo
    
    # Set font for the header
    pdf.set_font("Arial", size=24, style='B')
    pdf.cell(200, 15, txt=sanitize_text("Takideco Proforma Invoice"), ln=True, align='C')
    pdf.ln(10)
    
    # Add issuer information
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 5, txt=sanitize_text("Taki Deco"), ln=True, align='C')
    pdf.cell(200, 5, txt=sanitize_text("0542310057 | 0542918226 | 0698077751"), ln=True, align='C')
    pdf.cell(200, 5, txt=sanitize_text("www.takideco.com | email: takidecommercial@gmail.com"), ln=True, align='C')
    pdf.ln(10)
    
    # Add client and transaction information side by side
    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, txt=sanitize_text(f"Nom de client: {client_info['nom_client']}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"N° De transaction: {transaction_info['transaction_number']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Nom de l’entreprise: {client_info['nom_entreprise']}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Date de transaction: {transaction_info['transaction_date']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Adresse: {client_info['adresse']}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"ID Client: {transaction_info['client_id']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Telephone: {client_info['telephone']}"), ln=1)
    pdf.ln(10)
    
    # Add items table
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(100, 10, txt=sanitize_text("Item"), border=1)
    pdf.cell(30, 10, txt=sanitize_text("Quantity"), border=1)
    pdf.cell(30, 10, txt=sanitize_text("Price"), border=1)
    pdf.cell(30, 10, txt=sanitize_text("Total"), border=1, ln=True)
    
    pdf.set_font("Arial", size=12)
    total_amount = 0
    for item in items:
        item_total = item['Quantity'] * item['Price']
        pdf.cell(100, 10, txt=sanitize_text(item['Denomination']), border=1)
        pdf.cell(30, 10, txt=sanitize_text(str(item['Quantity'])), border=1)
        pdf.cell(30, 10, txt=sanitize_text(f"{item['Price']:.2f}"), border=1)
        pdf.cell(30, 10, txt=sanitize_text(f"{item_total:.2f}"), border=1, ln=True)
        total_amount += item_total
    
    # Apply discount
    if discount_type == "Percentage":
        discount_amount = total_amount * (discount_value / 100)
    else:
        discount_amount = discount_value
    
    total_amount_after_discount = total_amount - discount_amount
    
    # Calculate TVA if applicable
    if apply_tva:
        tva_amount = total_amount_after_discount * 0.19
        total_amount_with_tva = total_amount_after_discount + tva_amount
    else:
        tva_amount = 0
        total_amount_with_tva = total_amount_after_discount
    
    # Add total amount, discount, and TVA details
    pdf.ln(10)
    pdf.cell(160, 10, txt=sanitize_text("Total Amount (HT):"), border=0)
    pdf.cell(30, 10, txt=sanitize_text(f"{total_amount:.2f}"), border=1, ln=True)
    pdf.cell(160, 10, txt=sanitize_text(f"Discount ({discount_value}{'%' if discount_type == 'Percentage' else 'DZD'}):"), border=0)
    pdf.cell(30, 10, txt=sanitize_text(f"{discount_amount:.2f}"), border=1, ln=True)
    pdf.cell(160, 10, txt=sanitize_text("Total Amount After Discount (HT):"), border=0)
    pdf.cell(30, 10, txt=sanitize_text(f"{total_amount_after_discount:.2f}"), border=1, ln=True)
    if apply_tva:
        pdf.cell(160, 10, txt=sanitize_text("TVA (19%):"), border=0)
        pdf.cell(30, 10, txt=sanitize_text(f"{tva_amount:.2f}"), border=1, ln=True)
        pdf.cell(160, 10, txt=sanitize_text("Total Amount (TTC):"), border=0)
        pdf.cell(30, 10, txt=sanitize_text(f"{total_amount_with_tva:.2f}"), border=1, ln=True)
    
    # Add additional text at the bottom
    pdf.ln(10)
    pdf.set_font("Arial", size=8)  # Smaller font size for this section
    pdf.set_text_color(0, 0, 128)  # Navy blue color
    pdf.multi_cell(0, 5, txt=sanitize_text(
        "Mode de règlement :\n"
        "Espèces, Virement bancaire ou Chèque (à remettre par le client à nos bureaux de Constantine dans un délai maximum de 48 heures suivant la commande).\n"
        "Acompte :\n"
        "Un acompte de 50 % est exigé au moment de placer la commande. La commande ne sera traitée qu’après réception de cet acompte.\n"
        "Délai de réalisation :\n"
        "La commande sera prête dans un délai de 7 à 10 jours à compter de la date de réception de l’acompte.\n"
        "Frais d’expédition :\n"
        "Les frais d’expédition sont à la charge du client. L’expédition peut être organisée par le client ou coordonnée par notre société, avec les frais facturés séparément."
    ))
    
    # Convert total amount to words
    try:
        total_amount_words = num2words(int(total_amount_with_tva), lang='fr')  # Convert to French words
    except OverflowError:
        total_amount_words = "Montant très élevé"  # Fallback for very large numbers
    
    pdf.ln(10)
    pdf.set_font("Arial", size=10, style='I')
    pdf.set_text_color(0, 0, 0)  # Black color
    pdf.cell(200, 10, txt=sanitize_text(f"Arrêter la présente facture proforma à la somme de : {total_amount_words} dinars."), ln=True)
    
    # Save PDF to a temporary file
    pdf_filename = "proforma_invoice.pdf"
    pdf.output(pdf_filename)
    
    return pdf_filename

# Main app
def main():
    st.title("Proforma Invoice Generator")
    
    # Load data from Google Drive
    try:
        df = read_excel_from_google_drive(CATAFACTUAPP_FILE_ID, "catafactuapp1.xlsx")
        if df is None:
            st.error("Failed to load data from Google Drive.")
            return
    except Exception as e:
        st.error(f"Failed to load data from Google Drive: {e}")
        return
    
    # Select price type
    price_type = st.radio("Select Price Type", ["prix-super-gros", "prix-gros", "prix-detaille"])
    
    # Add TVA option
    apply_tva = st.checkbox("Apply TVA (19%)", value=False)
    
    # Add discount option
    discount_type = st.radio("Discount Type", ["Percentage", "Fixed Amount"])
    discount_value = st.number_input("Discount Value", min_value=0.0, value=0.0)
    
    # Search for item
    search_term = st.text_input("Search for an item by Denomination")
    if search_term:
        # Use regex=False for faster string matching
        filtered_df = df[df['Denomination'].str.contains(search_term, case=False, na=False, regex=False)]
        
        if not filtered_df.empty:
            selected_item = st.selectbox("Select an item", filtered_df['Denomination'])
            selected_row = filtered_df[filtered_df['Denomination'] == selected_item].squeeze()
            
            # Display the price of the selected item
            if price_type in selected_row.index:
                st.write(f"**Price ({price_type}):** {selected_row[price_type]}")
            else:
                st.error(f"Price type '{price_type}' not found for this item.")
            
            quantity = st.number_input("Quantity", min_value=1, value=1)
            
            if st.button("Add Item"):
                if price_type in selected_row.index:
                    item_dict = {
                        "Denomination": selected_row['Denomination'],
                        "Quantity": quantity,
                        "Price": selected_row[price_type]
                    }
                    if 'items' not in st.session_state:
                        st.session_state['items'] = []
                    st.session_state['items'].append(item_dict)
                    st.success("Item added!")
                else:
                    st.error(f"Price type '{price_type}' not found in data. Available columns: {list(selected_row.index)}")
    
    # Display selected items
    if 'items' in st.session_state and st.session_state['items']:
        st.write("### Selected Items")
        for item in st.session_state['items']:
            st.write(f"{item['Denomination']} - {item['Quantity']} x {item['Price']}")
        
        # Prompt for client information
        st.write("### Client Information")
        nom_client = st.text_input("Nom de client")
        nom_entreprise = st.text_input("Nom de l’entreprise")
        adresse = st.text_input("Adresse")
        telephone = st.text_input("Telephone")
        
        client_info = {
            "nom_client": nom_client,
            "nom_entreprise": nom_entreprise,
            "adresse": adresse,
            "telephone": telephone
        }
        
        # Automatically generate transaction information
        if 'transaction_number' not in st.session_state:
            st.session_state['transaction_number'] = 1000  # Start from 1000
        else:
            st.session_state['transaction_number'] += 1  # Increment for each new transaction
        
        transaction_info = {
            "transaction_number": st.session_state['transaction_number'],
            "transaction_date": datetime.now().strftime("%d/%m/%Y"),  # Current date
            "client_id": random.randint(1000, 9999)  # Random client ID for now
        }
        
        # Display transaction information
        st.write("### Transaction Information")
        st.write(f"N° De transaction: {transaction_info['transaction_number']}")
        st.write(f"Date de transaction: {transaction_info['transaction_date']}")
        st.write(f"ID Client: {transaction_info['client_id']}")
        
        # Generate and upload PDF
        if st.button("Generate Proforma Invoice"):
            if not all(client_info.values()):
                st.error("Please fill in all client information fields.")
            else:
                pdf_filename = generate_pdf(st.session_state['items'], price_type, client_info, transaction_info, apply_tva, discount_type, discount_value)
                
                # Provide a download link for the PDF
                with open(pdf_filename, "rb") as file:
                    btn = st.download_button(
                        label="Download Proforma Invoice",
                        data=file,
                        file_name=pdf_filename,
                        mime="application/pdf"
                    )
                st.success("Proforma Invoice Generated! Click the button above to download.")

        if st.button("Clear Items"):
            st.session_state['items'] = []
            st.success("Items cleared!")

if __name__ == "__main__":
    main()