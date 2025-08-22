@echo off
echo PDF Fun Studio - Starting up...
echo.

echo Checking Python installation...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 not found! Please install Python 3.12 and add it to PATH
    pause
    exit /b 1
)

echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js not found! Please install Node.js 16+ and add it to PATH
    pause
    exit /b 1
)

echo Installing Python dependencies...
py -3.12 -m pip install -r requirements.txt

echo Installing Node.js dependencies...
npm install

echo.
echo Starting PDF Fun Studio...
echo Open your browser to: http://localhost:3000
echo Press Ctrl+C to stop the server
echo.

npm start

pause
