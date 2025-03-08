import pandas as pd
import streamlit as st
from .utils import fetch_df_from_db, save_df_to_db

def load_products():
    df = fetch_df_from_db('products')
    if df.empty:
        st.error("Failed to load products.")
        return pd.DataFrame(columns=[
            "reference", "denomination", "quantite_actuelle", "prix-super-gros",
            "prix-gros", "prix-détail", "couleurs-dispo-usine", "images", "category"
        ])
    return df

def update_stock(products_df, items):
    for item in items:
        idx = products_df[products_df['reference'] == item['reference']].index[0]
        current_stock = products_df.loc[idx, 'quantite_actuelle']
        if current_stock >= item['Quantity']:
            products_df.loc[idx, 'quantite_actuelle'] -= item['Quantity']
            # Update quantite_vendue if it exists
            if 'quantite_vendue' in products_df.columns:
                products_df.loc[idx, 'quantite_vendue'] = products_df.loc[idx, 'quantite_vendue'] + item['Quantity']
        else:
            st.error(f"Insufficient stock for {item['denomination']}")
            return False
    save_df_to_db(products_df, 'products')
    return True

def restock_product(products_df, reference, quantity, cost):
    idx = products_df[products_df['reference'] == reference].index[0]
    products_df.loc[idx, 'quantite_actuelle'] += quantity
    # Update quantite_restockee if it exists
    if 'quantite_restockee' in products_df.columns:
        products_df.loc[idx, 'quantite_restockee'] = products_df.loc[idx, 'quantite_restockee'] + quantity
    save_df_to_db(products_df, 'products')
    return cost * quantity