#!/bin/bash
# Run script for backend - ensures virtual environment is activated

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    # Activate virtual environment
    source venv/bin/activate
fi

# Check if FastAPI is installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "FastAPI not found. Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Run the application
echo "Starting backend server..."
python app.py

