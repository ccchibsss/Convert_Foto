@echo off
setlocal
REM Usage: run.bat <input_dir> <runs_dir> [debug]
set INPUT=%1
set RUNS=%2
set DEBUG=%3
if "%INPUT%"=="" (
  echo Usage: run.bat ^<input_dir^> ^<runs_dir^> [debug 0/1]
  exit /b 1
)
if "%RUNS%"=="" (
  echo Usage: run.bat ^<input_dir^> ^<runs_dir^> [debug 0/1]
  exit /b 1
)
if "%DEBUG%"=="" set DEBUG=0
python -m wmr.cli run --input "%INPUT%" --runs_dir "%RUNS%" --workers 4 --debug %DEBUG%
