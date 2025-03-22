# ui.py
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
    """
    tokens = []
    buffer = ""
    in_tag = False
    for c in body:
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
    if buffer:
        tokens.append(Text(buffer))
    return tokens


class Layout:
    def __init__(self, tokens, width):
        # Initialize fields
        self.tokens = tokens
        self.width = width
        self.display_list = []
        self.line = []

        # Font styling state
        self.weight: WeightType = "normal"
        self.style: StyleType = "roman"
        self.size = 12

        # Cursor state
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP

        self.center_mode = False

        # Then loop over the tokens
        for tok in tokens:
            self.token(tok)

        self.flush()

    def token(self, tok):
        if isinstance(tok, Text):
            # For each word in the text
            for word in tok.text.split():
                self.word(word)


        else:
            # It's a Tag
            tag = tok.text.lower()
            if tag.startswith("h1") and "class" in tag and "title" in tag:
                self.flush()
                self.center_mode = True
            elif tag == "/h1":
                self.flush()  # Flush the h1 content.
                self.center_mode = False
            elif tag == "b":
                self.weight = "bold"
            elif tag == "/b":
                self.weight = "normal"
            elif tag == "i":
                self.style = "italic"
            elif tag == "/i":
                self.style = "roman"
            elif tag == "small":
                self.size -= 2
            elif tag == "/small":
                self.size += 2
            elif tag == "big":
                self.size += 4
            elif tag == "/big":
                self.size -= 4
            elif tag == "br":
                self.flush()  # finish current line
                self.cursor_y += self.line_height()

            elif tag == "p":
                self.flush()  # finish current line
                self.cursor_y += 2 * self.line_height()

        # ignore other tags

    def word(self, word):
        # Create a font with the current styling.
        current_font = get_font(self.size, self.weight, self.style)
        w = current_font.measure(word)
        # If the word doesn't fit, flush the current line.
        if self.cursor_x + w > self.width - HSTEP:
            self.flush()
        # Append the word to the line buffer. (No y position computed yet.)
        self.line.append((self.cursor_x, word, current_font))
        # Advance cursor_x by word width.
        self.cursor_x += w
        # Add space after word.
        space_w = current_font.measure(" ")
        if self.cursor_x + space_w > self.width - HSTEP:
            self.flush()
        else:
            self.cursor_x += space_w

    def flush(self):
        if not self.line:
            return

        if self.center_mode:
            # Compute total width: maximum (x + word width) among tokens.
            total_width = max(x + font.measure(word) for (x, word, font) in self.line) - HSTEP
            offset = (self.width - total_width) // 2
            # Adjust x coordinates of all tokens.
            self.line = [(x + offset, word, font) for (x, word, font) in self.line]
        # First pass: compute metrics for all words in this line.
        metrics = [font.metrics() for (x, word, font) in self.line]
        max_ascent = max(m["ascent"] for m in metrics)
        max_descent = max(m["descent"] for m in metrics)
        # Compute baseline: current cursor_y plus 1.25×max_ascent.
        baseline = self.cursor_y + int(1.25 * max_ascent)
        # Second pass: assign y positions so that each word's top is (baseline - its ascent).
        for (x, word, font) in self.line:
            y = baseline - font.metrics("ascent")
            # Here we add the token to the display list.
            # For simplicity, we mark is_emoji as False.
            self.display_list.append((x, y, word, font, False))
        # Update cursor_y: move down by baseline plus 1.25×max_descent.
        self.cursor_y = baseline + int(1.25 * max_descent)
        # Reset horizontal position and clear the line buffer.
        self.cursor_x = HSTEP
        self.line = []



    def line_height(self):
        # We can compute a "temporary" font or store one
        tmp_font = tkinter.font.Font(size=self.size, weight=self.weight, slant=self.style)
        return math.ceil(tmp_font.metrics("linespace") * 1.25)


