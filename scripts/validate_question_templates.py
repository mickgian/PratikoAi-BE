#!/usr/bin/env python3
"""
Validation script for Interactive Question Templates.
DEV-153: Create Interactive Question Templates YAML

This script validates:
1. All leads_to references point to existing question IDs
2. All questions have an "altro" option
3. Multi-step flows are properly connected
"""

from pathlib import Path

import yaml  # type: ignore[import-untyped]


def validate_templates():
    """Validate all question templates."""
    template_dir = Path("app/core/templates/interactive_questions")

    # Collect all question IDs and leads_to references
    all_question_ids: set[str] = set()
    all_leads_to: list[dict] = []
    questions_without_altro: list[str] = []
    validation_errors: list[str] = []

    for yaml_file in template_dir.glob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        if not data or "questions" not in data:
            validation_errors.append(f"{yaml_file.name}: No 'questions' key found")
            continue

        for q_id, question in data["questions"].items():
            all_question_ids.add(q_id)

            # Check for 'altro' option
            options = question.get("options", [])
            has_altro = any(opt.get("id") == "altro" for opt in options)
            if not has_altro:
                questions_without_altro.append(f"{yaml_file.name}: {q_id}")

            # Collect leads_to references
            for opt in options:
                if "leads_to" in opt:
                    all_leads_to.append(
                        {
                            "file": yaml_file.name,
                            "question": q_id,
                            "option": opt.get("id"),
                            "leads_to": opt["leads_to"],
                        }
                    )

    # Check for orphan leads_to references
    orphan_references = []
    for ref in all_leads_to:
        if ref["leads_to"] not in all_question_ids:
            orphan_references.append(ref)

    # Print results
    print("=" * 60)
    print("TEMPLATE VALIDATION REPORT")
    print("=" * 60)

    print(f"\nTotal questions found: {len(all_question_ids)}")
    print(f"Total leads_to references: {len(all_leads_to)}")

    if questions_without_altro:
        print(f"\n❌ Questions WITHOUT 'altro' option ({len(questions_without_altro)}):")
        for q in questions_without_altro:
            print(f"   - {q}")
    else:
        print("\n✅ All questions have 'altro' option")

    if orphan_references:
        print(f"\n❌ Orphan leads_to references ({len(orphan_references)}):")
        for ref in orphan_references:
            print(
                f"   - {ref['file']}: {ref['question']} -> option '{ref['option']}' "
                f"leads to '{ref['leads_to']}' (NOT FOUND)"
            )
    else:
        print("\n✅ All leads_to references are valid")

    if validation_errors:
        print(f"\n❌ Validation errors ({len(validation_errors)}):")
        for err in validation_errors:
            print(f"   - {err}")
    else:
        print("\n✅ No validation errors")

    print("\n" + "=" * 60)
    if not questions_without_altro and not orphan_references and not validation_errors:
        print("VALIDATION PASSED ✅")
        return True
    else:
        print("VALIDATION FAILED ❌")
        return False


if __name__ == "__main__":
    import sys

    success = validate_templates()
    sys.exit(0 if success else 1)
