import os
import re

def rename_images():
    image_dir = 'images/'
    pattern = re.compile(r'^(.*?)\s*\((\d+)\)\.(jpe?g|png)$', re.IGNORECASE)

    for root, dirs, files in os.walk(image_dir):
        for filename in files:
            match = pattern.match(filename)
            if match:
                base = match.group(1).rstrip()
                num = match.group(2)
                ext = match.group(3).lower()
                
                new_name = f"{base}_{num}.{ext}"
                old_path = os.path.join(root, filename)
                new_path = os.path.join(root, new_name)

                os.rename(old_path, new_path)
                print(f"Renamed: {os.path.relpath(old_path)} -> {os.path.relpath(new_path)}")

if __name__ == '__main__':
    rename_images()