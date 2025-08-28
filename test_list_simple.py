import sys
sys.path.append('/Users/micky/PycharmProjects/PratikoAi-BE')

from app.core.content_formatter import ContentFormatter

def test_simple_list():
    formatter = ContentFormatter()
    
    markdown_input = """- Item 1
- Item 2
- Item 3"""
    
    result = formatter.convert_markdown_to_html(markdown_input)
    print(f"Input: {markdown_input}")
    print(f"Result: {result}")
    
    # Check for proper list structure
    assert "<ul>" in result
    assert "<li>Item 1</li>" in result
    assert "<li>Item 2</li>" in result  
    assert "<li>Item 3</li>" in result
    assert "</ul>" in result
    
    print("✅ Simple list test passed!")

if __name__ == "__main__":
    test_simple_list()