@echo off
rem Lance l'interface web Coran++ et l'ouvre dans le navigateur.
rem Double-cliquer sur ce fichier depuis l'Explorateur Windows.
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

rem Si l'interface tourne deja, on ouvre seulement le navigateur.
curl -s -o NUL http://127.0.0.1:8000/api/meta
if not errorlevel 1 (
  echo L'interface tourne deja : ouverture du navigateur.
  start "" http://127.0.0.1:8000
  exit /b 0
)

if not exist "data\processed\quran.db" (
  echo Premiere utilisation : construction de la base, quelques minutes...
  "%UV%" run python -m quran_harness build
  if errorlevel 1 goto erreur
)

title Coran++ - interface web (fermer cette fenetre arrete l'interface)
echo.
echo Interface : http://127.0.0.1:8000
echo Laisser cette fenetre ouverte. La fermer arrete l'interface.
echo.
start "" cmd /c "timeout /t 5 >nul & start http://127.0.0.1:8000"
"%UV%" run python -m quran_harness web
if errorlevel 1 goto erreur
exit /b 0

:erreur
echo.
echo Une erreur est survenue. Voir le message ci-dessus.
pause
exit /b 1
