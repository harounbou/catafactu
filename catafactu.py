import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from fpdf import FPDF
import os

# Function to authenticate and connect to Google Sheets
def connect_to_google_sheets():
    # Use environment variables for credentials (safer for deployment)
    creds_dict = {
        "type": os.getenv("GOOGLE_TYPE"),
        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n"),
        "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
        "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_CERT_URL"),
        "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_CERT_URL")
    }
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("catafactuapp").worksheet("ActuStock")
    return sheet

# Function to fetch filtered data from Google Sheets
def fetch_filtered_data(sheet, search_term):
    # Fetch only relevant rows to improve performance
    all_records = sheet.get_all_records()
    df = pd.DataFrame(all_records)
    if search_term:
        df = df[df['Denomination'].str.contains(search_term, case=False, na=False)]
    return df

# Function to generate a PDF invoice
def generate_pdf(items, price_type):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Proforma Invoice", ln=True, align='C')
    pdf.ln(10)
    
    total_amount = 0
    for item in items:
        pdf.cell(200, 10, txt=f"{item['Denomination']} - {item['Quantity']} x {item['Price']}", ln=True)
        total_amount += item['Quantity'] * item['Price']
    
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Total: {total_amount}", ln=True)
    pdf.output("proforma_invoice.pdf")

# Main function
def main():
    st.title("Proforma Invoice Generator")
    
    # Connect to Google Sheets
    sheet = connect_to_google_sheets()
    
    # User selects price type
    price_type = st.radio("Select Price Type", ["prix-super-gros", "prix-gros", "prix-detaille"])
    
    # User searches for items
    search_term = st.text_input("Search for an item by Denomination")
    if search_term:
        df = fetch_filtered_data(sheet, search_term)
        st.write(df)
        
        selected_item = st.selectbox("Select an item", df['Denomination'])
        quantity = st.number_input("Quantity", min_value=1, value=1)
        
        if st.button("Add Item"):
            selected_row = df[df['Denomination'] == selected_item].squeeze()
            item_dict = {
                "Denomination": selected_row['Denomination'],
                "Quantity": quantity,
                "Price": selected_row[price_type]
            }
            if 'items' not in st.session_state:
                st.session_state['items'] = []
            st.session_state['items'].append(item_dict)
            st.success("Item added!")
    
    # Display selected items
    if 'items' in st.session_state and st.session_state['items']:
        st.write("### Selected Items")
        for item in st.session_state['items']:
            st.write(f"{item['Denomination']} - {item['Quantity']} x {item['Price']}")
        
        # Generate PDF
        if st.button("Generate Proforma Invoice"):
            generate_pdf(st.session_state['items'], price_type)
            st.success("Proforma Invoice Generated! Download 'proforma_invoice.pdf'.")
        
        if st.button("Clear Items"):
            st.session_state['items'] = []
            st.success("Items cleared!")

if __name__ == "__main__":
    main()