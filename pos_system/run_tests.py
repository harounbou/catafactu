#!/usr/bin/env python3
"""
Test runner for the POS system.
Discovers and runs all tests in the tests directory.
"""
import unittest
import sys
import os

def run_tests():
    """
    Discover and run all tests in the tests directory.
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create test loader
    loader = unittest.TestLoader()
    
    # Discover tests in the tests directory
    test_suite = loader.discover(os.path.join(script_dir, 'tests'))
    
    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    result = runner.run(test_suite)
    
    # Return True if all tests pass, False otherwise
    return result.wasSuccessful()

if __name__ == '__main__':
    print("Running POS system tests...")
    success = run_tests()
    
    if success:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)