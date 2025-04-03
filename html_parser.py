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
    # List of text formatting tags that can be mis-nested
    FORMATTING_TAGS = {
        "b", "i", "u", "em", "strong", "small", "big", "code", 
        "strike", "s", "tt", "mark", "span", "font"
    }

    def __init__(self, body):
        self.body = body
        self.unfinished = []  # Unfinished nodes (the current open elements).
        self.formatting_elements = []  # Keep track of open formatting elements

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
        # This specifically handles cases like <!DOCTYPE html> and any <!-- comments -->
        # that might slip through the lexer/parser
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
            tag_name = tag[1:]  # Remove the '/' prefix
            
            # Special handling for formatting tags that might be mis-nested
            if tag_name in self.FORMATTING_TAGS and tag_name in [elem.tag for elem in self.formatting_elements]:
                self.handle_mis_nested_formatting(tag_name)
            else:
                # Normal closing tag handling
                if len(self.unfinished) == 1:
                    return
                node = self.unfinished.pop()
                
                # If this is a formatting tag being closed, remove it from formatting_elements
                if node.tag in self.FORMATTING_TAGS:
                    self.formatting_elements = [elem for elem in self.formatting_elements if elem != node]
                    
                parent = self.unfinished[-1]
                parent.children.append(node)
        else:
            # Special handling for paragraphs and list items
            # which shouldn't be nested directly within themselves
            if tag in ["p", "li"]:
                self.handle_special_nesting(tag)
                
            # Handle opening tags.
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)
            
            # If this is a formatting tag, add it to formatting_elements
            if tag in self.FORMATTING_TAGS:
                self.formatting_elements.append(node)
            
    def handle_mis_nested_formatting(self, tag_name):
        """
        Handle mis-nested formatting tags by inserting appropriate close/open tags.
        For example: <b>Bold <i>both</b> italic</i> should be treated as
                    <b>Bold <i>both</i></b><i> italic</i>
        """
        # Find the formatting element in the list
        format_index = None
        for i, elem in enumerate(self.formatting_elements):
            if elem.tag == tag_name:
                format_index = i
                break
                
        if format_index is None:
            # The tag isn't in our formatting elements, handle as normal
            if len(self.unfinished) == 1:
                return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
            return
            
        # Get the formatting element
        format_elem = self.formatting_elements[format_index]
        
        # First, close all tags opened after this formatting tag
        tags_to_reopen = []
        while self.unfinished[-1] != format_elem:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
            
            # If this is a formatting tag that needs to be reopened, remember it
            if node.tag in self.FORMATTING_TAGS and node in self.formatting_elements:
                tags_to_reopen.append(node)
                # Remove from formatting elements as we'll add a new one later
                self.formatting_elements.remove(node)
                
        # Now close the actual formatting tag we're targeting
        node = self.unfinished.pop()  # This should be format_elem
        parent = self.unfinished[-1]
        parent.children.append(node)
        self.formatting_elements.remove(format_elem)
        
        # Reopen tags that we had to close, in the original order
        for tag_elem in reversed(tags_to_reopen):
            # Create a new element with the same attributes
            new_elem = Element(tag_elem.tag, tag_elem.attributes, self.unfinished[-1])
            self.unfinished.append(new_elem)
            self.formatting_elements.append(new_elem)
            
    def handle_special_nesting(self, tag):
        """
        Handle special nesting rules for certain elements:
        - <p> elements cannot contain other <p> elements
        - <li> elements cannot be directly nested in other <li> elements
          (except when they're part of a nested list)
        """
        # For each tag in the unfinished stack (from newest to oldest)
        # Check if we need to auto-close anything
        for i in range(len(self.unfinished) - 1, -1, -1):
            if tag == "p" and self.unfinished[i].tag == "p":
                # Close any open paragraph when starting a new paragraph
                # This creates sibling paragraphs rather than nested ones
                while self.unfinished[-1].tag != "p":
                    node = self.unfinished.pop()
                    parent = self.unfinished[-1]
                    parent.children.append(node)
                # Now close the paragraph itself
                node = self.unfinished.pop()
                parent = self.unfinished[-1]
                parent.children.append(node)
                break
            
            elif tag == "li" and self.unfinished[i].tag == "li":
                # For list items, we need to check if there's a list (ul/ol) in between
                # If not, close the current li
                list_between = False
                for j in range(len(self.unfinished) - 1, i, -1):
                    if self.unfinished[j].tag in ["ul", "ol"]:
                        list_between = True
                        break
                
                if not list_between:
                    # Close until we reach the li to close
                    while self.unfinished[-1].tag != "li":
                        node = self.unfinished.pop()
                        parent = self.unfinished[-1]
                        parent.children.append(node)
                    # Now close the li
                    node = self.unfinished.pop()
                    parent = self.unfinished[-1]
                    parent.children.append(node)
                break

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
        in_comment = False
        
        i = 0
        while i < len(self.body):
            c = self.body[i]
            
            # Check for comment start
            if not in_comment and c == '<' and i + 3 < len(self.body) and self.body[i:i+4] == '<!--':
                # We're entering a comment
                if text and not in_tag:
                    self.add_text(text)
                    text = ""
                in_comment = True
                i += 4  # Skip over <!--
                continue
                
            # Check for comment end
            if in_comment and i + 2 < len(self.body) and self.body[i:i+3] == '-->':
                # We're leaving a comment
                in_comment = False
                i += 3  # Skip over -->
                continue
                
            # Skip characters while in comment
            if in_comment:
                i += 1
                continue
            
            # Regular HTML parsing logic (mostly unchanged)
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
            i += 1
                
        if not in_tag and not in_comment and text:
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
