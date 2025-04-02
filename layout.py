# layout.py
import tkinter
import tkinter.font
import math
from typing import Literal

# Global constants.
WIDTH = 800
HEIGHT = 600
SCROLL_STEP = 100
HSTEP = 13
VSTEP = 18

WeightType = Literal["normal", "bold"]
StyleType = Literal["roman", "italic"]


FONTS = {}

def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        # Create the font
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        # Create a label so that measuring is cached more effectively
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

# Text and Tag classes for tokenizing the HTML content.
class Text:
    def __init__(self, text):
        self.text = text

class Tag:
    def __init__(self, tag):
        self.text = tag

def lex(body):
    """
    Lexical analyzer that returns a list of tokens (Text or Tag objects).
    Unfinished tags are dropped.
    Comments (<!-- ... -->) are skipped entirely.
    """
    tokens = []
    buffer = ""
    in_tag = False
    in_comment = False
    comment_buffer = ""
    
    i = 0
    while i < len(body):
        c = body[i]
        
        # Check for comment start sequence
        if not in_comment and c == '<' and i + 3 < len(body) and body[i:i+4] == '<!--':
            # We're entering a comment
            if buffer:
                tokens.append(Text(buffer))
                buffer = ""
            in_comment = True
            i += 4  # Skip over <!--
            continue
            
        # Check for comment end sequence
        if in_comment and i + 2 < len(body) and body[i:i+3] == '-->':
            # We're leaving a comment
            in_comment = False
            i += 3  # Skip over -->
            continue
            
        # Skip characters while in comment
        if in_comment:
            i += 1
            continue

        # Normal token handling (unchanged from original implementation)
        if c == "<":
            if buffer:
                tokens.append(Text(buffer))
                buffer = ""
            in_tag = True
        elif c == ">":
            if in_tag:
                tokens.append(Tag(buffer.strip()))
                buffer = ""
                in_tag = False
        else:
            buffer += c
        i += 1
            
    if buffer and not in_comment:
        tokens.append(Text(buffer))
    return tokens



class Layout:
    def __init__(self, root, width=WIDTH):
        self.display_list = []  # List of tuples: (x, y, text, font, is_emoji)
        self.line = []  # Current line buffer

        # Font styling state
        self.weight = "normal"
        self.style = "roman"
        self.size = 12

        # Cursor state
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP

        self.center_mode = False
        self.width = width

        # Recursively walk the node tree
        self.recurse(root)
        self.flush()

    def open_tag(self, tag):
        # Example handling for some tags:
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag.startswith("h1"):
            self.flush()          # Flush current line before heading changes layout
            self.center_mode = True
        # ... add additional tag handling as needed

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag.startswith("h1"):
            self.flush()
            self.center_mode = False
        # ... add additional tag handling as needed

    def recurse(self, node):
        # We assume that text nodes are instances of Text (from html_parser) and
        # element nodes are instances of Element.
        from html_parser import Text  # Importing our node classes.
        if isinstance(node, Text):
            # Process text node: split text into words and layout each word.
            for word in node.text.split():
                self.word(word)
        else:
            # For element nodes, treat the tag as an open tag,
            # then recurse into its children, then call the close_tag.
            self.open_tag(node.tag)
            for child in node.children:
                self.recurse(child)
            self.close_tag(node.tag)

    def word(self, word):
        current_font = get_font(self.size, self.weight, self.style)
        w = current_font.measure(word)
        # If the word doesn't fit in the current line, flush the line.
        if self.cursor_x + w > self.width - HSTEP:
            self.flush()
        # Append the word along with its x-coordinate and font.
        self.line.append((self.cursor_x, word, current_font))
        self.cursor_x += w
        # Measure a space and add it.
        space_w = current_font.measure(" ")
        if self.cursor_x + space_w > self.width - HSTEP:
            self.flush()
        else:
            self.cursor_x += space_w

    def flush(self):
        if not self.line:
            return

        # If center mode is enabled, adjust each word's x-coordinate.
        if self.center_mode:
            total_width = max(x + font.measure(word) for (x, word, font) in self.line) - HSTEP
            offset = (self.width - total_width) // 2
            self.line = [(x + offset, word, font) for (x, word, font) in self.line]

        # First pass: compute metrics for all words.
        metrics = [font.metrics() for (x, word, font) in self.line]
        max_ascent = max(m["ascent"] for m in metrics)
        max_descent = max(m["descent"] for m in metrics)
        # Compute baseline position.
        baseline = self.cursor_y + int(1.25 * max_ascent)
        # Second pass: assign y positions.
        for (x, word, font) in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font, False))
        # Update cursor_y to move to the next line.
        self.cursor_y = baseline + int(1.25 * max_descent)
        # Reset horizontal cursor and clear the line buffer.
        self.cursor_x = HSTEP
        self.line = []
