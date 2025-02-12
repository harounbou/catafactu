import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
from io import BytesIO
from num2words import num2words
from datetime import datetime
import random

# Local files
CLIENTS_FILE = "clients.xlsx"  # Local clients file
PRODUCTS_FILE = "catafactuapp1.xlsx"  # Local products file

# ------------------------------------------
# Utility functions for file loading
# ------------------------------------------

def read_local_excel(file_path):
    """
    Read a local Excel file.
    """
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()  # Strip leading/trailing spaces from column names
        return df
    except Exception as e:
        st.error(f"Échec de la lecture du fichier Excel local : {e}")
        return None

# ------------------------------------------
# Client Functions
# ------------------------------------------

def get_client_info(clients_df, search_value, search_method):
    """
    Check if a client exists based on the search method.
    """
    if not clients_df.empty:
        if search_method == "Nom du client":
            client = clients_df[clients_df['nom_client'].astype(str).str.contains(search_value, case=False, na=False)]
        elif search_method == "ID Client":
            try:
                client_id = int(search_value)
                client = clients_df[clients_df['id_client'] == client_id]
            except ValueError:
                return None
        if not client.empty:
            return client.iloc[0].to_dict()
    return None

def get_next_available_row(clients_df):
    """
    Find the next available row where all client details are empty.
    """
    required_fields = ["nom_client", "prenom_client", "telephone_client", "address_client", "email_client", "entreprise_client"]
    for idx, row in clients_df.iterrows():
        if all(pd.isna(row[field]) for field in required_fields):
            return idx
    return len(clients_df)  # If no empty row, append to the end

def add_new_client(clients_df, client_info):
    """
    Add a new client to the clients DataFrame at the first available empty row or append if none are available.
    """
    next_row = get_next_available_row(clients_df)
    if 'id_client' in client_info:
        client_info['id_client'] = int(client_info['id_client'])
    else:
        # If ID is not provided, find the next available ID
        existing_ids = clients_df['id_client'].dropna().astype(int)
        if existing_ids.empty:
            client_info['id_client'] = 2000
        else:
            client_info['id_client'] = existing_ids.max() + 1
    
    # Ensure ID is within the range 2000-5000
    if client_info['id_client'] > 5000:
        client_info['id_client'] = 2000  # Reset to 2000 if we've exceeded 5000

    if next_row < len(clients_df):
        # Insert into an existing empty row
        clients_df.loc[next_row, client_info.keys()] = client_info.values()
    else:
        # Append a new row
        clients_df = pd.concat([clients_df, pd.DataFrame([client_info])], ignore_index=True)
    
    if save_clients_file(clients_df):
        return clients_df
    return None

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

# ------------------------------------------
# PDF Generation
# ------------------------------------------

def sanitize_text(text):
    """
    Replace unsupported characters in the text with supported ones.
    """
    text = text.replace("’", "'") if pd.notna(text) else ""
    return text

