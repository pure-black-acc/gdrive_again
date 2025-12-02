@echo off
echo Updating pip...
python -m pip install --upgrade pip

echo Installing required packages...
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip install tk
pip install pyinstaller
pip install customtkinter
pip install pillow

echo Upgrading Google API libraries...
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

echo All dependencies installed successfully!
pause