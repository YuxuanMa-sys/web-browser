#!/usr/bin/env python3
# test_edge_comment.py - Test HTML comment edge cases

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add parent directory to path
from layout import lex, Text, Tag
import layout

def test_edge_cases():
    # Test cases for the <!--> edge case
    test_cases = [
        "<!--> This isn't a valid HTML comment according to spec, but many browsers treat it as a comment",
        "Text1<!--> -->Text2",  # Incomplete comment followed by comment terminator
        "Text3<!-->Text4",      # Another variant
        "<p>Text<!--> Comment test</p>",
    ]
    
    print("=== Testing HTML Comment Edge Cases ===")
    for i, test in enumerate(test_cases):
        print(f"\nEdge Case {i+1}: {test!r}")
        tokens = lex(test)
        print("Tokens:")
        for token in tokens:
            if isinstance(token, Text):
                print(f"TEXT: {token.text!r}")
            else:
                print(f"TAG: {token.text!r}")
    
    # Now let's test how actual browsers handle this
    print("\n=== According to HTML spec and browser implementations ===")
    print("In modern browsers, <!--> is treated as a comment opening followed by '>'")
    print("Browsers interpret this as a comment until they find the next '-->', if any")
    
    # Also test our HTML parser directly
    from html_parser import HTMLParser
    print("\n=== Testing with our HTML Parser ===")
    for i, test in enumerate(test_cases):
        print(f"\nParser Test {i+1}: {test!r}")
        root = HTMLParser(test).parse()
        print_tree(root)

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

if __name__ == '__main__':
    test_edge_cases()
    
    # Optionally load the test file in the browser if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--browser':
        from url import URL
        from browser import Browser
        import tkinter
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_file = os.path.join(current_dir, "test_edge_comment.html")
        url_str = f"file://{test_file}"
        
        print(f"\nLoading {url_str} in browser...")
        Browser().load(URL(url_str))
        tkinter.mainloop() 