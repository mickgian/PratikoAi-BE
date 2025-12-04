#!/usr/bin/env python3
"""Test script to verify October 2025 documents appear with correct publication dates.
Tests the complete flow: authentication -> create session -> query -> check dates in response.
"""

import asyncio
import json
from datetime import datetime

import httpx

API_BASE = "http://localhost:8000/api/v1"
TEST_USER = "rss_test@pratiko.ai"
TEST_PASSWORD = "TestPass123!"  # pragma: allowlist secret


async def test_october_query():
    """Test query for October 2025 documents."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("🔐 Authenticating...")

        # Login
        login_response = await client.post(
            f"{API_BASE}/auth/login", data={"username": TEST_USER, "password": TEST_PASSWORD}
        )

        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return

        auth_data = login_response.json()
        token = auth_data.get("access_token")
        print(f"✅ Authenticated as {TEST_USER}")

        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        print("\n📝 Creating chat session...")
        session_response = await client.post(
            f"{API_BASE}/auth/session", headers=headers, json={"title": "Test October 2025 Documents"}
        )

        if session_response.status_code not in [200, 201]:
            print(f"❌ Session creation failed: {session_response.status_code}")
            print(f"Response: {session_response.text}")
            return

        session_data = session_response.json()
        session_id = session_data.get("session_id") or session_data.get("id")
        session_token = session_data.get("token", {}).get("access_token")
        print(f"✅ Created session: {session_id}")

        # Use session token for chat requests
        session_headers = {"Authorization": f"Bearer {session_token}"}

        # Send query for October 2025 documents
        print("\n💬 Sending query: 'Quali sono i documenti normativi pubblicati a ottobre 2025?'")
        query_start = datetime.now()

        query_response = await client.post(
            f"{API_BASE}/chatbot/chat/stream",
            headers=session_headers,
            json={
                "messages": [
                    {"role": "user", "content": "Quali sono i documenti normativi pubblicati a ottobre 2025?"}
                ]
            },
        )

        if query_response.status_code != 200:
            print(f"❌ Query failed: {query_response.status_code}")
            print(f"Response: {query_response.text}")
            return

        # Handle streaming response
        response_text = ""
        trace_id = None

        for line in query_response.text.split("\n"):
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str and data_str != "[DONE]":
                    try:
                        data = json.loads(data_str)
                        # StreamResponse format: {"content": "text", "done": false}
                        content = data.get("content", "")
                        if content:
                            response_text += content
                            print(content, end="", flush=True)
                        # Check if this is the done event
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        pass

        query_duration = (datetime.now() - query_start).total_seconds()

        print(f"\n\n✅ Query completed in {query_duration:.2f}s")

        # Check for publication dates in response
        response_lower = response_text.lower()

        print("\n📊 Analysis:")
        print(f"   Response length: {len(response_text)} chars")

        # Check for October dates
        october_indicators = ["ottobre 2025", "30 ottobre", "29 ottobre", "14 ottobre", "12 ottobre"]
        found_dates = [ind for ind in october_indicators if ind in response_lower]

        if found_dates:
            print(f"   ✅ Found October dates: {', '.join(found_dates)}")
        else:
            print("   ⚠️  No October 2025 dates found in response")

        # Check for expected documents
        expected_docs = ["attuazione", "plusvalenza", "articolo 1, commi 74"]
        found_docs = [doc for doc in expected_docs if doc in response_lower]

        if found_docs:
            print(f"   ✅ Found expected documents: {', '.join(found_docs)}")
        else:
            print("   ⚠️  Expected documents not found")

        if trace_id:
            print(f"\n📋 Trace ID: {trace_id}")
            print("   Check logs at: /Users/micky/PycharmProjects/PratikoAi-BE/logs/rag_traces/")

        return trace_id, response_text


if __name__ == "__main__":
    try:
        trace_id, response = asyncio.run(test_october_query())
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
