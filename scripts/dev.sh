#!/bin/bash
# Development script for running all checks locally

set -e

echo "🧪 Running development checks..."
echo "================================"

# Check if we're in the right directory
if [ ! -f "src/bot.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Install development dependencies if not already installed
if ! python -c "import black, isort, mypy" 2>/dev/null; then
    echo "📦 Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

echo "🔍 Running linting checks..."

# Run black formatting check
echo "  - Checking code formatting with black..."
black --check src/ test/ || {
    echo "❌ Code formatting issues found. Run 'black src/ test/' to fix."
    exit 1
}

# Run isort import sorting check
echo "  - Checking import sorting with isort..."
isort --check-only src/ test/ || {
    echo "❌ Import sorting issues found. Run 'isort src/ test/' to fix."
    exit 1
}

# Run mypy type checking
echo "  - Running mypy type checking..."
mypy src/ --ignore-missing-imports

echo "🔒 Running security checks..."

# Run bandit security scanning
echo "  - Running bandit security scan..."
bandit -r src/ -f json -o bandit-report.json || true

# Run safety vulnerability check
echo "  - Running safety vulnerability check..."
safety check --json --output safety-report.json || true

echo "🧪 Running tests..."

# Run tests with pytest
echo "  - Running pytest tests..."
pytest test/

# Run tests with unittest
echo "  - Running unittest tests..."
python test/run_tests.py --simple

echo "🐳 Testing Docker build..."

# Test Docker build
echo "  - Building Docker image..."
docker build -t valheim-discord-bot:dev .

echo "✅ All checks passed!"
echo "📊 Coverage report available in htmlcov/index.html"
echo "🔒 Security reports available in bandit-report.json and safety-report.json" 