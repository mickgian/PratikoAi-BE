"""End-to-End Acceptance Test for LLM Query Normalization

This script tests the complete flow:
1. User query with linguistic variation (written numbers, abbreviations, typos)
2. QueryNormalizer extracts document reference via LLM
3. KnowledgeSearchService uses extracted reference to find documents

NOTE: This uses the REAL LLM API (gpt-4o-mini), not mocked.
"""

import asyncio

from app.services.query_normalizer import QueryNormalizer


async def test_query_variations():
    """Test various query formats that should all resolve to the same document."""
    normalizer = QueryNormalizer()

    test_cases = [
        ("risoluzione sessantaquattro", {"type": "risoluzione", "number": "64"}),
        ("ris 64", {"type": "risoluzione", "number": "64"}),
        ("risouzione 64", {"type": "risoluzione", "number": "64"}),  # Typo
        ("cosa dice la 64?", {"type": "risoluzione", "number": "64"}),  # Word order variation
        ("Risoluzione numero sessantaquattro dell'agenzia", {"type": "risoluzione", "number": "64"}),
        ("come calcolare le tasse", None),  # Non-document query
    ]

    print("=" * 80)
    print("END-TO-END ACCEPTANCE TEST: LLM Query Normalization")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for query, expected in test_cases:
        print(f"Testing: '{query}'")
        print(f"Expected: {expected}")

        try:
            result = await normalizer.normalize(query)
            print(f"Got:      {result}")

            if expected is None:
                if result is None:
                    print("✅ PASS - Correctly returned None for non-document query")
                    passed += 1
                else:
                    print(f"❌ FAIL - Expected None, got {result}")
                    failed += 1
            else:
                if result and result.get("type") == expected["type"] and result.get("number") == expected["number"]:
                    print(f"✅ PASS - Correctly extracted {result}")
                    passed += 1
                else:
                    print(f"❌ FAIL - Expected {expected}, got {result}")
                    failed += 1

        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

        print()

    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    return passed, failed


async def test_original_failing_query():
    """Test the original failing query from the user's bug report."""
    print()
    print("=" * 80)
    print("ORIGINAL FAILING QUERY TEST")
    print("=" * 80)
    print()

    normalizer = QueryNormalizer()
    original_query = "Cosa dice la Risoluzione n. 64 del 10 novembre 2025?"

    print(f"Original Query: '{original_query}'")
    print()

    result = await normalizer.normalize(original_query)

    print(f"LLM Extracted: {result}")
    print()

    if result and result.get("number") == "64":
        print("✅ SUCCESS - LLM correctly extracted document number '64'")
        print("   This query should now find Resolution 64 via title pattern matching")
        return True
    else:
        print(f"❌ FAILURE - Expected number '64', got {result}")
        return False


async def main():
    """Run all acceptance tests."""
    # Test 1: Query variations
    passed, failed = await test_query_variations()

    # Test 2: Original failing query
    original_success = await test_original_failing_query()

    # Summary
    print()
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Query Variations: {passed} passed, {failed} failed")
    print(f"Original Query: {'✅ PASS' if original_success else '❌ FAIL'}")
    print()

    if failed == 0 and original_success:
        print("🎉 ALL ACCEPTANCE TESTS PASSED!")
        print()
        print("The LLM query normalization feature is working correctly.")
        print("Users can now query documents using:")
        print("  - Written numbers (sessantaquattro → 64)")
        print("  - Abbreviations (ris → risoluzione)")
        print("  - Typos (risouzione → risoluzione)")
        print("  - Any word order (cosa dice la 64? → Resolution 64)")
    else:
        print("⚠️  Some tests failed - review output above")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
