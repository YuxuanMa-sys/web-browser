# html_parser.py
import os
from typing import List

# Node classes
class Text:
    def __init__(self, text: str, parent):
        self.text = text
        self.children: List = []  # Text nodes never have children, but for consistency.
        self.parent = parent

    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag: str, attributes: dict, parent):
        self.tag = tag
        self.attributes = attributes
        self.children: List = []
        self.parent = parent

    def __repr__(self):
        return f"<{self.tag}>"

# A minimal set of self-closing (void) tags.
SELF_CLOSING_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

class HTMLParser:
    # For basic attribute parsing (very simple).
    def get_attributes(self, text: str):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                # Remove quotes if present.
                if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
                    value = value[1:-1]
                attributes[key.casefold()] = value
            else:
                attributes[attrpair.casefold()] = ""
        return tag, attributes

    def __init__(self, body: str):
        self.body = body
        self.unfinished = []  # Stack of unfinished nodes

    def add_text(self, text: str):
        # Skip whitespace-only text
        if text.isspace():
            return
        parent = self.unfinished[-1] if self.unfinished else None
        node = Text(text, parent)
        if parent:
            parent.children.append(node)
        else:
            # No current parent means this text becomes the root.
            self.unfinished.append(node)

    def add_tag(self, tag: str):
        # First, ignore doctype and comments.
        if tag.startswith("!"):
            return

        # Parse attributes.
        tag_name, attributes = self.get_attributes(tag)

        if tag.startswith("/"):
            # Closing tag. Ensure we don't pop the last node.
            if len(self.unfinished) <= 1:
                return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag_name in SELF_CLOSING_TAGS or tag.endswith("/"):
            # Self-closing tag: create node and attach, but do not push.
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag_name, attributes, parent)
            if parent:
                parent.children.append(node)
        else:
            # Opening tag.
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag_name, attributes, parent)
            if parent:
                parent.children.append(node)
            self.unfinished.append(node)

    def parse(self):
        buffer = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if buffer:
                    self.add_text(buffer)
                    buffer = ""
            elif c == ">":
                in_tag = False
                self.add_tag(buffer.strip())
                buffer = ""
            else:
                buffer += c
        if buffer and not in_tag:
            self.add_text(buffer)
        return self.finish()

    def finish(self):
        # Close any remaining unfinished nodes.
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop() if self.unfinished else None
