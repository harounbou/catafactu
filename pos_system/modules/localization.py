"""
Localization module for the POS system.
Provides translations for UI elements and messages.
"""

# Available languages
LANGUAGES = {
    "French": "fr",
    "Arabic": "ar",
    "English": "en"
}

# Translations dictionary
TRANSLATIONS = {
    # Dashboard
    "dashboard_title": {
        "fr": "Tableau de Bord",
        "ar": "لوحة التحكم",
        "en": "Dashboard"
    },
    "total_sales": {
        "fr": "Ventes Totales",
        "ar": "إجمالي المبيعات",
        "en": "Total Sales"
    },
    "top_items": {
        "fr": "Articles les Plus Vendus",
        "ar": "المنتجات الأكثر مبيعًا",
        "en": "Top Selling Items"
    },
    "till_balance": {
        "fr": "Solde de la Caisse",
        "ar": "رصيد الصندوق",
        "en": "Till Balance"
    },
    
    # POS
    "pos_title": {
        "fr": "Point de Vente (POS)",
        "ar": "نقطة البيع",
        "en": "Point of Sale (POS)"
    },
    "reset_transaction": {
        "fr": "Réinitialiser Transaction",
        "ar": "إعادة تعيين المعاملة",
        "en": "Reset Transaction"
    },
    "stock_checker": {
        "fr": "Vérificateur de Stock",
        "ar": "فاحص المخزون",
        "en": "Stock Checker"
    },
    "configuration": {
        "fr": "Configuration",
        "ar": "الإعدادات",
        "en": "Configuration"
    },
    "price_type": {
        "fr": "Type de prix",
        "ar": "نوع السعر",
        "en": "Price Type"
    },
    "discount_type": {
        "fr": "Type de remise",
        "ar": "نوع الخصم",
        "en": "Discount Type"
    },
    "discount_value": {
        "fr": "Valeur Remise",
        "ar": "قيمة الخصم",
        "en": "Discount Value"
    },
    "apply_tva": {
        "fr": "Appliquer TVA 19%",
        "ar": "تطبيق ضريبة القيمة المضافة 19%",
        "en": "Apply VAT 19%"
    },
    "invoice_language": {
        "fr": "Langue de la facture",
        "ar": "لغة الفاتورة",
        "en": "Invoice Language"
    },
    "notes": {
        "fr": "Notes",
        "ar": "ملاحظات",
        "en": "Notes"
    },
    
    # Client Management
    "client_management": {
        "fr": "Gestion Client",
        "ar": "إدارة العملاء",
        "en": "Client Management"
    },
    "new_client": {
        "fr": "Nouveau Client",
        "ar": "عميل جديد",
        "en": "New Client"
    },
    "existing_client": {
        "fr": "Client Existant",
        "ar": "عميل موجود",
        "en": "Existing Client"
    },
    "search_client": {
        "fr": "Rechercher Client",
        "ar": "البحث عن عميل",
        "en": "Search Client"
    },
    "client_name": {
        "fr": "Nom",
        "ar": "الاسم",
        "en": "Name"
    },
    "client_firstname": {
        "fr": "Prénom",
        "ar": "الاسم الأول",
        "en": "First Name"
    },
    "client_company": {
        "fr": "Entreprise",
        "ar": "الشركة",
        "en": "Company"
    },
    "client_phone": {
        "fr": "Téléphone",
        "ar": "الهاتف",
        "en": "Phone"
    },
    "client_address": {
        "fr": "Adresse",
        "ar": "العنوان",
        "en": "Address"
    },
    
    # Item Selection
    "item_selection": {
        "fr": "Sélection d'Articles",
        "ar": "اختيار المنتجات",
        "en": "Item Selection"
    },
    "search_items": {
        "fr": "Recherche Articles",
        "ar": "البحث عن المنتجات",
        "en": "Search Items"
    },
    "available_items": {
        "fr": "Articles Disponibles",
        "ar": "المنتجات المتاحة",
        "en": "Available Items"
    },
    "color": {
        "fr": "Couleur",
        "ar": "اللون",
        "en": "Color"
    },
    "quantity": {
        "fr": "Quantité",
        "ar": "الكمية",
        "en": "Quantity"
    },
    "add_to_cart": {
        "fr": "Ajouter au Panier",
        "ar": "إضافة إلى السلة",
        "en": "Add to Cart"
    },
    
    # Cart
    "cart": {
        "fr": "Panier",
        "ar": "سلة التسوق",
        "en": "Cart"
    },
    "items": {
        "fr": "articles",
        "ar": "منتجات",
        "en": "items"
    },
    "subtotal": {
        "fr": "Sous-total",
        "ar": "المجموع الفرعي",
        "en": "Subtotal"
    },
    "discount": {
        "fr": "Remise",
        "ar": "الخصم",
        "en": "Discount"
    },
    "vat": {
        "fr": "TVA (19%)",
        "ar": "ضريبة القيمة المضافة (19%)",
        "en": "VAT (19%)"
    },
    "total": {
        "fr": "Total",
        "ar": "المجموع",
        "en": "Total"
    },
    "validate_cart": {
        "fr": "Valider Panier",
        "ar": "تأكيد السلة",
        "en": "Validate Cart"
    },
    
    # Transaction Types
    "finalize_transaction": {
        "fr": "Finaliser Transaction",
        "ar": "إنهاء المعاملة",
        "en": "Finalize Transaction"
    },
    "transaction_type": {
        "fr": "Type de Transaction",
        "ar": "نوع المعاملة",
        "en": "Transaction Type"
    },
    "immediate_purchase": {
        "fr": "Achat Immédiat",
        "ar": "شراء فوري",
        "en": "Immediate Purchase"
    },
    "custom_order": {
        "fr": "Commande Personnalisée",
        "ar": "طلب مخصص",
        "en": "Custom Order"
    },
    "account_purchase": {
        "fr": "Achat en Compte",
        "ar": "شراء على الحساب",
        "en": "Account Purchase"
    },
    "generate_order": {
        "fr": "Générer Bon de Commande",
        "ar": "إنشاء أمر شراء",
        "en": "Generate Purchase Order"
    },
    
    # Payment
    "payment_option": {
        "fr": "Option de Paiement",
        "ar": "خيار الدفع",
        "en": "Payment Option"
    },
    "full_payment": {
        "fr": "Paiement Complet",
        "ar": "دفع كامل",
        "en": "Full Payment"
    },
    "deposit": {
        "fr": "Acompte",
        "ar": "دفعة مقدمة",
        "en": "Deposit"
    },
    "deposit_amount": {
        "fr": "Montant de l'acompte",
        "ar": "مبلغ الدفعة المقدمة",
        "en": "Deposit Amount"
    },
    "remaining_amount": {
        "fr": "Reste à payer",
        "ar": "المبلغ المتبقي",
        "en": "Remaining Amount"
    },
    "cash": {
        "fr": "Espèces",
        "ar": "نقدًا",
        "en": "Cash"
    },
    "bank_transfer": {
        "fr": "Virement",
        "ar": "تحويل بنكي",
        "en": "Bank Transfer"
    },
    "ccp": {
        "fr": "CCP",
        "ar": "CCP",
        "en": "CCP"
    },
    "check": {
        "fr": "Chèque",
        "ar": "شيك",
        "en": "Check"
    },
    
    # Messages
    "success": {
        "fr": "Succès",
        "ar": "نجاح",
        "en": "Success"
    },
    "error": {
        "fr": "Erreur",
        "ar": "خطأ",
        "en": "Error"
    },
    "warning": {
        "fr": "Attention",
        "ar": "تحذير",
        "en": "Warning"
    },
    "info": {
        "fr": "Information",
        "ar": "معلومات",
        "en": "Information"
    },
    "transaction_registered": {
        "fr": "Transaction enregistrée!",
        "ar": "تم تسجيل المعاملة!",
        "en": "Transaction registered!"
    },
    "insufficient_stock": {
        "fr": "Stock insuffisant",
        "ar": "المخزون غير كافٍ",
        "en": "Insufficient stock"
    },
    "payment_mismatch": {
        "fr": "Le montant payé ne correspond pas au total",
        "ar": "المبلغ المدفوع لا يتطابق مع المجموع",
        "en": "Payment amount doesn't match total"
    }
}

def get_translation(key, language="fr"):
    """
    Get translation for a key in the specified language.
    
    Args:
        key (str): Translation key
        language (str): Language code ('fr', 'ar', 'en')
        
    Returns:
        str: Translated text or key if translation not found
    """
    if key in TRANSLATIONS and language in TRANSLATIONS[key]:
        return TRANSLATIONS[key][language]
    return key

def get_language_code(language_name):
    """
    Get language code from language name.
    
    Args:
        language_name (str): Language name ('French', 'Arabic', 'English')
        
    Returns:
        str: Language code ('fr', 'ar', 'en')
    """
    return LANGUAGES.get(language_name, "fr")