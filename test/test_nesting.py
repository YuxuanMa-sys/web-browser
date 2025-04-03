#!/usr/bin/env python3
# test_nesting.py - Test HTML element nesting behavior

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add parent directory to path
from html_parser import HTMLParser

def print_tree(node, indent=0):
    """Print the HTML tree structure."""
    print(" " * indent + str(node))
    for child in node.children:
        print_tree(child, indent + 2)

def test_paragraph_nesting():
    """Test how paragraphs are handled when nested."""
    print("\n=== Testing Paragraph Nesting ===")
    
    # Test case: <p>hello<p>world</p> should be two sibling paragraphs
    html = "<p>hello<p>world</p>"
    print("\nTest Case: <p>hello<p>world</p>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)
    
    # Test case: <p>Paragraph with <b>bold text</b> <p>and a nested paragraph</p></p>
    html = "<p>Paragraph with <b>bold text</b> <p>and a nested paragraph</p></p>"
    print("\nTest Case: <p>Paragraph with <b>bold text</b> <p>and a nested paragraph</p></p>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)
    
    # Test case: Multiple nested paragraphs
    html = "<p>First <p>Second <p>Third</p></p></p>"
    print("\nTest Case: <p>First <p>Second <p>Third</p></p></p>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)

def test_list_item_nesting():
    """Test how list items are handled when nested."""
    print("\n=== Testing List Item Nesting ===")
    
    # Test case: Basic list nesting - should be acceptable
    html = "<ul><li>First item</li><li>Second item</li></ul>"
    print("\nTest Case: <ul><li>First item</li><li>Second item</li></ul>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)
    
    # Test case: Invalid list item nesting - should be corrected
    html = "<ul><li>First item<li>Second item directly in first</li></li></ul>"
    print("\nTest Case: <ul><li>First item<li>Second item directly in first</li></li></ul>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)
    
    # Test case: Valid nested list - should remain nested
    html = "<ul><li>Item 1<ul><li>Nested item 1</li><li>Nested item 2</li></ul></li></ul>"
    print("\nTest Case: <ul><li>Item 1<ul><li>Nested item 1</li><li>Nested item 2</li></ul></li></ul>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)
    
    # Test case: Deeply nested list items that should be siblings
    html = "<ul><li>One<li>Two<li>Three</li></li></li></ul>"
    print("\nTest Case: <ul><li>One<li>Two<li>Three</li></li></li></ul>")
    root = HTMLParser(html).parse()
    print("Result Tree:")
    print_tree(root)

if __name__ == "__main__":
    test_paragraph_nesting()
    test_list_item_nesting() 