#!/usr/bin/env python3
"""
Test runner script for the Valheim Discord Bot.
This script provides an easy way to run all tests with coverage reporting.
"""

import os
import subprocess
import sys


def run_tests():
    """Run all tests with coverage reporting."""
    print("🧪 Running Valheim Discord Bot Tests")
    print("=" * 50)
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("❌ pytest not found. Please install test dependencies:")
        print("   pip install -r requirements-test.txt")
        return 1
    
    # Run tests with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "--verbose",
        "--cov=src.bot",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-fail-under=100",
        "test_bot_pytest.py",
        "test_bot.py"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
    
    return result.returncode


def run_simple_tests():
    """Run simple tests without pytest."""
    print("🧪 Running Simple Tests")
    print("=" * 30)
    
    try:
        import unittest
        from test_bot import TestValheimBot, TestValheimBotIntegration
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add test classes
        suite.addTests(loader.loadTestsFromTestCase(TestValheimBot))
        suite.addTests(loader.loadTestsFromTestCase(TestValheimBotIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print("\n✅ All simple tests passed!")
            return 0
        else:
            print("\n❌ Some simple tests failed!")
            return 1
            
    except ImportError as e:
        print(f"❌ Error importing test modules: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        exit_code = run_simple_tests()
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code) 