def generate_pdf(items, price_type, client_info, transaction_info, apply_tva, discount_type, discount_value, show_onama, delivery_days):
    pdf = FPDF()
    pdf.add_page()
    
    # Add logo (adjust path as needed)
    pdf.image("logo.png", x=10, y=8, w=30)
    
    pdf.set_font("Arial", size=24, style='B')
    pdf.cell(200, 15, txt=sanitize_text("Facture Proforma Takideco"), ln=True, align='C')
    pdf.ln(10)
    
    # Issuer information
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 5, txt=sanitize_text("Taki Deco"), ln=True, align='C')
    if show_onama:
        pdf.cell(200, 5, txt=sanitize_text("0542310057 | 0542918226 | 0698077751"), ln=True, align='C')
    else:
        pdf.cell(200, 5, txt=sanitize_text("0542918226 | 0698077751"), ln=True, align='C')
    pdf.cell(200, 5, txt=sanitize_text("www.takideco.com | email: takidecommercial@gmail.com"), ln=True, align='C')
    pdf.ln(10)
    
    # Client and transaction information
    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, txt=sanitize_text(f"Nom de client : {client_info.get('nom_client', '')}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"N° De transaction : {transaction_info['transaction_number']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Nom de l’entreprise : {client_info.get('entreprise_client', '')}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"Date de transaction : {transaction_info['transaction_date']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Adresse : {client_info.get('address_client', '')}"), ln=0)
    pdf.cell(90, 10, txt=sanitize_text(f"ID Client : {transaction_info['client_id']}"), ln=1, align='R')
    pdf.cell(100, 10, txt=sanitize_text(f"Telephone : {client_info.get('telephone_client', '')}"), ln=1)
    pdf.ln(10)
    
    # Items table header
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
    
    if apply_tva:
        tva_amount = total_amount_after_discount * 0.19
        total_amount_with_tva = total_amount_after_discount + tva_amount
    else:
        tva_amount = 0
        total_amount_with_tva = total_amount_after_discount
    
    pdf.ln(10)
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
    
    pdf.ln(10)
    pdf.set_font("Arial", size=8)
    pdf.set_text_color(0, 0, 128)
    pdf.multi_cell(0, 5, txt=sanitize_text(
        "Mode de règlement :\n"
        "Espèces, Virement bancaire ou Chèque (à remettre par le client à nos bureaux de Constantine dans un délai maximum de 48 heures suivant la commande).\n"
        "Acompte :\n"
        "Un acompte de 50 % est exigé au moment de placer la commande. La commande ne sera traitée qu’après réception de cet acompte.\n"
        "Délai de réalisation :\n" +
        (f"La commande sera prête dans un délai de {delivery_days} jours à compter de la date de réception de l’acompte."
         if delivery_days > 0 else "La commande sera prête dans un délai de 7 à 10 jours à compter de la date de réception de l’acompte.") +
        "\nFrais d’expédition :\n"
        "Les frais d’expédition sont à la charge du client. L’expédition peut être organisée par le client ou coordonnée par notre société, avec les frais facturés séparément."
    ))
    
    try:
        total_amount_words = num2words(int(total_amount_with_tva), lang='fr')
    except OverflowError:
        total_amount_words = "Montant très élevé"
    
    pdf.ln(10)
    pdf.set_font("Arial", size=10, style='I')
    pdf.set_text_color(0, 0, 0)
    pdf.cell(200, 10, txt=sanitize_text(f"Arrêter la présente facture proforma à la somme de : {total_amount_words} dinars."), ln=True)
    
    pdf_filename = f"Proforma-{client_info.get('nom_client', 'Client')}-{datetime.now().strftime('%d%m%Y')}.pdf"
    pdf.output(pdf_filename)
    
    return pdf_filename

# ------------------------------------------
# Main Proforma Invoice Page
# ------------------------------------------

