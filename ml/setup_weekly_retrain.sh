#!/bin/bash
# Setup weekly retraining automation

SCRIPT_PATH="/tmp/retrain_model.sh"
LOG_PATH="/tmp/model_retrain.log"

echo "Setting up weekly model retraining..."

# Create cron job to run every Sunday at 8 AM
CRON_JOB="0 8 * * 0 $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "Cron job already exists"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✓ Cron job added: Every Sunday at 8 AM"
fi

echo ""
echo "Weekly retraining is now automated!"
echo "  Schedule: Every Sunday at 8:00 AM"
echo "  Script: $SCRIPT_PATH"
echo "  Logs: $LOG_PATH"
echo ""
echo "To manually run: $SCRIPT_PATH"
echo "To view logs: tail -f $LOG_PATH"
echo "To remove: crontab -e (then delete the line)"
