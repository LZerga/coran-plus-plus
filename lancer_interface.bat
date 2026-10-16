@echo off
rem Lance l'interface web du harnais et l'ouvre dans le navigateur.
rem Double-cliquer sur ce fichier depuis l'Explorateur Windows.
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo uv est introuvable. Fermer cette fenetre, rouvrir une session Windows, puis reessayer.
  pause
  exit /b 1
)

rem Si l'interface tourne deja, on ouvre seulement le navigateur.
curl -s -o NUL http://127.0.0.1:8000/api/meta
if not errorlevel 1 (
  echo L'interface tourne deja : ouverture du navigateur.
  start "" http://127.0.0.1:8000
  exit /b 0
)

if not exist "data\processed\quran.db" (
  echo Premiere utilisation : construction de la base, environ une minute...
  uv run python -m quran_harness build
  if errorlevel 1 goto erreur
)

echo.
echo Interface : http://127.0.0.1:8000
echo Laisser cette fenetre ouverte. La fermer arrete l'interface.
echo.
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000"
uv run python -m quran_harness web
if errorlevel 1 goto erreur
exit /b 0

:erreur
echo.
echo Une erreur est survenue. Voir le message ci-dessus.
pause
exit /b 1
