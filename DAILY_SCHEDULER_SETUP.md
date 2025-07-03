# Daily Scheduler Setup Guide

This guide explains how to set up and use the daily scheduler files to run tasks at 3:00 AM every day.

## Files Created

1. **`daily_scheduler.py`** - Python scheduler that runs continuously
2. **`daily_task_runner.py`** - Single execution script with your task logic
3. **`run_daily_task.bat`** - Windows batch file for Task Scheduler
4. **Updated `requirements.txt`** - Added the `schedule` library

## Setup Options

### Option 1: Python Continuous Scheduler (Recommended for Development)

1. Install the new dependency:
   ```bash
   pip install -r requirements.txt
   ```

2. Customize the `daily_task()` function in `daily_scheduler.py` with your actual logic

3. Run the scheduler:
   ```bash
   python daily_scheduler.py
   ```

The script will run continuously and execute your task every day at 3:00 AM.

### Option 2: Windows Task Scheduler (Recommended for Production)

1. Customize the `execute_daily_task()` function in `daily_task_runner.py`

2. Open Windows Task Scheduler (`taskschd.msc`)

3. Create a new basic task:
   - **Name**: Daily Task Runner
   - **Trigger**: Daily at 3:00 AM
   - **Action**: Start a program
   - **Program**: Path to `run_daily_task.bat`
   - **Start in**: Your project directory

4. Test the task by running it manually first

## Customization

### Adding Your Task Logic

Replace the placeholder comments in either file with your actual business logic:

```python
# Example customizations for your YouTube fact-checker API:
def execute_daily_task():
    # Clean up old fact-check results
    cleanup_old_results()
    
    # Update daily statistics
    update_analytics()
    
    # Generate usage reports
    generate_daily_report()
    
    # Refresh cached data
    refresh_cache()
```

### Logging

Both scripts include comprehensive logging:
- Console output for monitoring
- Log files for debugging (`daily_scheduler.log`, `daily_task_runner.log`)

## Testing

Test your scheduler before deploying:

```bash
# Test the single execution script
python daily_task_runner.py

# Test the continuous scheduler (stop with Ctrl+C)
python daily_scheduler.py
```

## Production Considerations

- Use Windows Task Scheduler for production reliability
- Set up monitoring and alerts for task failures
- Consider running as a Windows Service for 24/7 operation
- Implement proper error handling and notifications
- Set up log rotation to prevent disk space issues

## Troubleshooting

- Check log files for error details
- Ensure Python virtual environment is properly activated
- Verify file permissions and paths
- Test scripts manually before scheduling 