@echo off
rem Demarre l'interface web sans ouvrir le navigateur.
rem Utilise par le demarrage automatique. Fermer la fenetre arrete l'interface.
cd /d "%~dp0"

rem Si l'interface tourne deja, il n'y a rien a faire.
curl -s -o NUL http://127.0.0.1:8000/api/meta
if not errorlevel 1 exit /b 0

title Correlations coraniques - interface web (fermer pour arreter)
uv run python -m quran_harness web
if errorlevel 1 pause
