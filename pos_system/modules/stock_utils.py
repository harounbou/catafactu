# modules/stock_utils.py
import streamlit as st
import pandas as pd
from .utils import get_full_image_path, find_image_path_for_color

def stock_checker_section(products_df, section_key_prefix=""):
    with st.expander("Vérificateur de Stock", expanded=False):
        search_term = st.text_input("Rechercher par nom ou référence", placeholder="Tapez le nom ou la référence", key=f"{section_key_prefix}stock_search")
        if st.button("Vérifier", key=f"{section_key_prefix}stock_check"):
            filtered_df = products_df[
                products_df['denomination'].str.contains(search_term, case=False, na=False) |
                products_df['reference'].str.contains(search_term, case=False, na=False)
            ]
            if not filtered_df.empty:
                for _, row in filtered_df.iterrows():
                    st.write(f"**{row['denomination']} ({row['reference']})**")
                    st.write(f"- Stock Total: {int(row['quantite_actuelle'])} unités")
                    colors = [color.strip() for color in row['couleurs-dispo-usine'].split(',')] if pd.notna(row['couleurs-dispo-usine']) else []
                    for color in colors:
                        color_lower = color.lower()
                        if color_lower in row.index and pd.notna(row[color_lower]):
                            stock = int(row[color_lower])
                            image_path = get_full_image_path(find_image_path_for_color(row['images'], color))
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                if image_path:
                                    st.image(image_path, width=50)
                                else:
                                    st.write("Image non disponible")
                            with col2:
                                st.write(f"- {color}: {stock} unités")
                                if stock <= 5:
                                    st.warning(f"Alerte: Stock faible pour {color} ({stock} unités restantes)")
                    if row['quantite_actuelle'] <= 5:
                        st.warning(f"Alerte: Stock total faible ({int(row['quantite_actuelle'])} unités restantes)")
            else:
                st.error("Aucun article trouvé.")