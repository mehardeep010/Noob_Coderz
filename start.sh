#!/bin/bash

echo "PDF Fun Studio - Starting up..."
echo

echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found! Please install Python 3.8+ and add it to PATH"
    exit 1
fi

echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "Node.js not found! Please install Node.js 16+ and add it to PATH"
    exit 1
fi

echo "Installing Python dependencies..."
python3.12 -m pip install -r requirements.txt

echo "Installing Node.js dependencies..."
npm install

echo
echo "Starting PDF Fun Studio..."
echo "Open your browser to: http://localhost:3000"
echo "Press Ctrl+C to stop the server"
echo

npm start
