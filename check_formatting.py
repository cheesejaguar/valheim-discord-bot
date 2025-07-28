#!/usr/bin/env python3
"""
Script to check if all black formatting issues are fixed.
"""

import subprocess
import sys


def check_black():
    """Check if all files are properly formatted with black."""
    print("🔍 Checking black formatting...")
    
    try:
        result = subprocess.run(
            ["python", "-m", "black", "--check", "src/", "test/"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print("✅ All files are properly formatted with black!")
            return True
        else:
            print("❌ Black formatting issues found:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("❌ Black not found. Install with: pip install black")
        return False


def check_isort():
    """Check if all imports are properly sorted with isort."""
    print("🔍 Checking import sorting...")
    
    try:
        result = subprocess.run(
            ["python", "-m", "isort", "--check-only", "src/", "test/"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print("✅ All imports are properly sorted!")
            return True
        else:
            print("❌ Import sorting issues found:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("❌ isort not found. Install with: pip install isort")
        return False


def main():
    """Run all formatting checks."""
    print("🧪 Running formatting checks...")
    print("=" * 40)
    
    black_ok = check_black()
    isort_ok = check_isort()
    
    if black_ok and isort_ok:
        print("\n✅ All formatting checks passed!")
        return 0
    else:
        print("\n❌ Some formatting checks failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 