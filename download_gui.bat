@echo off
REM Download Tuw

REM Version info
set TUW_VERSION=v0.6.4

REM Delete ./python if exist
if exist Tuw.exe del Tuw.exe

REM Download embeddable python
curl -OL https://github.com/matyalatte/tuw/releases/download/%TUW_VERSION%/Tuw-%TUW_VERSION%-Windows-x64-ucrt.zip
powershell Expand-Archive -Force -Path Tuw-%TUW_VERSION%-Windows-x64-ucrt.zip
del Tuw-%TUW_VERSION%-Windows-x64-ucrt.zip
cd Tuw-%TUW_VERSION%-Windows-x64-ucrt
move Tuw.exe ..

cd ..
rmdir /s /q Tuw-%TUW_VERSION%-Windows-x64-ucrt

pause
