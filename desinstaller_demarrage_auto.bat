@echo off
rem Annule le demarrage automatique de l'interface web.
powershell -NoProfile -Command "$p = [Environment]::GetFolderPath('Startup') + '\Correlations coraniques.lnk'; if (Test-Path $p) { Remove-Item $p; 'Demarrage automatique retire.' } else { 'Aucun demarrage automatique installe.' }"
echo L'interface deja en marche continue jusqu'a la fermeture de sa fenetre.
pause
