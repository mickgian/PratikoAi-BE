#!/usr/bin/env python3
"""Test script to verify Risoluzione 56 query works end-to-end.
Tests the complete flow: authentication -> create session -> query -> check results.
"""

import asyncio
import json
from datetime import datetime

import httpx

API_BASE = "http://localhost:8000/api/v1"
TEST_USER = "rss_test@pratiko.ai"
TEST_PASSWORD = "TestPass123!"  # pragma: allowlist secret


async def test_risoluzione_query():
    """Test the complete flow for Risoluzione 56 query."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🔐 Authenticating...")

        # Login (using form data, not JSON)
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
            f"{API_BASE}/auth/session", headers=headers, json={"title": "Test Risoluzione 56"}
        )

        if session_response.status_code not in [200, 201]:
            print(f"❌ Session creation failed: {session_response.status_code}")
            print(f"Response: {session_response.text}")
            return

        session_data = session_response.json()
        session_id = session_data.get("session_id") or session_data.get("id")
        session_token = session_data.get("token", {}).get("access_token")
        print(f"✅ Created session: {session_id}")

        # Use session token for chat requests (not user token)
        session_headers = {"Authorization": f"Bearer {session_token}"}

        # Send query
        print("\n💬 Sending query: 'Cosa dice la risoluzione numero 56?'")
        query_start = datetime.now()

        query_response = await client.post(
            f"{API_BASE}/chatbot/chat/stream",
            headers=session_headers,
            json={"messages": [{"role": "user", "content": "Cosa dice la risoluzione numero 56?"}]},
        )

        if query_response.status_code != 200:
            print(f"❌ Query failed: {query_response.status_code}")
            print(f"Response: {query_response.text}")
            return

        # Handle streaming response (SSE)
        response_text = ""
        trace_id = None

        # Read the streaming response
        for line in query_response.text.split("\n"):
            if line.startswith("data: "):
                data_str = line[6:]  # Remove 'data: ' prefix
                if data_str and data_str != "[DONE]":
                    try:
                        data = json.loads(data_str)
                        if data.get("event") == "content":
                            content = data.get("data", {}).get("content", "")
                            response_text += content
                        elif data.get("event") == "trace":
                            trace_id = data.get("data", {}).get("trace_id")
                    except json.JSONDecodeError:
                        pass

        query_duration = (datetime.now() - query_start).total_seconds()

        print(f"\n✅ Query completed in {query_duration:.2f}s")
        print("\n📊 Response preview:")
        print(f"   {response_text[:300]}...")

        # Check if response mentions Risoluzione 56 content
        response_lower = response_text.lower()
        if "risoluzione" in response_lower or "tardiva registrazione" in response_lower:
            print("\n✅ Response contains relevant content!")
        else:
            print("\n⚠️  Response might be generic (check trace logs)")

        # Get trace ID for log analysis
        if trace_id:
            print(f"\n📋 Trace ID: {trace_id}")
            print("   Check logs at: /Users/micky/PycharmProjects/PratikoAi-BE/logs/rag_traces/")

        return trace_id


if __name__ == "__main__":
    try:
        trace_id = asyncio.run(test_risoluzione_query())
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
