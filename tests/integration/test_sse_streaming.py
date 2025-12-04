"""Test SSE streaming endpoint to verify keepalive fix."""

import asyncio
import time

import httpx


async def test_sse_streaming():
    """Test that SSE chunks arrive in real-time without page refresh."""
    print("\n=== Testing SSE Streaming Endpoint ===")
    print("Testing for immediate chunk delivery (keepalive fix)\n")

    url = "http://localhost:8000/api/v1/chatbot/chat/stream"
    payload = {"messages": [{"role": "user", "content": "Cosa sono le detrazioni fiscali per ottobre 2025?"}]}

    start_time = time.time()
    first_chunk_time = None
    chunk_count = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        print(f"[{time.time() - start_time:.2f}s] Sending request...")

        async with client.stream("POST", url, json=payload) as response:
            connection_time = time.time() - start_time
            print(f"[{connection_time:.2f}s] Connection established (HTTP {response.status_code})")
            print("Waiting for chunks...\n")

            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                if line.startswith("data: "):
                    chunk_count += 1
                    elapsed = time.time() - start_time

                    if first_chunk_time is None:
                        first_chunk_time = elapsed
                        print(f"✅ [CRITICAL] First chunk received at {first_chunk_time:.2f}s after request")
                        print(f"   Time from connection: {first_chunk_time - connection_time:.2f}s\n")

                    # Only print first few chunks
                    if chunk_count <= 3:
                        data = line[6:] if len(line) > 6 else ""
                        preview = data[:100] if data else ""
                        print(f"[{elapsed:.2f}s] Chunk {chunk_count}: {preview}...")

                    # Stop after 5 chunks or if done
                    if chunk_count >= 5 or '"done":true' in line:
                        print(f"\n[{elapsed:.2f}s] Stopping after {chunk_count} chunks")
                        break

    print("\n=== Test Results ===")
    if first_chunk_time:
        print("✅ SSE streaming is WORKING")
        print(f"   - First chunk arrived: {first_chunk_time:.2f}s after request")
        print(f"   - Total chunks received: {chunk_count}")

        if first_chunk_time < 2.0:
            print("   - ✅ EXCELLENT: Chunks arrived immediately (< 2s)")
        elif first_chunk_time < 5.0:
            print("   - ✅ GOOD: Chunks arrived quickly (< 5s)")
        elif first_chunk_time < 30.0:
            print(f"   - ⚠️  WARNING: Chunks arrived slowly ({first_chunk_time:.2f}s)")
        else:
            print(f"   - ❌ FAILED: Chunks arrived too late ({first_chunk_time:.2f}s)")
            print(f"   - Expected < 5s, got {first_chunk_time:.2f}s")
    else:
        print("❌ SSE streaming FAILED - No chunks received")


if __name__ == "__main__":
    asyncio.run(test_sse_streaming())
