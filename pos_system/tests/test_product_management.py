"""
Unit tests for product management functions.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import sqlite3

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.product_management import (
    calculate_current_quantity,
    check_stock,
    update_stock
)

class TestProductManagement(unittest.TestCase):
    """Test cases for product management functions."""
    
    def test_calculate_current_quantity(self):
        """Test calculation of current quantity from color quantities."""
        # Create a mock product row with color quantities
        product_row = {
            'brown': 5,
            'blue': 3,
            'white': 2,
            'black': 0,
            'reference': 'TEST001',
            'denomination': 'Test Product'
        }
        
        # Test calculation
        result = calculate_current_quantity(product_row)
        self.assertEqual(result, 10)  # 5 + 3 + 2 + 0 = 10
        
        # Test with empty product
        empty_product = {'reference': 'TEST002', 'denomination': 'Empty Product'}
        result = calculate_current_quantity(empty_product)
        self.assertEqual(result, 0)
    
    @patch('modules.product_management.load_products')
    def test_check_stock_sufficient(self, mock_load_products):
        """Test stock checking with sufficient stock."""
        # Mock product data
        mock_df = pd.DataFrame({
            'reference': ['TEST001'],
            'quantite_actuelle': [10],
            'brown': [5],
            'blue': [3],
            'white': [2]
        })
        mock_load_products.return_value = mock_df
        
        # Test with sufficient total stock
        result, message = check_stock('TEST001', 8)
        self.assertTrue(result)
        self.assertEqual(message, "In stock")
        
        # Test with sufficient color-specific stock
        result, message = check_stock('TEST001', 4, 'brown')
        self.assertTrue(result)
        self.assertEqual(message, "In stock")
    
    @patch('modules.product_management.load_products')
    def test_check_stock_insufficient(self, mock_load_products):
        """Test stock checking with insufficient stock."""
        # Mock product data
        mock_df = pd.DataFrame({
            'reference': ['TEST001'],
            'quantite_actuelle': [10],
            'brown': [5],
            'blue': [3],
            'white': [2]
        })
        mock_load_products.return_value = mock_df
        
        # Test with insufficient total stock
        result, message = check_stock('TEST001', 15)
        self.assertFalse(result)
        self.assertEqual(message, "Only 10 units available in total")
        
        # Test with insufficient color-specific stock
        result, message = check_stock('TEST001', 6, 'brown')
        self.assertFalse(result)
        self.assertEqual(message, "Only 5 units available in brown")
    
    @patch('modules.product_management.get_db_connection')
    def test_update_stock(self, mock_get_db_connection):
        """Test stock update functionality."""
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_db_connection.return_value = mock_conn
        
        # Mock cursor.fetchone to return a product
        mock_cursor.fetchone.return_value = {
            'reference': 'TEST001',
            'couleurs-dispo-usine': 'brown,blue,white',
            'brown': 5,
            'blue': 3,
            'white': 2
        }
        
        # Test updating stock for a specific color
        result = update_stock('TEST001', -2, 'brown')
        self.assertTrue(result)
        
        # Verify execute was called with the right parameters
        mock_cursor.execute.assert_any_call(
            "SELECT * FROM products WHERE reference = ?", 
            ('TEST001',)
        )
        
        # Test updating stock without specifying color
        result = update_stock('TEST001', 5, None)
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()