@echo off
echo Building RuSwitch...
pip install pyinstaller
pip install -r requirements.txt
pyinstaller --onefile --noconsole --icon=icon.ico --name=RuSwitch main.py
echo Done! Output: dist\RuSwitch.exe
pause
