# ui.py
import tkinter
import tkinter.font
import math
from url import get_emoji_image
from typing import Literal

# Global constants.
WIDTH = 800
HEIGHT = 600
SCROLL_STEP = 100
HSTEP = 13
VSTEP = 18

WeightType = Literal["normal", "bold"]
StyleType = Literal["roman", "italic"]

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

        # Font styling state
        self.weight: WeightType = "normal"
        self.style: StyleType = "roman"
        self.size = 12

        # Cursor state
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP

        # Then loop over the tokens
        for tok in tokens:
            self.token(tok)

    def token(self, tok):
        if isinstance(tok, Text):
            # For each word in the text
            for word in tok.text.split():
                self.word(word)
            # Maybe a line break after each text token
            self.cursor_x = HSTEP
            self.cursor_y += self.line_height()
        else:
            # It's a Tag
            tag = tok.text.lower()
            if tag == "b":
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
                # line break
                self.cursor_x = HSTEP
                self.cursor_y += self.line_height()
            elif tag == "p":
                # paragraph break
                self.cursor_x = HSTEP
                self.cursor_y += 2 * self.line_height()
            # ignore other tags

    def word(self, text):
        # Create a font with the current styling
        font = tkinter.font.Font(
            family="Times",
            size=self.size,
            weight=self.weight,
            slant=self.style,
        )

        w = font.measure(text)
        # Check if it fits
        if self.cursor_x + w > self.width - HSTEP:
            self.cursor_x = HSTEP
            self.cursor_y += self.line_height()

        # Check if it's a single-character emoji
        is_emoji = (len(text) == 1 and get_emoji_image(text) is not None)

        # Add to the display list
        self.display_list.append((self.cursor_x, self.cursor_y, text, font, is_emoji))

        # Advance
        self.cursor_x += w
        # Optionally add a space if not the last word in the text token
        space_w = font.measure(" ")
        if self.cursor_x + space_w <= self.width - HSTEP:
            self.cursor_x += space_w

    def line_height(self):
        # We can compute a "temporary" font or store one
        tmp_font = tkinter.font.Font(size=self.size, weight=self.weight, slant=self.style)
        return math.ceil(tmp_font.metrics("linespace") * 1.25)


class Browser:
    def __init__(self):
        self.display_list = None
        self.raw_tokens = []  # Store tokens for re-layout on resize.
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack(fill="both", expand=True)
        self.scroll = 0
        self.font = tkinter.font.Font(family="Times", size=16)
        self.window.bind("<KeyPress-Down>", self.scrolldown)
        self.window.bind("<KeyPress-Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.on_mousewheel)  # Windows/macOS
        self.window.bind("<Button-4>", self.on_mousewheel_up)   # Linux scroll up
        self.window.bind("<Button-5>", self.on_mousewheel_down) # Linux scroll down
        self.canvas.bind("<Configure>", self.on_configure)

    def load(self, url):
        content = url.request()
        if getattr(url, "view_source", False):
            print(content, end="")
        else:
            tokens = lex(content)
            self.raw_tokens = tokens  # Store tokens for re-layout.
            layout_obj = Layout(tokens, self.canvas.winfo_width())
            self.display_list = layout_obj.display_list
            self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, txt, fnt, is_emoji in self.display_list:
            if y - self.scroll > self.canvas.winfo_height() or y - self.scroll < 0:
                continue
            if is_emoji:
                img = get_emoji_image(txt)
                if img:
                    self.canvas.create_image(x, y - self.scroll, image=img, anchor="nw")
            else:
                self.canvas.create_text(x, y - self.scroll, text=txt, anchor="nw", font=fnt)
        visible_height = self.canvas.winfo_height()
        max_y = max((y for (x, y, txt, fnt, is_emoji) in self.display_list), default=0)
        max_scroll = max(0, max_y - visible_height)
        if self.scroll > max_scroll:
            self.scroll = max_scroll
        if max_y > visible_height:
            scrollbar_width = 10
            thumb_height = visible_height * (visible_height / max_y)
            thumb_height = max(thumb_height, 20)
            thumb_y = (self.scroll / max_scroll) * (visible_height - thumb_height) if max_scroll > 0 else 0
            x0 = self.canvas.winfo_width() - scrollbar_width
            y0 = thumb_y
            x1 = self.canvas.winfo_width()
            y1 = thumb_y + thumb_height
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="blue")

    def scrolldown(self, event):
        self.scroll += SCROLL_STEP
        self.draw()

    def scrollup(self, event):
        self.scroll -= SCROLL_STEP
        if self.scroll < 0:
            self.scroll = 0
        self.draw()

    def on_mousewheel(self, event):
        scroll_amount = - (event.delta / 120) * SCROLL_STEP
        self.scroll += scroll_amount
        if self.scroll < 0:
            self.scroll = 0
        self.draw()

    def on_mousewheel_up(self, event):
        self.scroll -= SCROLL_STEP
        if self.scroll < 0:
            self.scroll = 0
        self.draw()

    def on_mousewheel_down(self, event):
        self.scroll += SCROLL_STEP
        self.draw()

    def on_configure(self, event):
        new_width = event.width
        if self.raw_tokens:
            layout_obj = Layout(self.raw_tokens, new_width)
            self.display_list = layout_obj.display_list
            self.draw()
