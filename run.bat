@echo off
REM Land Scout Lite - one click weekly run
SETLOCAL
IF NOT EXIST .venv (
  py -3 -m venv .venv
)
CALL .venv\Scripts\activate.bat
python -m pip install -U pip
python -m pip install -e .[dev]

REM Create defaults if missing
IF NOT EXIST examples mkdir examples
IF NOT EXIST examples\config.example.yaml (
  >examples\config.example.yaml (
    echo scoring:
    echo   default_thresholds: [1000, 4000, 8000]
    echo   thresholds_by_county:
    echo     peoria:   [1200, 4500, 9000]
    echo     knox:     [1000, 4000, 8000]
    echo     woodford: [1500, 5000, 10000]
    echo     chicago:  [5000, 15000, 40000]
    echo     tazewell: [1300, 4500, 9000]
    echo     henry:    [1100, 4200, 8500]
    echo     canton:   [1100, 4200, 8500]
  )
)

IF "%~1"=="" (
  echo Usage: run.bat ^<input_csv^> [counties] [topN]
  echo Example: run.bat data\your_weekly_listings.csv "Peoria,Knox" 10
  EXIT /B 1
)

SET INPUT=%~1
SET COUNTIES=%~2
IF "%COUNTIES%"=="" SET COUNTIES=Peoria,Knox,Woodford
SET TOP=%~3
IF "%TOP%"=="" SET TOP=20

python -m land_scout.cli ^
  --input "%INPUT%" ^
  --config examples\config.example.yaml ^
  --counties "%COUNTIES%" ^
  --top %TOP% ^
  --out out\weekly.csv ^
  --report out\week.md

echo Done. Outputs in out\weekly.csv and out\week.md
ENDLOCAL
