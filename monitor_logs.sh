#!/bin/bash
# Monitor backend logs for EMIT and SOCKET_WRITE messages

echo "Monitoring backend logs for streaming instrumentation..."
echo "Look for lines containing EMIT or SOCKET_WRITE"
echo "Press Ctrl+C to stop"

docker logs -f pratikoai-be-app-1 2>&1 | grep -E "(EMIT|SOCKET_WRITE|stream_id|Second-start|duplicate)" --line-buffered