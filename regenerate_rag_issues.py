#!/usr/bin/env python3

import json
import subprocess
import sys
import time


def run_command(command, description):
    """Run a command and return success/failure"""
    print(f"⚡ {description}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    else:
        print("✅ Success")
        return True


def main():
    print("🔄 Regenerating RAG Step Issues with Updated Investigation Data")
    print("=" * 70)

    # Step 1: Get all RAG step issue numbers
    print("\n📋 Step 1: Collecting RAG step issue numbers...")
    result = subprocess.run(
        "gh issue list --limit 1000 --json number,title | jq -r '.[] | select(.title | test(\"RAG STEP [0-9]+\")) | .number'",
        shell=True,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ Failed to get issue list: {result.stderr}")
        return False

    issue_numbers = [num.strip() for num in result.stdout.strip().split("\n") if num.strip()]
    print(f"📊 Found {len(issue_numbers)} RAG step issues to delete")

    if len(issue_numbers) == 0:
        print("⚠️  No RAG step issues found to delete")
    else:
        # Step 2: Delete all existing RAG step issues
        print(f"\n🗑️  Step 2: Deleting {len(issue_numbers)} existing RAG step issues...")

        failed_deletions = []
        for i, issue_num in enumerate(issue_numbers, 1):
            print(f"  Deleting issue #{issue_num} ({i}/{len(issue_numbers)})")
            delete_result = subprocess.run(
                f"gh issue delete {issue_num} --yes", shell=True, capture_output=True, text=True
            )

            if delete_result.returncode != 0:
                print(f"    ❌ Failed to delete #{issue_num}: {delete_result.stderr}")
                failed_deletions.append(issue_num)
            else:
                print(f"    ✅ Deleted #{issue_num}")

            # Small delay to avoid rate limiting
            time.sleep(0.1)

        if failed_deletions:
            print(f"⚠️  Failed to delete {len(failed_deletions)} issues: {failed_deletions}")
        else:
            print("✅ All existing RAG step issues deleted successfully")

    # Step 3: Wait a moment for GitHub to process deletions
    print("\n⏳ Waiting 3 seconds for GitHub to process deletions...")
    time.sleep(3)

    # Step 4: Regenerate all issues with updated content
    print("\n🚀 Step 3: Regenerating all 135 RAG step issues with updated investigation data...")

    regenerate_command = "python3 scripts/rag_issue_prompter.py"
    regenerate_result = subprocess.run(regenerate_command, shell=True, capture_output=True, text=True)

    if regenerate_result.returncode != 0:
        print(f"❌ Failed to regenerate issues: {regenerate_result.stderr}")
        print(f"📄 stdout: {regenerate_result.stdout}")
        return False

    print("✅ Issue regeneration completed")
    print(f"📄 Output: {regenerate_result.stdout}")

    # Step 5: Verify the new issues were created
    print("\n🔍 Step 4: Verifying new issues were created...")
    verify_result = subprocess.run(
        'gh issue list --limit 200 | grep -E "RAG STEP [0-9]+" | wc -l', shell=True, capture_output=True, text=True
    )

    if verify_result.returncode == 0:
        new_count = int(verify_result.stdout.strip())
        print(f"📊 Found {new_count} new RAG step issues")

        if new_count == 135:
            print("🎉 SUCCESS: All 135 RAG step issues regenerated with updated investigation data!")
        else:
            print(f"⚠️  Expected 135 issues, found {new_count}")
    else:
        print(f"❌ Failed to verify new issues: {verify_result.stderr}")

    print("\n" + "=" * 70)
    print("✅ RAG Issues Regeneration Complete!")
    print("\n💡 Next steps:")
    print("1. Check GitHub issues to verify they contain Claude Code instructions")
    print("2. Pick any issue and copy-paste the commands into Claude Code")
    print("3. Follow the TDD approach with the generated unit tests")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
