"""
Unit tests for utility functions.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.utils import (
    validate_email,
    validate_phone,
    get_full_image_path,
    get_db_color_name,
    sanitize_text,
    truncate_text
)

class TestUtilsFunctions(unittest.TestCase):
    """Test cases for utility functions."""
    
    def test_validate_email(self):
        """Test email validation function."""
        # Valid emails
        self.assertTrue(validate_email("test@example.com"))
        self.assertTrue(validate_email("user.name+tag@example.co.uk"))
        
        # Invalid emails
        self.assertFalse(validate_email("invalid-email"))
        self.assertFalse(validate_email("missing@domain"))
        self.assertFalse(validate_email("@example.com"))
        
        # Empty email should return True (as per current implementation)
        self.assertTrue(validate_email(""))
        self.assertTrue(validate_email(None))
    
    def test_validate_phone(self):
        """Test phone validation function."""
        # Valid phone (10 digits)
        self.assertTrue(validate_phone("1234567890"))
        
        # Invalid phones
        self.assertFalse(validate_phone("123456789"))  # Too short
        self.assertFalse(validate_phone("12345678901"))  # Too long
        self.assertFalse(validate_phone("abcdefghij"))  # Non-numeric
        
        # Empty phone should return True (as per current implementation)
        self.assertTrue(validate_phone(""))
        self.assertTrue(validate_phone(None))
    
    def test_get_db_color_name(self):
        """Test color name mapping function."""
        self.assertEqual(get_db_color_name("brown gradient"), "brown_deg")
        self.assertEqual(get_db_color_name("grey gradient"), "grey_deg")
        self.assertEqual(get_db_color_name("blue"), "blue")
        self.assertEqual(get_db_color_name("Green Bottle"), "green_bottle")
    
    def test_sanitize_text(self):
        """Test text sanitization function."""
        self.assertEqual(sanitize_text("It's a test"), "It's a test")
        self.assertEqual(sanitize_text(""), "")
        self.assertEqual(sanitize_text(None), "")
    
    def test_truncate_text(self):
        """Test text truncation function."""
        self.assertEqual(truncate_text("Short text"), "Short text")
        self.assertEqual(truncate_text("This is a very long text that should be truncated"), "This is a very...")
        self.assertEqual(truncate_text("Exactly 14 char"), "Exactly 14 char")
        self.assertEqual(truncate_text("15 characters!"), "15 characters...")
        
        # Custom max length
        self.assertEqual(truncate_text("Short text", max_length=5), "Short...")
    
    @patch('os.path.exists')
    @patch('os.path.isabs')
    def test_get_full_image_path(self, mock_isabs, mock_exists):
        """Test image path resolution function."""
        # Setup mocks
        mock_isabs.return_value = False
        
        # Test when path exists
        mock_exists.return_value = True
        result = get_full_image_path("test.jpg")
        self.assertIsNotNone(result)
        
        # Test when path doesn't exist
        mock_exists.return_value = False
        result = get_full_image_path("nonexistent.jpg")
        self.assertIsNone(result)
        
        # Test with None input
        result = get_full_image_path(None)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()