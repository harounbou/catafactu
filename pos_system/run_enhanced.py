#!/usr/bin/env python3
"""
Script to run the enhanced version of the POS system.
This script:
1. Fixes the PyFPDF and fpdf2 conflict
2. Updates stock calculations
3. Launches the enhanced application
"""
import subprocess
import sys
import os
import time

def print_step(step_number, description):
    """Print a formatted step message."""
    print(f"\n[Step {step_number}] {description}")
    print("=" * 60)

def run_command(command, description):
    """Run a command and handle errors."""
    print_step(command[0], description)
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(e.stderr)
        return False

def main():
    """Main function to run the enhanced POS system."""
    print("\n" + "=" * 60)
    print("ENHANCED POS SYSTEM LAUNCHER")
    print("=" * 60)
    
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Step 1: Fix PyFPDF and fpdf2 conflict
    print_step(1, "Fixing PyFPDF and fpdf2 conflict")
    try:
        subprocess.run([sys.executable, "fix_fpdf_conflict.py"], check=True)
    except subprocess.CalledProcessError:
        print("Warning: Could not fix PyFPDF conflict automatically.")
        print("You may need to manually run: pip uninstall --yes pypdf && pip install --upgrade fpdf2")
    
    # Step 2: Update stock calculations
    print_step(2, "Updating stock calculations")
    try:
        subprocess.run([sys.executable, "update_stock_calculation.py"], check=True)
    except subprocess.CalledProcessError:
        print("Warning: Could not update stock calculations.")
        print("Stock quantities may not be accurate.")
    
    # Step 3: Create logs directory
    print_step(3, "Setting up environment")
    os.makedirs("logs", exist_ok=True)
    os.makedirs("generated_pdfs", exist_ok=True)
    
    # Step 4: Launch the enhanced application
    print_step(4, "Launching enhanced POS system")
    print("The application will start in a moment...")
    time.sleep(2)
    
    try:
        # Use the enhanced app if it exists, otherwise fall back to the original
        app_path = "app_enhanced.py" if os.path.exists("app_enhanced.py") else "app.py"
        subprocess.run(["streamlit", "run", app_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching application: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()