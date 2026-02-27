@echo off
setlocal enabledelayedexpansion
set "uri=%~1"
set "path=!uri:openfolder://=!"

REM Re-insert colon after drive letter (browser strips D: to D)
set "drive=!path:~0,1!"
set "rest=!path:~1!"
set "path=!drive!:!rest!"

REM Convert forward slashes to backslashes
set "path=!path:/=\!"

REM Decode percent-encoded spaces
set "path=!path:%%20= !"

%SystemRoot%\explorer.exe "!path!"
endlocal
