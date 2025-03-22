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


def lex(body):
    text = ""
    result = []
    in_tag = False
    i = 0
    while i < len(body):
        c = body[i]
        if c == "<":
            in_tag = True
            i += 1
            continue
        elif c == ">":
            in_tag = False
            i += 1
            continue
        if not in_tag:
            result.append(c)
            text += c
        i += 1
    html_text = "".join(result)
    html_text = html_text.replace("&lt;", "<").replace("&gt;", ">")
    print(html_text, end="")
    return text

def layout(text, width):
    font = tkinter.font.Font()
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text.split():
        w = font.measure(c)
        # print(c, w)
        if c == "\n":
            cursor_x = HSTEP
            cursor_y += VSTEP * 2
        else:
            # Check if the character is an emoji (if an image exists for it).
            img = get_emoji_image(c)
            if img is not None:
                display_list.append((cursor_x, cursor_y, c, True))
            else:
                display_list.append((cursor_x, cursor_y, c, False))
                cursor_x += w + font.measure(" ")
            cursor_x += HSTEP
            if cursor_x + w >= width - HSTEP:
                cursor_y += font.metrics("linespace") * 1.25
                cursor_x = HSTEP
    return display_list

class Browser:
    def __init__(self):
        self.display_list = None
        self.raw_text = ""
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
            # print(1)
            print(content, end="")
        else:
            text = lex(content)
            self.raw_text = text  # Store raw text for re-layout on resize.
            self.display_list = layout(text, self.canvas.winfo_width())
            self.draw()

    def draw(self):
        self.canvas.delete("all")
        for token in self.display_list:
            x, y, txt, is_emoji = token
            if y - self.scroll > self.canvas.winfo_height() or y - self.scroll < 0:
                continue
            if is_emoji:
                img = get_emoji_image(txt)
                if img is not None:
                    self.canvas.create_image(x, y - self.scroll, image=img, anchor="nw")
            else:
                self.canvas.create_text(x, y - self.scroll, text=txt, anchor="nw")
        visible_height = self.canvas.winfo_height()
        max_y = max((y for (x, y, txt, is_emoji) in self.display_list), default=0)
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
        if self.raw_text:
            self.display_list = layout(self.raw_text, new_width)
            self.draw()
