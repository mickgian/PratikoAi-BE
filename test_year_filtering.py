"""Test year-based filtering in search."""

import asyncio

import httpx


async def test_year_filtering():
    """Test search with year in query."""
    # Test query with year
    query = "fammi un riassunto di tutte le risoluzioni dell'agenzia delle entrate di ottobre e novembre 2025"

    print(f"\n🔍 Testing query: {query}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/api/v1/chat",
            json={"message": query, "conversation_id": "test-year-filtering", "user_id": "test-user"},
        )

        if response.status_code == 200:
            result = response.json()
            content = result.get("response", result.get("answer", result.get("message", "")))

            print("✅ Response received:\n")
            print(content)
            print("\n" + "=" * 80)

            # Check if we got all 5 risoluzioni
            risoluzioni = ["56", "62", "63", "64", "65"]
            found = []
            missing = []

            for num in risoluzioni:
                if num in content:
                    found.append(num)
                else:
                    missing.append(num)

            print(f"\n📊 Found risoluzioni: {found}")
            if missing:
                print(f"⚠️  Missing risoluzioni: {missing}")
            else:
                print("✅ All 5 risoluzioni found!")

        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)


if __name__ == "__main__":
    asyncio.run(test_year_filtering())
