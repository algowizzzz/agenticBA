#!/bin/bash

echo "======= Document Summarization Progress ======="
echo "Last checked: $(date)"

# Get total transcripts in the database
TOTAL_TRANSCRIPTS=$(mongosh --quiet --eval "db.getSiblingDB('earnings_transcripts').transcripts.countDocuments({})")
echo "Total transcripts: $TOTAL_TRANSCRIPTS"

# Get count of all summaries
ALL_SUMMARIES=$(mongosh --quiet --eval "db.getSiblingDB('earnings_transcripts').document_summaries.countDocuments({})")
echo "Total summaries: $ALL_SUMMARIES"

# Get count of summaries with today's date
TODAY=$(date +%Y-%m-%d)
RECENT_SUMMARIES=$(mongosh --quiet --eval "db.getSiblingDB('earnings_transcripts').document_summaries.countDocuments({last_updated_utc: {\$gt: ISODate('${TODAY}T00:00:00Z')}})")
echo "Summaries generated today: $RECENT_SUMMARIES"

# Calculate percentage complete for today's progress
if [ $TOTAL_TRANSCRIPTS -gt 0 ]; then
    PERCENT_DONE=$(echo "scale=2; $RECENT_SUMMARIES * 100 / $TOTAL_TRANSCRIPTS" | bc)
    echo "Today's progress: $PERCENT_DONE% complete"
    
    # Calculate total completion percentage
    TOTAL_PERCENT=$(echo "scale=2; $ALL_SUMMARIES * 100 / $TOTAL_TRANSCRIPTS" | bc)
    echo "Overall progress: $TOTAL_PERCENT% complete"
fi

# Check if the summarizer is still running - use a more reliable pattern
if ps aux | grep "python.*generate_document_summaries.py" | grep -v grep > /dev/null; then
    echo "Status: RUNNING"
    
    # Get the process ID
    PID=$(ps aux | grep "python.*generate_document_summaries.py" | grep -v grep | awk '{print $2}')
    echo "Process ID: $PID"
    
    # Get CPU and memory usage
    if [ -n "$PID" ]; then
        CPU_USAGE=$(ps -p $PID -o %cpu | tail -n 1)
        MEM_USAGE=$(ps -p $PID -o %mem | tail -n 1)
        echo "CPU usage: $CPU_USAGE%"
        echo "Memory usage: $MEM_USAGE%"
    fi
else
    echo "Status: NOT RUNNING"
fi

# Show most recent log entries if log file exists
LATEST_LOG=$(ls -t summarizer_log_*.txt 2>/dev/null | head -1)
if [ -n "$LATEST_LOG" ]; then
    echo "Latest log: $LATEST_LOG"
    echo "Size: $(du -h $LATEST_LOG | cut -f1) bytes"
    
    # Find the most recent transcript ID being processed
    LATEST_ID=$(grep -a "Processing transcript" $LATEST_LOG | tail -1)
    if [ -n "$LATEST_ID" ]; then
        echo "Latest transcript: $LATEST_ID"
    fi
    
    # Find the most recent summary saved
    LATEST_SAVED=$(grep -a "Successfully saved summary for" $LATEST_LOG | tail -1)
    if [ -n "$LATEST_SAVED" ]; then
        echo "Latest saved: $LATEST_SAVED"
    fi
    
    echo "Last 10 log entries:"
    tail -10 "$LATEST_LOG"
fi

# Estimate completion time based on current rate
if [ $RECENT_SUMMARIES -gt 0 ]; then
    # Get earliest and latest timestamps from today's summaries
    EARLIEST=$(mongosh --quiet --eval "db.getSiblingDB('earnings_transcripts').document_summaries.find({last_updated_utc: {\$gt: ISODate('${TODAY}T00:00:00Z')}}).sort({last_updated_utc: 1}).limit(1).toArray()[0].last_updated_utc" 2>/dev/null)
    LATEST=$(mongosh --quiet --eval "db.getSiblingDB('earnings_transcripts').document_summaries.find({last_updated_utc: {\$gt: ISODate('${TODAY}T00:00:00Z')}}).sort({last_updated_utc: -1}).limit(1).toArray()[0].last_updated_utc" 2>/dev/null)
    
    if [ -n "$EARLIEST" ] && [ -n "$LATEST" ]; then
        # Convert to timestamps
        EARLIEST_TS=$(date -j -f "%Y-%m-%dT%H:%M:%S" $(echo $EARLIEST | cut -d. -f1) "+%s" 2>/dev/null)
        LATEST_TS=$(date -j -f "%Y-%m-%dT%H:%M:%S" $(echo $LATEST | cut -d. -f1) "+%s" 2>/dev/null)
        
        if [ -n "$EARLIEST_TS" ] && [ -n "$LATEST_TS" ] && [ $EARLIEST_TS -ne $LATEST_TS ]; then
            TIME_DIFF=$((LATEST_TS - EARLIEST_TS))
            DOCS_PER_SECOND=$(echo "scale=4; $RECENT_SUMMARIES / $TIME_DIFF" | bc)
            DOCS_PER_HOUR=$(echo "scale=2; $DOCS_PER_SECOND * 3600" | bc)
            REMAINING_DOCS=$((TOTAL_TRANSCRIPTS - ALL_SUMMARIES))
            
            if [ $DOCS_PER_SECOND != "0" ] && [ $REMAINING_DOCS -gt 0 ]; then
                SECONDS_REMAINING=$(echo "scale=0; $REMAINING_DOCS / $DOCS_PER_SECOND" | bc)
                HOURS=$((SECONDS_REMAINING / 3600))
                MINUTES=$(((SECONDS_REMAINING % 3600) / 60))
                
                echo "Current rate: ~$DOCS_PER_HOUR summaries per hour"
                echo "Estimated time remaining: ~${HOURS}h ${MINUTES}m"
                echo "Estimated completion: $(date -v+${SECONDS_REMAINING}S "+%Y-%m-%d %H:%M:%S")"
            fi
        fi
    fi
fi

echo "==============================================" 