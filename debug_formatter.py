import sys
sys.path.append('/Users/micky/PycharmProjects/PratikoAi-BE')

from app.core.content_formatter import ContentFormatter
import re

def debug_heading_conversion():
    formatter = ContentFormatter()
    
    markdown_input = "### 1. Definizione/Concetto principale"
    print(f"Input: '{markdown_input}'")
    
    # Test the regex pattern directly
    h3_pattern = re.compile(r'^### (.+)$', re.MULTILINE)
    match = h3_pattern.search(markdown_input)
    print(f"H3 pattern match: {match}")
    if match:
        print(f"Matched group: '{match.group(1)}'")
    
    # Test the substitution
    test_sub = h3_pattern.sub(r'<h3>\1</h3>', markdown_input)
    print(f"Direct substitution result: '{test_sub}'")
    
    # Test the full conversion
    try:
        result = formatter.convert_markdown_to_html(markdown_input)
        print(f"Full conversion result: '{result}'")
    except Exception as e:
        print(f"Error in conversion: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_heading_conversion()