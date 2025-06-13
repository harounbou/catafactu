"""
Data validation module for the POS system.
Provides functions to validate user inputs and data integrity.
"""
import re
import pandas as pd
from datetime import datetime

# Regular expressions for validation
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_REGEX = r'^\d{10}$'
REFERENCE_REGEX = r'^[A-Za-z0-9]{3,10}$'
PRICE_REGEX = r'^\d+(\.\d{1,2})?$'

def validate_client_data(client_data):
    """
    Validate client data before saving to database.
    
    Args:
        client_data (dict): Client data to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Required fields
    if not client_data.get('nom_client'):
        return False, "Le nom du client est obligatoire"
    
    if not client_data.get('telephone_client'):
        return False, "Le numéro de téléphone est obligatoire"
    
    # Phone number format
    phone = client_data.get('telephone_client', '')
    if phone and not re.match(PHONE_REGEX, phone):
        return False, "Le numéro de téléphone doit contenir 10 chiffres"
    
    # Email format (if provided)
    email = client_data.get('email_client', '')
    if email and not re.match(EMAIL_REGEX, email):
        return False, "Format d'email invalide"
    
    return True, ""

def validate_product_data(product_data):
    """
    Validate product data before saving to database.
    
    Args:
        product_data (dict): Product data to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Required fields
    if not product_data.get('reference'):
        return False, "La référence du produit est obligatoire"
    
    if not product_data.get('denomination'):
        return False, "La dénomination du produit est obligatoire"
    
    # Reference format
    reference = product_data.get('reference', '')
    if not re.match(REFERENCE_REGEX, reference):
        return False, "La référence doit contenir entre 3 et 10 caractères alphanumériques"
    
    # Price validation
    price_fields = ['prix-super-gros', 'prix-gros', 'prix-détail']
    for field in price_fields:
        price = product_data.get(field)
        if price is not None:
            try:
                price_value = float(price)
                if price_value < 0:
                    return False, f"Le {field} ne peut pas être négatif"
            except (ValueError, TypeError):
                return False, f"Le {field} doit être un nombre valide"
    
    # Stock validation
    color_fields = [
        'uni_colour', 'default_colour', 'brown', 'brown_deg', 'blue', 'white',
        'black', 'green_bottle', 'red', 'grey', 'grey_deg', 'beige', 'yellow',
        'orange', 'garnet', 'golden', 'green', 'rose'
    ]
    
    for field in color_fields:
        if field in product_data and product_data[field] is not None:
            try:
                qty = int(product_data[field])
                if qty < 0:
                    return False, f"La quantité pour {field} ne peut pas être négative"
            except (ValueError, TypeError):
                return False, f"La quantité pour {field} doit être un nombre entier"
    
    return True, ""

def validate_transaction_data(transaction_data):
    """
    Validate transaction data before processing.
    
    Args:
        transaction_data (dict): Transaction data to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Required fields
    if not transaction_data.get('client_info'):
        return False, "Les informations client sont obligatoires"
    
    if not transaction_data.get('items') or len(transaction_data['items']) == 0:
        return False, "La transaction doit contenir au moins un article"
    
    # Validate payment details
    payment_details = transaction_data.get('payment_details', {})
    if not payment_details:
        return False, "Les détails de paiement sont obligatoires"
    
    total_payment = sum(float(amount) for amount in payment_details.values())
    final_amount = float(transaction_data.get('final_amount', 0))
    
    # For completed transactions, payment must match final amount
    if transaction_data.get('status') == 'completed' and total_payment != final_amount:
        return False, f"Le montant payé ({total_payment}) ne correspond pas au montant final ({final_amount})"
    
    # For deposit payments, validate deposit amount
    if transaction_data.get('status') == 'deposit_paid':
        deposit_amount = float(transaction_data.get('deposit_amount', 0))
        if deposit_amount <= 0:
            return False, "Le montant de l'acompte doit être supérieur à zéro"
        if deposit_amount > final_amount:
            return False, "Le montant de l'acompte ne peut pas dépasser le montant final"
    
    return True, ""

def sanitize_input(input_str):
    """
    Sanitize user input to prevent SQL injection and other security issues.
    
    Args:
        input_str: The input string to sanitize
        
    Returns:
        str: Sanitized string
    """
    if input_str is None:
        return ""
    
    # Convert to string if not already
    input_str = str(input_str)
    
    # Remove potentially dangerous characters
    sanitized = input_str.replace("'", "''")  # Escape single quotes for SQL
    sanitized = sanitized.replace(";", "")    # Remove semicolons
    
    return sanitized