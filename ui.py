# ui.py
import tkinter
import tkinter.font
import math
from url import get_emoji_image

# Global constants.
WIDTH = 800
HEIGHT = 600
SCROLL_STEP = 100
HSTEP = 13
VSTEP = 18

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

def layout(tokens, width):
    """
    Word-by-word layout with basic text styling:
    - Processes tokens from lex().
    - For Text tokens, splits text into words on whitespace.
    - Measures each word using tkinter.font.Font() with current style.
    - Wraps to a new line if a word doesn't fit in the remaining space.
    - Inserts a space (measured via font.measure(" ")) between words.
    - Processes Tag tokens to adjust styling: supports <b>, </b>, <i>, </i>, <br>, and <p>.
    Returns a list of display tokens: (x, y, word, font, is_emoji).
    """
    display_list = []
    weight = "normal"
    style = "roman"
    size = 16
    cursor_x = HSTEP
    cursor_y = VSTEP
    for tok in tokens:
        if isinstance(tok, Tag):
            tag_text = tok.text.lower()
            if tag_text == "b":
                weight = "bold"
            elif tag_text == "/b":
                weight = "normal"
            elif tag_text == "i":
                style = "italic"
            elif tag_text == "/i":
                style = "roman"
            elif tag_text == "br":
                cursor_x = HSTEP
                cursor_y += math.ceil(tkinter.font.Font(size=size).metrics("linespace") * 1.25)
            elif tag_text == "p":
                cursor_x = HSTEP
                cursor_y += math.ceil(tkinter.font.Font(size=size).metrics("linespace") * 1.25) * 2
            # Ignore other tags.
        elif isinstance(tok, Text):
            words = tok.text.split()
            for idx, word in enumerate(words):
                current_font = tkinter.font.Font(family="Times", size=size, weight=weight, slant=style)
                w = current_font.measure(word)
                if cursor_x + w > width - HSTEP:
                    cursor_x = HSTEP
                    cursor_y += math.ceil(current_font.metrics("linespace") * 1.25)
                is_emoji = (len(word) == 1 and get_emoji_image(word) is not None)
                display_list.append((cursor_x, cursor_y, word, current_font, is_emoji))
                cursor_x += w
                if idx != len(words) - 1:
                    space_w = current_font.measure(" ")
                    if cursor_x + space_w > width - HSTEP:
                        cursor_x = HSTEP
                        cursor_y += math.ceil(current_font.metrics("linespace") * 1.25)
                    else:
                        cursor_x += space_w
            # After processing a text token, force a newline.
            cursor_x = HSTEP
            cursor_y += math.ceil(tkinter.font.Font(size=size).metrics("linespace") * 1.25)
    return display_list

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
            self.display_list = layout(tokens, self.canvas.winfo_width())
            self.draw()

    def draw(self):
        self.canvas.delete("all")
        for token in self.display_list:
            x, y, txt, fnt, is_emoji = token
            if y - self.scroll > self.canvas.winfo_height() or y - self.scroll < 0:
                continue
            if is_emoji:
                img = get_emoji_image(txt)
                if img is not None:
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
            self.display_list = layout(self.raw_tokens, new_width)
            self.draw()
