@echo off

set base=localizations\localization_all.
set ext=.localization
set eng_json=%base%0%ext%.json

@pushd %~dp0

rem Merge localization_all.0.localization into
rem localization_all.24.localization, localization_all.32.localization, ..., localization_all.248.localization

python\python.exe src\main.py %base%0%ext% --mode=extract
for /l %%x in (24, 8, 248) do (
    python\python.exe src\main.py %base%%%x%ext% --mode=extract
    python\python.exe src\main.py %base%%%x%ext%.json %eng_json% --mode=merge
    python\python.exe src\main.py %base%%%x%ext% %base%%%x%ext%.new.json --mode=inject
)
@popd

pause

