# test_parser.py
from url import URL
from parser import HTMLParser

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in getattr(node, "children", []):
        print_tree(child, indent + 2)

if __name__ == '__main__':
    # Load a local file or URL. For example, using file URL:
    body = URL("https://browser.engineering/html.html").request()
    parser = HTMLParser(body)
    dom_tree = parser.parse()
    print_tree(dom_tree)