def proforma_page():
    st.title("Générateur de Facture Proforma")
    
    # Load data from local files
    try:
        df = read_local_excel(PRODUCTS_FILE)
        clients_df = read_local_excel(CLIENTS_FILE)
        if df is None or clients_df is None:
            st.error("Échec du chargement des données.")
            return
    except Exception as e:
        st.error(f"Échec du chargement des données : {e}")
        return
    
    # Price type, TVA, discount, and delivery days options
    price_type = st.radio("Sélectionnez le type de prix", ["prix-super-gros", "prix-gros", "prix-détail"], key='price_type')
    apply_tva = st.checkbox("Appliquer la TVA (19%)", value=False, key='apply_tva')
    show_onama = st.checkbox("Basculer à L'Onama", value=False, key='show_onama')
    discount_type = st.radio("Type de remise", ["Pourcentage", "Montant fixe"], key='discount_type')
    discount_value = st.number_input("Valeur de la remise", min_value=0.0, value=0.0, key='discount_value')
    delivery_days = st.selectbox("Délai de livraison (jours)", list(range(0, 31)), key='delivery_days')
    
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
                    "Reference": selected_row['Reference'],
                    "Quantity": quantity,
                    "Price": selected_row[price_type]
                }
                if 'items' not in st.session_state:
                    st.session_state['items'] = []
                st.session_state['items'].append(item_dict)
                st.success("Article ajouté !")
                del st.session_state['filtered_articles']
            else:
                st.error(f"Type de prix '{price_type}' non trouvé dans les données.")
    
    # Display selected items
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
                    st.rerun()
    
    # --- Client Search / Creation Section ---
    st.write("### Recherche de client")
    client_search_method = st.radio("Rechercher par", ["Nom du client", "ID Client"], key="client_search_method")
    client_search_value = st.text_input("Entrez la valeur de recherche", key="client_search_value")
    if st.button("Rechercher client"):
        if client_search_value:
            client_info = get_client_info(clients_df, client_search_value, client_search_method)
            if client_info:
                st.session_state["client_info_loaded"] = client_info
                st.success(f"Client {client_info.get('nom_client', 'Inconnu')} chargé !")
            else:
                st.info("Aucun client trouvé.")
        else:
            st.warning("Veuillez entrer une valeur de recherche.")

    if "client_info_loaded" in st.session_state:
        client_info = st.session_state["client_info_loaded"]
        st.write("### Informations du client chargé")
        for key, value in client_info.items():
            if pd.notna(value):  # Check if the value is not NaN
                st.write(f"{key}: {value}")
    else:
        st.write("### Ajouter un nouveau client")
        new_nom_client = st.text_input("Nom du client", key="new_nom_client")
        new_prenom_client = st.text_input("Prénom du client", key="new_prenom_client")
        new_nom_entreprise = st.text_input("Nom de l’entreprise", key="new_nom_entreprise")
        new_adresse = st.text_input("Adresse", key="new_adresse")
        new_telephone = st.text_input("Telephone", key="new_telephone")
        new_email = st.text_input("Email du client", key="new_email")
        if st.button("Ajouter nouveau client", key="add_new_client"):
            new_client_info = {
                "nom_client": new_nom_client,
                "prenom_client": new_prenom_client,
                "entreprise_client": new_nom_entreprise,
                "address_client": new_adresse,
                "telephone_client": new_telephone,
                "email_client": new_email
            }
            clients_df = add_new_client(clients_df, new_client_info)
            if clients_df is not None:
                # Directly use the newly added client for proforma without searching
                client_info = clients_df.iloc[-1].to_dict()
                st.session_state["client_info_loaded"] = client_info
                st.success("Nouveau client ajouté et clients.xlsx mis à jour !")
            else:
                st.error("Échec de l'ajout du nouveau client.")
    
    # Ensure 'items' in session_state is initialized
    if 'items' not in st.session_state:
        st.session_state['items'] = []

    # Transaction information
    if 'transaction_number' not in st.session_state:
        st.session_state['transaction_number'] = 1000
    else:
        st.session_state['transaction_number'] += 1

    # Client information for PDF generation
    client_info_for_pdf = st.session_state.get("client_info_loaded", {
        "nom_client": "",
        "prenom_client": "",
        "entreprise_client": "",
        "address_client": "",
        "telephone_client": "",
        "email_client": ""
    })

    transaction_info = {
        "transaction_number": st.session_state['transaction_number'],
        "transaction_date": datetime.now().strftime("%d/%m/%Y"),
        "client_id": client_info_for_pdf.get("id_client", random.randint(1000, 9999))
    }

    # Show transaction info regardless of client info
    st.write("### Informations de la transaction")
    st.write(f"N° De transaction : {transaction_info['transaction_number']}")
    st.write(f"Date de transaction : {transaction_info['transaction_date']}")
    st.write(f"ID Client : {transaction_info['client_id']}")
    
    if st.button("Générer la facture proforma"):
        # Generate PDF with potentially empty client info
        pdf_filename = generate_pdf(
            st.session_state['items'],
            price_type,
            client_info_for_pdf,
            transaction_info,
            apply_tva,
            discount_type,
            discount_value,
            show_onama,
            delivery_days
        )
        
        with open(pdf_filename, "rb") as file:
            st.download_button(
                label="Télécharger la facture proforma",
                data=file,
                file_name=pdf_filename,
                mime="application/pdf"
            )
        st.success("Facture proforma générée ! Cliquez sur le bouton ci-dessus pour télécharger.")
        
        # Clear client info after transaction if it was loaded
        if "client_info_loaded" in st.session_state:
            del st.session_state["client_info_loaded"]
            st.success("Client details cleared for next transaction.")

    # Clear all session state for a fresh start
    if st.button("Effacer tous les détails"):
        for key in ['items', 'client_info_loaded', 'filtered_articles']:
            if key in st.session_state:
                del st.session_state[key]
        st.success("Tous les détails ont été effacés !")

# ------------------------------------------
# Placeholder Pages
# ------------------------------------------

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

# ------------------------------------------
# Main App
# ------------------------------------------

def main():
    st.sidebar.title("Menu")
    page = st.sidebar.radio("Aller à", ["Proforma", "Bon de Commande", "Bon de Versement", "Catalogue", "Facture"])
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