@echo off
rem Fait demarrer l'interface web a chaque ouverture de session Windows.
rem Cree un raccourci vers serveur.bat dans le dossier Demarrage de l'utilisateur.
rem Pour annuler : desinstaller_demarrage_auto.bat
cd /d "%~dp0"

powershell -NoProfile -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Startup') + '\Correlations coraniques.lnk'); $s.TargetPath = '%~dp0serveur.bat'; $s.WorkingDirectory = '%~dp0'; $s.WindowStyle = 7; $s.Description = 'Interface web du harnais (http://127.0.0.1:8000)'; $s.Save()"
if errorlevel 1 (
  echo Le raccourci n'a pas pu etre cree.
  pause
  exit /b 1
)

echo Demarrage automatique installe.
echo A chaque ouverture de session, l'interface demarre dans une fenetre reduite.
echo Adresse a garder en favori : http://127.0.0.1:8000
echo.
echo Demarrage de l'interface maintenant...
start "" /min "%~dp0serveur.bat"
timeout /t 5 >nul
start "" http://127.0.0.1:8000
pause
