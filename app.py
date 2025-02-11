import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
from io import BytesIO
from num2words import num2words
from datetime import datetime
import random
import gdown
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Google Drive folder and file IDs
GOOGLE_DRIVE_FOLDER_ID = "1ElAUnwNUjnoaVUxH1yZKpNaAqcy9y3r3"
CATAFACTUAPP_FILE_ID = "1a5PgsZNj7fsfUtWHGpDgBQUBRLLlaun1"  # Replace with the actual file ID
PROFORMA_INVOICES_FILE_ID = "1FR0XjHqCJ98-hbMBCeh7ikzUgIqNEWSO"  # Replace with the actual file ID

# Local clients file
CLIENTS_FILE = "clients.xlsx"  # Local file in the same directory as app.py

# Email configuration (replace with your email credentials)
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_email_password"

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
        st.error(f"Échec du téléchargement du fichier depuis Google Drive : {e}")
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

# Function to read the local clients.xlsx file
def read_clients_file():
    """
    Read the local clients.xlsx file.
    """
    if os.path.exists(CLIENTS_FILE):
        clients_df = pd.read_excel(CLIENTS_FILE)
        clients_df.columns = clients_df.columns.str.strip()  # Strip leading/trailing spaces from column names
        return clients_df
    else:
        st.error(f"Le fichier {CLIENTS_FILE} est introuvable dans le répertoire local.")
        return None

