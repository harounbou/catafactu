# POS System - Takideco

A comprehensive Point of Sale (POS) system built with Streamlit for managing inventory, sales, clients, and more.

## Features

- User authentication and access control
- Product management with color-specific inventory
- Client management
- Transaction processing (sales, proformas, orders)
- PDF generation for receipts, invoices, and orders
- Stock management and tracking
- Financial tracking (expenditures, staff payments, till balance)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pos_system
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Fix PyFPDF and fpdf2 conflict:
```bash
python fix_fpdf_conflict.py
```

## Usage

Run the application:
```bash
streamlit run app.py
```

### Default Login Credentials

- Admin: username `admin`, password `admin`
- Operator: username `eulma`, password `eulma`

## Project Structure

- `app.py`: Main application file
- `modules/`: Core functionality modules
  - `client_management.py`: Client-related functions
  - `pdf_generator.py`: PDF generation for receipts, proformas, etc.
  - `pos.py`: Point of Sale functionality
  - `product_management.py`: Product and inventory management
  - `proforma.py`: Proforma invoice handling
  - `restock.py`: Inventory restocking
  - `transaction_management.py`: Transaction processing
  - `utils.py`: Utility functions
- `data/`: Database and configuration files
- `images/`: Product images
- `backups/`: Database backups

## Database

The application uses SQLite for data storage. The database file is located at `data/pos_system.db`.

## Backup

Automatic daily backups are scheduled at midnight. Manual backups can be created from the Articles page.

## Known Issues

- PyFPDF and fpdf2 conflict: Run `python fix_fpdf_conflict.py` to resolve.

## License

[Specify your license here]