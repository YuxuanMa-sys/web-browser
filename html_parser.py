# html_parser.py

class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []  # Even though text nodes don't have children.
        self.parent = parent

    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

    def __repr__(self):
        if self.attributes:
            attr_str = " ".join(f'{k}="{v}"' for k, v in self.attributes.items())
            return f"<{self.tag} {attr_str}>"
        return "<" + self.tag + ">"

class HTMLParser:
    # List of self-closing (void) tags.
    SELF_CLOSING_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
    # List of tags that should appear in the <head>.
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]

    def __init__(self, body):
        self.body = body
        self.unfinished = []  # Unfinished nodes (the current open elements).

    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.casefold()] = value
            else:
                attributes[attrpair.casefold()] = ""
        return tag, attributes

    def implicit_tags(self, tag):
        """
        Insert implicit tags if they are missing.
        The 'tag' parameter is the tag being added (or None for text nodes).
        """
        while True:
            open_tags = [node.tag for node in self.unfinished]
            # Implicit <html>: if nothing is open and the tag is not "html"
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            # Implicit <head> or <body>: if only <html> is open and the upcoming tag
            # is not head, body, or a closing </html>.
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            # Implicit closing of <head>: if <html> and <head> are open,
            # but the upcoming tag does not belong in the head.
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

    def add_text(self, text):
        if text.isspace():
            return
        self.implicit_tags(None)
        if not self.unfinished:
            # If no element is open, create a default document element.
            root = Element("document", {}, None)
            self.unfinished.append(root)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, text):
        # If the tag is provided by implicit_tags, it may have no attributes.
        # We handle it the same way by parsing it.
        tag, attributes = self.get_attributes(text)
        # Ignore tags starting with "!" (doctypes, comments, etc.)
        if tag.startswith("!"):
            return
        self.implicit_tags(tag)
        # Handle self-closing tags.
        if tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            if parent:
                parent.children.append(node)
            return
        # Handle closing tags.
        if tag.startswith("/"):
            if len(self.unfinished) == 1:
                return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        else:
            # Handle opening tags.
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop() if self.unfinished else None

    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text:
                    self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

# Example test (assuming URL module is available):
if __name__ == "__main__":
    import sys
    from url import URL  # Adjust the import path as needed.
    # Retrieve the HTML source code from a given URL or file.
    body = URL(sys.argv[1]).request() if len(sys.argv) > 1 else ""
    root = HTMLParser(body).parse()
    print_tree(root)