# Function to save the updated clients.xlsx file
def save_clients_file(clients_df):
    """
    Save the updated clients DataFrame to the local clients.xlsx file.
    """
    try:
        clients_df.to_excel(CLIENTS_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Échec de la sauvegarde du fichier {CLIENTS_FILE} : {e}")
        return False

# Function to check if a client exists and retrieve their details
def get_client_info(clients_df, email, telephone):
    """
    Check if a client exists in the clients DataFrame based on email or telephone.
    If found, return their details. Otherwise, return None.
    """
    if not clients_df.empty:
        client = clients_df[(clients_df['Email'] == email) | (clients_df['Telephone'] == telephone)]
        if not client.empty:
            return client.iloc[0].to_dict()
    return None

# Function to add a new client to the clients DataFrame
def add_new_client(clients_df, client_info):
    """
    Add a new client to the clients DataFrame.
    """
    # Generate the next available client ID
    if clients_df.empty:
        client_id = 1
    else:
        client_id = clients_df['ID'].max() + 1
    client_info['ID'] = client_id

    new_client = pd.DataFrame([client_info])
    updated_clients_df = pd.concat([clients_df, new_client], ignore_index=True)
    return updated_clients_df

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
def generate_pdf(items, price_type, client_info, transaction_info, apply_tva, discount_type, discount_value, show_onama, delivery_days):
    pdf = FPDF()
    pdf.add_page()
    
    # Add logo
    pdf.image("logo.png", x=10, y=8, w=30)  # Replace "logo.png" with the path to your logo
    
    # Set font for the header
    pdf.set_font("Arial", size=24, style='B')
    pdf.cell(200, 15, txt=sanitize_text("Facture Proforma Takideco"), ln=True, align='C')
    pdf.ln(10)
    
    # Add issuer information
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 5, txt=sanitize_text("Taki Deco"), ln=True, align='C')
    if show_onama:
        pdf.cell(200, 5, txt=sanitize_text("0542310057 | 0542918226 | 0698077751"), ln=True, align='C')
    else:
        pdf.cell(200, 5, txt=sanitize_text("0542918226 | 0698077751"), ln=True, align='C')
    pdf.cell(200, 5, txt=sanitize_text("www.takideco.com | email: takidecommercial@gmail.com"), ln=True, align='C')
    pdf.ln(10)
    
    # Add client and transaction information side by side
    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, txt=sanitize_text(f"Nom de client : {client_info['nom_client']}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"N° De transaction : {transaction_info['transaction_number']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Nom de l’entreprise : {client_info['nom_entreprise']}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Date de transaction : {transaction_info['transaction_date']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Adresse : {client_info['adresse']}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"ID Client : {transaction_info['client_id']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Telephone : {client_info['telephone']}"), ln=1)
    pdf.ln(10)
    
    # Add items table
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(80, 10, txt=sanitize_text("Article"), border=1)
    pdf.cell(30, 10, txt=sanitize_text("Référence"), border=1)
    pdf.cell(30, 10, txt=sanitize_text("Quantité"), border=1)
    pdf.cell(30, 10, txt=sanitize_text("Prix"), border=1)
    pdf.cell(30, 10, txt=sanitize_text("Total"), border=1, ln=True)
    
    pdf.set_font("Arial", size=12)
    total_amount = 0
    for item in items:
        item_total = item['Quantity'] * item['Price']
        pdf.cell(80, 10, txt=sanitize_text(item['Denomination']), border=1)
        pdf.cell(30, 10, txt=sanitize_text(item['Reference']), border=1)
        pdf.cell(30, 10, txt=sanitize_text(str(item['Quantity'])), border=1)
        pdf.cell(30, 10, txt=sanitize_text(f"{item['Price']:.2f}"), border=1)
        pdf.cell(30, 10, txt=sanitize_text(f"{item_total:.2f}"), border=1, ln=True)
        total_amount += item_total
    
    # Apply discount
    if discount_type == "Pourcentage":
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
    pdf.cell(160, 10, txt=sanitize_text("Montant Total (HT) :"), border=0)
    pdf.cell(30, 10, txt=sanitize_text(f"{total_amount:.2f}"), border=1, ln=True)
    pdf.cell(160, 10, txt=sanitize_text(f"Remise ({discount_value}{'%' if discount_type == 'Pourcentage' else 'DZD'}) :"), border=0)
    pdf.cell(30, 10, txt=sanitize_text(f"{discount_amount:.2f}"), border=1, ln=True)
    pdf.cell(160, 10, txt=sanitize_text("Montant Total Après Remise (HT) :"), border=0)
    pdf.cell(30, 10, txt=sanitize_text(f"{total_amount_after_discount:.2f}"), border=1, ln=True)
    if apply_tva:
        pdf.cell(160, 10, txt=sanitize_text("TVA (19%) :"), border=0)
        pdf.cell(30, 10, txt=sanitize_text(f"{tva_amount:.2f}"), border=1, ln=True)
        pdf.cell(160, 10, txt=sanitize_text("Montant Total (TTC) :"), border=0)
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
        f"{'La commande sera prête dans un délai de ' + str(delivery_days) + ' jours à compter de la date de réception de l’acompte.' if delivery_days > 0 else 'La commande sera prête dans un délai de 7 à 10 jours à compter de la date de réception de l’acompte.'}\n"
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
    pdf_filename = f"Proforma-{client_info['nom_client'] if client_info['nom_client'] else 'Client'}-{datetime.now().strftime('%d%m%Y')}.pdf"
    pdf.output(pdf_filename)
    
    return pdf_filename

# Function to send email with PDF attachment
def send_email_with_pdf(email_to, pdf_filename, client_name):
    try:
        # Create the email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = email_to
        msg['Subject'] = f"Facture Proforma pour {client_name}"
        
        # Email body
        body = f"""
        Bonjour,

        Veuillez trouver ci-joint la facture proforma pour {client_name}.

        Cordialement,
        Taki Deco
        """
        msg.attach(MIMEMultipart(body))
        
        # Attach the PDF
        with open(pdf_filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={pdf_filename}",
            )
            msg.attach(part)
        
        # Send the email
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, email_to, msg.as_string())
        
        return True
    except Exception as e:
        st.error(f"Échec de l'envoi de l'email : {e}")
        return False

