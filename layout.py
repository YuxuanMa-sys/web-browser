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
    Contents of <script> tags are treated as plain text until </script> is encountered.
    Handles quoted attributes in tags properly.
    """
    tokens = []
    buffer = ""
    
    # States for our FSM
    STATE_TEXT = 0          # Regular text outside tags
    STATE_TAG = 1           # Inside a tag
    STATE_COMMENT = 2       # Inside a comment
    STATE_SCRIPT = 3        # Inside a script tag
    STATE_QUOTE_SINGLE = 4  # Inside a single-quoted attribute
    STATE_QUOTE_DOUBLE = 5  # Inside a double-quoted attribute
    
    state = STATE_TEXT
    
    i = 0
    while i < len(body):
        c = body[i]
        
        # Handle different states
        if state == STATE_TEXT:
            # Check for comment start
            if c == '<' and i + 3 < len(body) and body[i:i+4] == '<!--':
                if buffer:
                    tokens.append(Text(buffer))
                    buffer = ""
                state = STATE_COMMENT
                i += 4  # Skip over <!--
                continue
                
            # Check if we're entering a script tag
            elif c == '<' and i + 6 < len(body) and body[i:i+7].lower() == '<script':
                if buffer:
                    tokens.append(Text(buffer))
                    buffer = ""
                state = STATE_TAG
                buffer = "script"  # Start accumulating the tag
                i += 7  # Skip over <script
                continue
                
            # Regular tag start
            elif c == '<':
                if buffer:
                    tokens.append(Text(buffer))
                    buffer = ""
                state = STATE_TAG
            else:
                buffer += c
                
        elif state == STATE_TAG:
            # Handle quoted attribute values
            if c == '"':
                buffer += c
                state = STATE_QUOTE_DOUBLE
            elif c == "'":
                buffer += c
                state = STATE_QUOTE_SINGLE
            # End of tag
            elif c == '>':
                tag_text = buffer.strip()
                tokens.append(Tag(tag_text))
                buffer = ""
                # Check if we just opened a script tag
                if tag_text.lower() == "script" or tag_text.lower().startswith("script "):
                    state = STATE_SCRIPT
                else:
                    state = STATE_TEXT
            else:
                buffer += c
                
        elif state == STATE_COMMENT:
            # Check for comment end
            if i + 2 < len(body) and body[i:i+3] == '-->':
                state = STATE_TEXT
                i += 3  # Skip over -->
                continue
                
        elif state == STATE_SCRIPT:
            # Check for script end tag
            if c == '<' and i + 8 < len(body) and body[i:i+9].lower() == '</script>':
                if buffer:
                    tokens.append(Text(buffer))
                    buffer = ""
                tokens.append(Tag("/script"))
                state = STATE_TEXT
                i += 9  # Skip over </script>
                continue
            elif c == '<' and i + 8 < len(body) and body[i:i+8].lower() == '</script':
                # Handle case where </script is followed by space, tab, newline, etc.
                next_char = body[i+8] if i+8 < len(body) else ''
                if next_char in ' \t\n\r\v/>':
                    if buffer:
                        tokens.append(Text(buffer))
                        buffer = ""
                    tokens.append(Tag("/script"))
                    state = STATE_TEXT
                    # Skip to the closing >
                    while i < len(body) and body[i] != '>':
                        i += 1
                    i += 1  # Skip over >
                    continue
            else:
                buffer += c
                
        elif state == STATE_QUOTE_DOUBLE:
            buffer += c
            # Exit double quote state only on unescaped double quote
            if c == '"' and body[i-1] != '\\':
                state = STATE_TAG
                
        elif state == STATE_QUOTE_SINGLE:
            buffer += c
            # Exit single quote state only on unescaped single quote
            if c == "'" and body[i-1] != '\\':
                state = STATE_TAG
                
        i += 1
            
    # Handle any remaining buffer
    if buffer:
        if state == STATE_TEXT:
            tokens.append(Text(buffer))
        elif state == STATE_TAG:
            # If we ended in a tag, treat it as text since it's incomplete
            tokens.append(Text("<" + buffer))
            
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
