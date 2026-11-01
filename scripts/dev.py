#!/usr/bin/env python3
"""
Development script for running all checks locally.
This is a Python alternative to the bash script.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a command and handle errors."""
    print(f"  - {description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(e.stderr)
        return False


def main():
    """Run all development checks."""
    print("🧪 Running development checks...")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("src/bot.py").exists():
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)

    # Install development dependencies if needed
    try:
        import black
        import isort
        import mypy
    except ImportError:
        print("📦 Installing development dependencies...")
        run_command(
            "pip install -r requirements-dev.txt", "Installing dev dependencies"
        )

    print("🔍 Running linting checks...")

    # Run black formatting check
    if not run_command(
        "black --check src/ test/", "Checking code formatting with black"
    ):
        print("❌ Code formatting issues found. Run 'black src/ test/' to fix.")
        sys.exit(1)

    # Run isort import sorting check
    if not run_command(
        "isort --check-only src/ test/", "Checking import sorting with isort"
    ):
        print("❌ Import sorting issues found. Run 'isort src/ test/' to fix.")
        sys.exit(1)

    # Run mypy type checking
    run_command("mypy src/ --ignore-missing-imports", "Running mypy type checking")

    print("🔒 Running security checks...")

    # Run bandit security scanning
    run_command(
        "bandit -r src/ -f json -o bandit-report.json",
        "Running bandit security scan",
        check=False,
    )

    # Run safety vulnerability check
    run_command(
        "safety check --json --output safety-report.json",
        "Running safety vulnerability check",
        check=False,
    )

    print("🧪 Running tests...")

    # Run tests with pytest
    if not run_command(
        "pytest test/",
        "Running pytest tests",
    ):
        print("❌ Tests failed!")
        sys.exit(1)

    # Run tests with unittest
    if not run_command("python test/run_tests.py --simple", "Running unittest tests"):
        print("❌ Unittest tests failed!")
        sys.exit(1)

    print("🐳 Testing Docker build...")

    # Test Docker build
    if not run_command(
        "docker build -t valheim-discord-bot:dev .", "Building Docker image"
    ):
        print("❌ Docker build failed!")
        sys.exit(1)

    print("✅ All checks passed!")
    print("📊 Coverage report available in htmlcov/index.html")
    print("🔒 Security reports available in bandit-report.json and safety-report.json")


if __name__ == "__main__":
    main()