# Proforma Invoice Page
def proforma_page():
    st.title("Générateur de Facture Proforma")
    
    # Load data from Google Drive and local file
    try:
        df = read_excel_from_google_drive(CATAFACTUAPP_FILE_ID, "catafactuapp1.xlsx")
        clients_df = read_clients_file()  # Read the local clients.xlsx file
        if df is None or clients_df is None:
            st.error("Échec du chargement des données.")
            return
    except Exception as e:
        st.error(f"Échec du chargement des données : {e}")
        return
    
    # Select price type
    price_type = st.radio("Sélectionnez le type de prix", ["prix-super-gros", "prix-gros", "prix-détail"])
    
    # Add TVA option
    apply_tva = st.checkbox("Appliquer la TVA (19%)", value=False)
    
    # Add "Basculer à L'Onama" option
    show_onama = st.checkbox("Basculer à L'Onama", value=False)
    
    # Add discount option
    discount_type = st.radio("Type de remise", ["Pourcentage", "Montant fixe"])
    discount_value = st.number_input("Valeur de la remise", min_value=0.0, value=0.0)
    
    # Add delivery days option
    delivery_days = st.selectbox("Délai de livraison (jours)", list(range(0, 31)))
    
    # --- Article Search Section ---
    search_term = st.text_input("Rechercher un article par Dénomination")
    if st.button("Rechercher l'article"):
        if search_term:
            filtered_df = df[df['Denomination'].str.contains(search_term, case=False, na=False, regex=False)]
            if not filtered_df.empty:
                st.session_state['filtered_articles'] = filtered_df
            else:
                st.error("Aucun article trouvé pour ce terme de recherche.")
        else:
            st.warning("Veuillez entrer un terme de recherche.")
    
    # If a search has been performed and filtered articles exist, display selection and addition controls.
    if 'filtered_articles' in st.session_state:
        filtered_df = st.session_state['filtered_articles']
        selected_item = st.selectbox("Sélectionnez un article", filtered_df['Denomination'], key="selected_item")
        selected_row = filtered_df[filtered_df['Denomination'] == selected_item].squeeze()
        
        if price_type in selected_row.index:
            st.write(f"**Prix ({price_type}) :** {selected_row[price_type]}")
        else:
            st.error(f"Type de prix '{price_type}' non trouvé pour cet article.")
        
        quantity = st.number_input("Quantité", min_value=1, value=1, key="quantity")
        if st.button("Ajouter l'article", key="ajouter_article"):
            if price_type in selected_row.index:
                item_dict = {
                    "Denomination": selected_row['Denomination'],
                    "Reference": selected_row['Reference'],  # Add reference from the Excel file
                    "Quantity": quantity,
                    "Price": selected_row[price_type]
                }
                if 'items' not in st.session_state:
                    st.session_state['items'] = []
                st.session_state['items'].append(item_dict)
                st.success("Article ajouté !")
                # Optionally clear the filtered articles after adding
                del st.session_state['filtered_articles']
            else:
                st.error(f"Type de prix '{price_type}' non trouvé dans les données. Colonnes disponibles : {list(selected_row.index)}")
    
    # Display selected items with remove option
    if 'items' in st.session_state and st.session_state['items']:
        st.write("### Articles sélectionnés")
        for i, item in enumerate(st.session_state['items']):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{item['Denomination']} - {item['Reference']} - {item['Quantity']} x {item['Price']}")
            with col2:
                if st.button(f"Supprimer {i+1}"):
                    st.session_state['items'].pop(i)
                    st.success("Article supprimé !")
                    st.rerun()  # Use st.rerun() instead of st.experimental_rerun()
        
        # Prompt for client information (optional)
        st.write("### Informations du client (optionnel)")
        nom_client = st.text_input("Nom du client")
        nom_entreprise = st.text_input("Nom de l’entreprise")
        adresse = st.text_input("Adresse")
        telephone = st.text_input("Telephone")
        email = st.text_input("Email du client")
        
        # Check if client exists; if not, add new client and retrieve its ID from clients.xlsx
        client_info = get_client_info(clients_df, email, telephone)
        if client_info is None:
            client_info = {
                "nom_client": nom_client,
                "nom_entreprise": nom_entreprise,
                "adresse": adresse,
                "telephone": telephone,
                "email": email
            }
            clients_df = add_new_client(clients_df, client_info)
            client_info = clients_df.iloc[-1].to_dict()  # Retrieve the new client info including the ID
            st.success("Nouveau client ajouté !")
        
        # Automatically generate transaction information
        if 'transaction_number' not in st.session_state:
            st.session_state['transaction_number'] = 1000  # Start from 1000
        else:
            st.session_state['transaction_number'] += 1  # Increment for each new transaction
        
        transaction_info = {
            "transaction_number": st.session_state['transaction_number'],
            "transaction_date": datetime.now().strftime("%d/%m/%Y"),  # Current date
            "client_id": client_info.get("ID", random.randint(1000, 9999))  # Use existing ID or generate a new one
        }
        
        # Display transaction information
        st.write("### Informations de la transaction")
        st.write(f"N° De transaction : {transaction_info['transaction_number']}")
        st.write(f"Date de transaction : {transaction_info['transaction_date']}")
        st.write(f"ID Client : {transaction_info['client_id']}")
        
        # Generate and upload PDF
        if st.button("Générer la facture proforma"):
            pdf_filename = generate_pdf(
                st.session_state['items'],
                price_type,
                client_info,
                transaction_info,
                apply_tva,
                discount_type,
                discount_value,
                show_onama,
                delivery_days
            )
            
            # Provide a download link for the PDF
            with open(pdf_filename, "rb") as file:
                st.download_button(
                    label="Télécharger la facture proforma",
                    data=file,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )
            st.success("Facture proforma générée ! Cliquez sur le bouton ci-dessus pour télécharger.")
            
            # Save the updated clients.xlsx file
            if client_info.get("ID") is None:
                if save_clients_file(clients_df):
                    st.success("Clients.xlsx mis à jour localement.")
                else:
                    st.error("Échec de la mise à jour de clients.xlsx.")
            
            # Send email with PDF attachment if an email is provided
            if email:
                if send_email_with_pdf(email, pdf_filename, client_info['nom_client'] if client_info['nom_client'] else "Client"):
                    st.success(f"Facture proforma envoyée à {email}.")
                else:
                    st.error("Échec de l'envoi de l'email.")

        if st.button("Effacer les articles"):
            st.session_state['items'] = []
            st.success("Articles effacés !")

# Placeholder pages for other functionalities
def bon_de_commande_page():
    st.title("Bon de Commande")
    st.write("Cette page est en cours de développement. Fonctionnalité à venir bientôt !")

def bon_de_versement_page():
    st.title("Bon de Versement")
    st.write("Cette page est en cours de développement. Fonctionnalité à venir bientôt !")

def catalogue_page():
    st.title("Catalogue")
    st.write("Cette page est en cours de développement. Fonctionnalité à venir bientôt !")

def facture_page():
    st.title("Facture")
    st.write("Cette page est en cours de développement. Fonctionnalité à venir bientôt !")

# Main app
def main():
    st.sidebar.title("Menu")
    
    # Add buttons for navigation
    page = st.sidebar.radio(
        "Aller à",
        ["Proforma", "Bon de Commande", "Bon de Versement", "Catalogue", "Facture"]
    )
    
    # Display the selected page
    if page == "Proforma":
        proforma_page()
    elif page == "Bon de Commande":
        bon_de_commande_page()
    elif page == "Bon de Versement":
        bon_de_versement_page()
    elif page == "Catalogue":
        catalogue_page()
    elif page == "Facture":
        facture_page()

if __name__ == "__main__":
    main()
