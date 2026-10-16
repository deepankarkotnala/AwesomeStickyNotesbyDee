@echo off
rem Builds the app's own Python environment (.venv): Python 3.14 plus the exact libraries in requirements.txt.
rem Run it once after copying the app to a new PC, and again if the app says its environment is broken.
cd /d "%~dp0"
echo Close Awesome Sticky Notes before continuing.
pause
py -3.14 -m venv --clear .venv || goto :error
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt || goto :error
echo.
echo Done. Double-click AwesomeStickyNotes.pyw to start the app.
pause
exit /b 0

:error
echo.
echo Setup failed. It needs Python 3.14 from https://www.python.org/downloads/ - install it and run this again.
pause
exit /b 1
