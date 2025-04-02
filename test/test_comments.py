#!/usr/bin/env python3
# test_comments.py - Test HTML comment handling

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add parent directory to path
from url import URL
from browser import Browser
import tkinter

# Test function to print tokens from the HTML lexer
def test_lexer():
    from layout import lex
    
    # Test cases for comment handling
    test_cases = [
        "This is text <!-- This is a comment --> More text",
        "<!-- Comment with <tags> inside -->",
        "<!--> Weird comment test -->",
        "<!-- Comment \n spanning \n multiple lines -->",
        "<!----> Empty comment",
        "Text before <!-- comment --> text after"
    ]
    
    print("=== Testing HTML Lexer Comment Handling ===")
    for i, test in enumerate(test_cases):
        print(f"\nTest {i+1}: {test!r}")
        tokens = lex(test)
        print("Tokens:")
        for token in tokens:
            if isinstance(token, layout.Text):
                print(f"TEXT: {token.text!r}")
            else:
                print(f"TAG: {token.text!r}")
    
    print("\n=== End of Lexer Tests ===\n")

if __name__ == '__main__':
    # First run lexer tests
    from layout import lex, Text, Tag
    import layout
    test_lexer()
    
    # Then load the test HTML file in the browser
    if len(sys.argv) > 1:
        url_str = sys.argv[1]
    else:
        # Get the absolute path to the test file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_file = os.path.join(current_dir, "test_comments.html")
        url_str = f"file://{test_file}"
    
    print(f"Loading {url_str} in browser...")
    Browser().load(URL(url_str))
    tkinter.mainloop() 