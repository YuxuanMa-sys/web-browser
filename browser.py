# browser.py
import tkinter
import tkinter.font
from layout import WIDTH, HEIGHT, SCROLL_STEP
from html_parser import HTMLParser
from layout import Layout

class Browser:
    def __init__(self):
        self.display_list = None
        self.nodes = None  # Will hold the root node of the parsed HTML tree.
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack(fill="both", expand=True)
        self.scroll = 0

        self.window.bind("<KeyPress-Down>", self.scrolldown)
        self.window.bind("<KeyPress-Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.on_mousewheel)
        self.window.bind("<Button-4>", self.on_mousewheel_up)
        self.window.bind("<Button-5>", self.on_mousewheel_down)
        self.canvas.bind("<Configure>", self.on_configure)

    def load(self, url):
        body = url.request()
        # Build the HTML node tree using our parser.
        self.nodes = HTMLParser(body).parse()
        # Create the layout using the node tree.
        self.display_list = Layout(self.nodes, self.canvas.winfo_width()).display_list
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, txt, font, is_emoji in self.display_list:
            if y - self.scroll > self.canvas.winfo_height() or y - self.scroll < 0:
                continue
            if is_emoji:
                # If emojis were supported, draw them appropriately.
                # self.canvas.create_image(x, y - self.scroll, image=img, anchor="nw")
                return
            else:
                self.canvas.create_text(x, y - self.scroll, text=txt, anchor="nw", font=font)

        # (Optional) Draw a scrollbar if needed...
        visible_height = self.canvas.winfo_height()
        max_y = max((y for (x, y, txt, font, is_emoji) in self.display_list), default=0)
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
        if self.nodes:
            self.display_list = Layout(self.nodes, new_width).display_list
            self.draw()
