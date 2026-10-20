@echo off
rem Demarre l'interface web Coran++ sans ouvrir le navigateur.
rem Utilise par le demarrage automatique. Fermer la fenetre arrete l'interface.
cd /d "%~dp0"

rem Trouver uv : dans le PATH, sinon aux emplacements ou l'installent winget et l'installeur officiel.
rem (L'Explorateur Windows ne connait pas toujours le PATH mis a jour apres l'installation.)
set "UV="
where uv >nul 2>nul && set "UV=uv"
if not defined UV if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe" set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe"
if not defined UV if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV=%USERPROFILE%\.cargo\bin\uv.exe"
if not defined UV (
  echo uv est introuvable. Installer uv : https://docs.astral.sh/uv/
  pause
  exit /b 1
)

rem Si l'interface tourne deja, il n'y a rien a faire.
curl -s -o NUL http://127.0.0.1:8000/api/meta
if not errorlevel 1 exit /b 0

title Coran++ - interface web (fermer pour arreter)
"%UV%" run python -m quran_harness web
if errorlevel 1 pause
