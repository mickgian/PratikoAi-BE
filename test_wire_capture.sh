#!/bin/bash
# Wire capture test script for SSE streaming

set -e

echo "Starting wire capture test..."

# Create session ID
SESSION_ID="debug-$(date +%s)"
echo "Using session ID: $SESSION_ID"

# Create a simple test message for streaming
TEST_MESSAGE='{"messages": [{"role": "user", "content": "Explain the Italian tax regime. Include specific sections: 1. Definizione/Concetto principale, 2. Normativa di riferimento, 3. Details about calculations."}]}'

# Test the streaming endpoint with curl
echo "Capturing SSE stream..."
curl -N -H "Accept: text/event-stream" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer fake-token-for-test" \
     -X POST \
     -d "$TEST_MESSAGE" \
     "http://localhost:8000/api/v1/chatbot/chat/stream" | tee /tmp/stream.log || true

echo -e "\n\nProcessing captured stream..."

# Extract ordered payloads
echo "Extracting frames..."
nl -ba /tmp/stream.log | sed -n 's/^ *[0-9]\+\tdata: //p' > /tmp/frames.jsonl

if [ -s /tmp/frames.jsonl ]; then
    echo "Extracted $(wc -l < /tmp/frames.jsonl) frames"
    
    # Show sequence numbers and checksums
    echo -e "\nSequence analysis (first 20 frames):"
    jq -r '[.seq, .done, .sha1, (.content|tostring|.[0:60])] | @tsv' /tmp/frames.jsonl | head -20 | nl -ba
    
    # Save concatenated HTML
    echo -e "\nExtracting HTML content..."
    jq -r '.content // empty' /tmp/frames.jsonl > /tmp/stream.contents.html
    
    # Check for duplicate markers
    echo -e "\nChecking for duplicate content markers:"
    grep -n "Definizione\|Concetto principale" /tmp/stream.contents.html || echo "No 'Definizione/Concetto principale' found"
    grep -n "Normativa di riferimento" /tmp/stream.contents.html || echo "No 'Normativa di riferimento' found"
    
    echo -e "\nFirst few lines of combined HTML:"
    head -10 /tmp/stream.contents.html || echo "No HTML content found"
    
    echo -e "\nLast few lines of combined HTML:"
    tail -10 /tmp/stream.contents.html || echo "No HTML content found"
else
    echo "No frames captured - check the streaming endpoint"
fi

echo -e "\nRaw stream log (first 50 lines):"
head -50 /tmp/stream.log || echo "No stream log found"

echo -e "\nTest completed. Check /tmp/stream.log and /tmp/frames.jsonl for details"