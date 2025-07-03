@echo off
REM Daily Task Runner - Windows Batch File
REM This batch file can be scheduled with Windows Task Scheduler to run at 3:00 AM daily
REM 
REM To schedule this with Windows Task Scheduler:
REM 1. Open Task Scheduler (taskschd.msc)
REM 2. Create Basic Task
REM 3. Set trigger to Daily at 3:00 AM
REM 4. Set action to start this batch file
REM 5. Set the "Start in" directory to your project folder

REM Change to the directory where this script is located
cd /d "%~dp0"

REM Log the start time
echo %date% %time% - Starting daily task >> daily_task.log

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo %date% %time% - Activating virtual environment >> daily_task.log
    call venv\Scripts\activate.bat
)

REM Run your daily task Python script
echo %date% %time% - Executing daily task >> daily_task.log
python daily_task_runner.py >> daily_task.log 2>&1

REM Log completion
echo %date% %time% - Daily task completed >> daily_task.log
echo. >> daily_task.log

REM Deactivate virtual environment if it was activated
if exist "venv\Scripts\activate.bat" (
    deactivate
)

pause 