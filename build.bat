@echo off
echo ============================================
echo   Building Defaulter Letter Generator EXE
echo ============================================

REM Install dependencies (first time only)
pip install -r requirements.txt

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist DefaulterLetterGenerator.spec del DefaulterLetterGenerator.spec

REM Build the EXE
pyinstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name DefaulterLetterGenerator ^
  --add-data "template.docx;." ^
  app.py

echo.
echo ============================================
echo   DONE! Your EXE is in the dist\ folder
echo ============================================
pause