# Web Browser Tests

This directory contains tests for the web browser implementation, focusing on HTML parsing features.

## Test Files

- `test_comments.py`: Tests HTML comment handling in the lexer and parser
- `test_comments.html`: Sample HTML file with various comment types for browser rendering tests
- `test_edge_comment.py`: Tests edge cases for HTML comments, particularly the `<!-->` syntax
- `test_edge_comment.html`: HTML file with edge cases of comment syntax
- `test_nesting.py`: Tests the special nesting rules for paragraphs and list items
- `test_nesting.html`: HTML file to demonstrate proper paragraph and list item nesting in the browser

## Running Tests

To run the comment handling tests:
```
python test/test_comments.py
```

To run the edge case tests:
```
python test/test_edge_comment.py
```

To run the element nesting tests:
```
python test/test_nesting.py
```

To view the test HTML files in the browser:
```
python test/test_edge_comment.py --browser
```

or:
```
python main.py file://$(pwd)/test/test_nesting.html
``` 