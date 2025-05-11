#!/bin/bash

# Get timestamp for log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="summarizer_log_${TIMESTAMP}.txt"

echo "Starting document summarization process at $(date)"
echo "Logs will be written to $LOG_FILE"

# Activate virtual environment and run the script
# Use script command to capture all terminal output properly
source venv/bin/activate
python3 generate_document_summaries.py 2>&1 | tee -a "$LOG_FILE"

echo "Summarization process completed at $(date)" | tee -a "$LOG_FILE"
echo "Check $LOG_FILE for details" 