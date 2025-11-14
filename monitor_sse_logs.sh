#!/bin/bash
# Monitor SSE streaming logs to verify keepalive fix

echo "=== Monitoring SSE Streaming Logs ==="
echo "Watching for:"
echo "  1. HTTP 200 OK timestamp"
echo "  2. 'DIAGNOSTIC_starting_buffered_streaming_loop' timestamp"  # pragma: allowlist secret
echo "  3. Time difference (should be < 5 seconds with fix)"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo "=========================================="
echo ""

docker-compose logs -f --tail=0 app 2>&1 | grep --line-buffered -E "(POST /api/v1/chatbot/chat/stream|DIAGNOSTIC_starting_buffered_streaming_loop|yielding_chunk)"
