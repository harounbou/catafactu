import pandas as pd
from datetime import datetime

# Load the data (replace with your file path)
df = pd.read_csv("dirty_products.csv", delimiter="\t")  # Assuming tab-delimited

# --------------------------------------
# Fix 1: Remove line breaks in product names
# --------------------------------------
df['denomination'] = df['denomination'].str.replace('\n', ' ', regex=False)

# --------------------------------------
# Fix 2: Standardize color names
# --------------------------------------
df['couleurs-dispo-usine'] = (
    df['couleurs-dispo-usine']
    .str.replace('brown_deg', 'brown_gradient', regex=False)
    .str.replace('grey_deg', 'grey_gradient', regex=False)
)

# --------------------------------------
# Fix 3: Clean image paths
# --------------------------------------
def clean_image_paths(paths):
    if pd.isna(paths):
        return ""
    # Replace absolute paths with relative ones
    paths = paths.replace('/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/', './')
    # Replace spaces and commas in filenames
    paths = (
        paths.replace(' ', '_')  # Spaces to underscores
        .replace(',_', ';')      # Fix separator consistency
        .replace(',', ';')       # Use semicolons as delimiters
    )
    return paths

df['images'] = df['images'].apply(clean_image_paths)

# --------------------------------------
# Fix 4: Clean color delimiters
# --------------------------------------
df['couleurs-dispo-usine'] = df['couleurs-dispo-usine'].str.replace(', ', ';')

# --------------------------------------
# Fix 5: Validate categories
# --------------------------------------
df['category'] = (
    df['category']
    .fillna('MISCELLANEOUS')  # Replace NULL categories
    .str.upper()              # Standardize to uppercase
)

# --------------------------------------
# Fix 6: Fix numerical fields and dates
# --------------------------------------
numeric_cols = ['quantite_initiale', 'quantite_restockee', 'quantite_vendue']
df[numeric_cols] = df[numeric_cols].fillna(0)

# Fix invalid future dates (e.g., 2025-04-07 → 2023-04-07)
df['last_updated'] = df['last_updated'].str.replace('2025', '2023')

# --------------------------------------
# Fix 7: Remove test entries (e.g., "jeter")
# --------------------------------------
df = df[~df['denomination'].str.contains('jeter', case=False, na=False)]

# --------------------------------------
# Fix 8: Drop unused columns
# --------------------------------------
unused_columns = ['brown', 'brown_deg', 'blue', 'white', 'black', 'green_bottle', 
                  'red', 'grey', 'grey_deg', 'beige', 'yellow', 'orange', 'garnet', 
                  'golden', 'green', 'rose', 'note', 'quantite_vendu_actue', 
                  'discontinued', 'version', 'quantite_actuelle']
df = df.drop(columns=unused_columns, errors='ignore')

# --------------------------------------
# Fix 9: Validate prices (example: flag items with 0.0 price)
# --------------------------------------
price_cols = ['prix-super-gros', 'prix-gros', 'prix-détail']
zero_prices = df[df[price_cols].sum(axis=1) == 0]
if not zero_prices.empty:
    print("WARNING: Items with 0.0 prices found:")
    print(zero_prices[['reference', 'denomination']])

# --------------------------------------
# Save cleaned data
# --------------------------------------
df.to_csv("cleaned_products.csv", index=False, sep='\t')
print("Cleaning complete! Saved to cleaned_products.csv")