# pos_system/modules/product_management.py
import pandas as pd
import streamlit as st
from .utils import read_local_excel, save_excel

PRODUCTS_FILE = "data/products.xlsx"

def load_products():
    df = read_local_excel(PRODUCTS_FILE)
    if df is None:
        st.error("Failed to load products.")
        return pd.DataFrame(columns=["denomination", "reference", "category", "prix-super-gros", "prix-gros", "prix-détail", "quantite_actuelle", "couleurs-dispo-usine", "images"])
    return df

def update_stock(products_df, items):
    for item in items:
        idx = products_df[products_df['reference'] == item['reference']].index[0]
        current_stock = products_df.loc[idx, 'quantite_actuelle']
        if current_stock >= item['Quantity']:
            products_df.loc[idx, 'quantite_actuelle'] -= item['Quantity']
        else:
            st.error(f"Insufficient stock for {item['denomination']}")
            return False
    save_excel(products_df, PRODUCTS_FILE)
    return True

def restock_product(products_df, reference, quantity, cost):
    idx = products_df[products_df['reference'] == reference].index[0]
    products_df.loc[idx, 'quantite_actuelle'] += quantity
    save_excel(products_df, PRODUCTS_FILE)
    return cost * quantity