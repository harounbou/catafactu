#!/usr/bin/env python3
# Script to fix the PyFPDF and fpdf2 conflict

import subprocess
import sys

def fix_fpdf_conflict():
    """
    Uninstall PyFPDF and ensure fpdf2 is properly installed to resolve the conflict.
    """
    print("Fixing PyFPDF and fpdf2 conflict...")
    
    try:
        # Uninstall PyFPDF
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "--yes", "pypdf"])
        print("Successfully uninstalled PyFPDF")
        
        # Upgrade fpdf2
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "fpdf2"])
        print("Successfully upgraded fpdf2")
        
        print("\nConflict resolved! You can now run the application without warnings.")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print("\nPlease manually run the following commands:")
        print("pip uninstall --yes pypdf")
        print("pip install --upgrade fpdf2")

if __name__ == "__main__":
    fix_fpdf_conflict()