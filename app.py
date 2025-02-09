import streamlit as st
import pandas as pd
from fpdf import FPDF
import boto3
import os
from io import BytesIO

# AWS S3 Configuration
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
S3_BUCKET_NAME = "cartafactu1"  # Bucket containing Excel files
INVOICE_BUCKET_NAME = "proforma-invoices1"  # Bucket for storing generated invoices

# Initialize S3 client
s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

# Cache the data loading process
@st.cache_data
def read_excel_from_s3(bucket_name, file_key):
    response = s3.get_object(Bucket=bucket_name, Key=file_key)
    df = pd.read_excel(BytesIO(response['Body'].read()))
    df.columns = df.columns.str.strip()  # Strip leading/trailing spaces from column names
    return df

# Function to generate and upload PDF invoice
def generate_and_upload_pdf(items, price_type):
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
    pdf_filename = "proforma_invoice.pdf"
    pdf.output(pdf_filename)
    
    # Upload to S3
    s3.upload_file(pdf_filename, INVOICE_BUCKET_NAME, pdf_filename)
    
    # Generate a pre-signed URL for the uploaded file
    presigned_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': INVOICE_BUCKET_NAME, 'Key': pdf_filename},
        ExpiresIn=3600  # URL expires in 1 hour
    )
    return presigned_url

# Main app
def main():
    st.title("Proforma Invoice Generator")
    
    # Load data from S3
    try:
        df = read_excel_from_s3(S3_BUCKET_NAME, "catafactuapp.xlsx")
    except Exception as e:
        st.error(f"Failed to load data from S3: {e}")
        return
    
    # Select price type
    price_type = st.radio("Select Price Type", ["prix-super-gros", "prix-gros", "prix-detaille"])
    
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
        
        # Generate and upload PDF
        if st.button("Generate Proforma Invoice"):
            pdf_url = generate_and_upload_pdf(st.session_state['items'], price_type)
            st.success(f"Proforma Invoice Generated! Download [here]({pdf_url}).")
        
        if st.button("Clear Items"):
            st.session_state['items'] = []
            st.success("Items cleared!")

if __name__ == "__main__":
    main()