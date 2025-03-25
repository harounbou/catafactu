import os
import sqlite3
from collections import defaultdict

# Configuration
DB_PATH = '/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/data/pos_system.db'
PROJECT_ROOT = '/Users/h.boukhalfa/Desktop/pos/catafactu/pos_system/'
IMAGES_DIR = os.path.join(PROJECT_ROOT, 'images')

def main():
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Phase 1: Index all images
    image_data = defaultdict(lambda: {'paths': [], 'colors': set()})

    for root, _, files in os.walk(IMAGES_DIR):
        for filename in files:
            # Process only image files
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue

            # Split filename components
            base_name = os.path.splitext(filename)[0]
            parts = base_name.split('_')
            
            if len(parts) < 2:
                continue  # Invalid format

            # Extract reference and color components
            ref = parts[0].lower()
            color_parts = parts[1:]

            # Remove numeric suffix if present
            if color_parts and color_parts[-1].isdigit():
                color_parts = color_parts[:-1]

            if not color_parts:
                continue  # No color information

            # Create color name
            color_name = '_'.join(color_parts).lower()

            # Get relative path
            abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(abs_path, PROJECT_ROOT)

            # Store data
            image_data[ref]['paths'].append(rel_path)
            image_data[ref]['colors'].add(color_name)

    # Phase 2: Update database
    cursor.execute("SELECT reference FROM products")
    for row in cursor.fetchall():
        ref = row[0]
        
        # Validate reference
        if not ref or len(ref.strip()) < 2:
            continue

        # Find matching images
        data = image_data.get(ref.strip().lower())
        if not data or not data['paths']:
            continue

        # Prepare values
        sorted_paths = sorted(data['paths'])
        images_value = ', '.join(sorted_paths)
        
        sorted_colors = sorted(data['colors'])
        colors_value = ', '.join(sorted_colors)

        # Update database
        cursor.execute("""
            UPDATE products 
            SET images = ?, `couleurs-dispo-usine` = ?
            WHERE reference = ?
        """, (images_value, colors_value, ref))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()