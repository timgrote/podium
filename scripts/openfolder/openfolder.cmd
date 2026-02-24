@echo off
setlocal enabledelayedexpansion
set "uri=%~1"
echo RAW URI: !uri!

set "path=!uri:openfolder://=!"
echo AFTER STRIP PREFIX: !path!

REM Re-insert colon after drive letter (browser strips D: to D)
set "drive=!path:~0,1!"
set "rest=!path:~1!"
set "path=!drive!:!rest!"
echo AFTER DRIVE FIX: !path!

REM Convert forward slashes to backslashes
set "path=!path:/=\!"
echo AFTER SLASH FIX: !path!

REM Decode percent-encoded spaces
set "path=!path:%%20= !"
echo FINAL PATH: !path!

%SystemRoot%\explorer.exe "!path!"
pause
endlocal
