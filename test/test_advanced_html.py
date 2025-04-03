#!/usr/bin/env python3
# test_advanced_html.py - Test advanced HTML features

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add parent directory to path
from html_parser import HTMLParser
from layout import lex, Text, Tag
import layout

def print_tree(node, indent=0):
    """Print the HTML tree structure."""
    print(" " * indent + str(node))
    for child in node.children:
        print_tree(child, indent + 2)

def test_script_handling():
    """Test how script tags are handled."""
    print("\n=== Testing Script Tag Handling ===")
    
    # Test case: Simple JavaScript with angle brackets
    script_html = "<script>let x = 10; if (x < 20) { console.log('x is less than 20'); }</script>"
    print("\nTest Case: Script with angle brackets")
    tokens = lex(script_html)
    print("Tokens:")
    for token in tokens:
        if isinstance(token, Text):
            print(f"TEXT: {token.text!r}")
        else:
            print(f"TAG: {token.text!r}")
    
    # Test case: Script with HTML-like content that should be treated as text
    script_html = "<script>let html = '<div>This looks like HTML</div>';</script>"
    print("\nTest Case: Script with HTML-like content")
    tokens = lex(script_html)
    print("Tokens:")
    for token in tokens:
        if isinstance(token, Text):
            print(f"TEXT: {token.text!r}")
        else:
            print(f"TAG: {token.text!r}")
    
    # Test case: Script with tag-like content
    script_html = "<script>// This </script is not a closing tag</script>"
    print("\nTest Case: Script with tag-like content")
    tokens = lex(script_html)
    print("Tokens:")
    for token in tokens:
        if isinstance(token, Text):
            print(f"TEXT: {token.text!r}")
        else:
            print(f"TAG: {token.text!r}")

def test_quoted_attributes():
    """Test how quoted attributes are handled."""
    print("\n=== Testing Quoted Attributes ===")
    
    # Test case: Attributes with spaces
    html = '<div class="container main" style="color: red; background-color: blue;">Content</div>'
    print("\nTest Case: Attributes with spaces")
    tokens = lex(html)
    print("Tokens:")
    for token in tokens:
        if isinstance(token, Text):
            print(f"TEXT: {token.text!r}")
        else:
            print(f"TAG: {token.text!r}")
    
    # Test case: Attributes with angle brackets
    html = '<a href="page.html?param=value&gt=10" title="Click > here">Link</a>'
    print("\nTest Case: Attributes with angle brackets")
    tokens = lex(html)
    print("Tokens:")
    for token in tokens:
        if isinstance(token, Text):
            print(f"TEXT: {token.text!r}")
        else:
            print(f"TAG: {token.text!r}")
    
    # Test case: Single-quoted attributes
    html = "<img src='image.jpg' alt='An image with a > symbol'>"
    print("\nTest Case: Single-quoted attributes")
    tokens = lex(html)
    print("Tokens:")
    for token in tokens:
        if isinstance(token, Text):
            print(f"TEXT: {token.text!r}")
        else:
            print(f"TAG: {token.text!r}")

def test_mis_nested_formatting():
    """Test how mis-nested formatting tags are handled."""
    print("\n=== Testing Mis-nested Formatting Tags ===")
    
    # Test case: Bold and italic mis-nested
    html = "<b>Bold <i>both</b> italic</i>"
    print("\nTest Case: <b>Bold <i>both</b> italic</i>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)
    
    # Test case: Multiple levels of mis-nesting
    html = "<b>Bold <i>and italic <u>and underline</b> still italic</i> still underlined</u>"
    print("\nTest Case: <b>Bold <i>and italic <u>and underline</b> still italic</i> still underlined</u>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)
    
    # Test case: Mis-nested with other content
    html = "<p>Text <b>bold <i>and italic</b> just italic</i> normal text</p>"
    print("\nTest Case: <p>Text <b>bold <i>and italic</b> just italic</i> normal text</p>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)

def test_view_source():
    """Test the view-source protocol (manual verification only)."""
    print("\n=== Testing View-Source Protocol ===")
    print("To test view-source, run the browser with a URL like:")
    print("python main.py view-source:http://example.com")
    print("or")
    print(f"python main.py view-source:file://{os.path.abspath('test/test_nesting.html')}")

if __name__ == "__main__":
    test_script_handling()
    test_quoted_attributes()
    test_mis_nested_formatting()
    test_view_source() 