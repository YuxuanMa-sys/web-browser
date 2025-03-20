import socket
import ssl
import os
import urllib.parse
import time
import gzip
import tkinter

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18

# Global connection pool for persistent connections
connection_pool = {}
# Global cache for HTTP responses: key -> (content, expire_time)
response_cache = {}

# Global cache for emoji images.
emoji_images = {}

def get_emoji_image(ch):
    """
    Given a character, if an emoji image exists for it in the 'emoji' folder,
    load it using Tk's PhotoImage and cache it.
    The file name is based on the Unicode codepoint in uppercase (e.g., "1F600.png").
    """
    global emoji_images
    if ch in emoji_images:
        return emoji_images[ch]
    code = f"{ord(ch):X}"
    path = os.path.join("emoji", code + ".png")
    if os.path.exists(path):
        img = tkinter.PhotoImage(file=path)
        emoji_images[ch] = img
        return img
    else:
        emoji_images[ch] = None
        return None


class URL:
    def __init__(self, url):
        # Default to not being about:blank.
        self.about_blank = False
        self.view_source = False
        try:
            # If the URL is about:blank, mark it and return.
            if url.lower() == "about:blank":
                self.about_blank = True
                return
            # Check for the "://" separator; if missing, treat it as malformed.
            if "://" not in url:
                raise ValueError("Malformed URL")

            self.scheme, rest = url.split("://", 1)
            # Validate the scheme.
            if self.scheme not in ["http", "https", "file", "data"]:
                raise ValueError("Unsupported URL scheme")

            if self.scheme == "data":
                # data URL: data:[<mediatype>][;base64],<data>
                meta, data = rest.split(",", 1)
                self.data = urllib.parse.unquote(data)
                return

            if self.scheme == "file":
                # file URL: treat the remainder as file path.
                if not rest.startswith("/"):
                    rest = "/" + rest
                self.path = rest
                return

            # For HTTP and HTTPS, set default port.
            if self.scheme == "http":
                self.port = 80
            elif self.scheme == "https":
                self.port = 443

            if "/" not in rest:
                rest += "/"

            self.host, path = rest.split("/", 1)
            self.path = "/" + path

            # If host includes a port, parse it.
            if ":" in self.host:
                self.host, port_str = self.host.split(":", 1)
                self.port = int(port_str)
        except Exception as e:
            print("Malformed URL encountered, defaulting to about:blank:", e)
            self.about_blank = True

    def request(self, redirects_remaining=5):
        # If about:blank is flagged, return an empty page.
        if self.about_blank:
            return ""
        # Delegate view-source requests.
        if self.view_source:
            return self.inner.request(redirects_remaining)
        if self.scheme == "data":
            return self.data
        if self.scheme == "file":
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()

        # For HTTP/HTTPS, construct the canonical URL.
        canonical_url = f"{self.scheme}://{self.host}:{self.port}{self.path}"
        # Check the cache first.
        if canonical_url in response_cache:
            cached_content, expire_time = response_cache[canonical_url]
            if expire_time is None or time.time() < expire_time:
                print("Serving from cache")
                return cached_content
            else:
                del response_cache[canonical_url]

        # Reuse or create a persistent connection.
        key = (self.scheme, self.host, self.port)
        if key in connection_pool:
            print(f"Reusing connection for {key} (socket id: {id(connection_pool[key])})")
            s = connection_pool[key]
        else:
            print(f"Creating new connection for {key}")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            s.connect((self.host, self.port))
            if self.scheme == "https":
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
            connection_pool[key] = s

        # Build HTTP/1.1 request with keep-alive and gzip support.
        headers = {
            "Host": self.host,
            "Connection": "keep-alive",
            "User-Agent": "MySimpleBrowser/1.0",
            "Accept-Encoding": "gzip",
        }
        request_data = f"GET {self.path} HTTP/1.1\r\n"
        for hdr, val in headers.items():
            request_data += f"{hdr}: {val}\r\n"
        request_data += "\r\n"
        s.sendall(request_data.encode("utf-8"))

        # Use binary mode to read response.
        response = s.makefile("rb", newline=None)
        status_line = response.readline()
        if not status_line:
            raise Exception("No status line received (connection closed?)")
        status_line = status_line.decode("utf-8", errors="replace").strip()
        parts = status_line.split(" ", 2)
        if len(parts) < 2:
            raise Exception(f"Malformed status line: {status_line}")
        version = parts[0]
        status_code = parts[1]
        explanation = parts[2] if len(parts) > 2 else ""
        code = int(status_code)

        # Read response headers.
        response_headers = {}
        while True:
            line = response.readline()
            if not line or line in (b"\r\n", b"\n"):
                break
            line_str = line.decode("utf-8", errors="replace")
            if ": " in line_str:
                header, value = line_str.split(": ", 1)
                response_headers[header.lower()] = value.strip()

        # Handle redirects (status codes 300-399).
        if 300 <= code < 400:
            if redirects_remaining <= 0:
                raise Exception("Too many redirects")
            if "location" not in response_headers:
                raise Exception("Redirect response missing Location header")
            new_url = response_headers["location"]
            if new_url.startswith("/"):
                new_url = f"{self.scheme}://{self.host}{new_url}"
            print(f"Redirecting to {new_url}")
            return URL(new_url).request(redirects_remaining - 1)

        # Read the response body.
        if response_headers.get("transfer-encoding", "").lower() == "chunked":
            body_bytes = b""
            while True:
                chunk_size_line = response.readline()
                if not chunk_size_line:
                    break
                chunk_size_str = chunk_size_line.decode("utf-8").strip()
                try:
                    chunk_size = int(chunk_size_str, 16)
                except ValueError:
                    raise Exception(f"Invalid chunk size: {chunk_size_str}")
                if chunk_size == 0:
                    response.readline()
                    break
                chunk = response.read(chunk_size)
                body_bytes += chunk
                response.read(2)
        elif "content-length" in response_headers:
            length = int(response_headers["content-length"])
            body_bytes = response.read(length)
        else:
            body_bytes = response.read()

        if response_headers.get("content-encoding", "").lower() == "gzip":
            try:
                body_bytes = gzip.decompress(body_bytes)
            except Exception as e:
                raise Exception(f"Failed to decompress gzip data: {e}")

        content = body_bytes.decode("utf-8", errors="replace")

        # --- Caching logic ---
        if code in (200, 301, 404):
            allow_cache = False
            expire_time_val = None
            cache_control = response_headers.get("cache-control")
            if cache_control:
                cache_control = cache_control.lower().strip()
                if cache_control == "no-store":
                    allow_cache = False
                elif cache_control.startswith("max-age=") and "," not in cache_control:
                    try:
                        max_age = int(cache_control[len("max-age="):])
                        allow_cache = True
                        expire_time_val = time.time() + max_age
                    except ValueError:
                        allow_cache = False
                else:
                    allow_cache = False
            else:
                allow_cache = True
                expire_time_val = None

            if allow_cache:
                response_cache[canonical_url] = (content, expire_time_val)
                print("Caching response for", canonical_url)

        return content

class Browser:
    def __init__(self):
        self.display_list = None
        self.raw_text = ""
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        # Make the canvas resizable.
        self.canvas.pack(fill="both", expand=True)
        self.scroll = 0

        # Bind keyboard scrolling events.
        self.window.bind("<KeyPress-Down>", self.scrolldown)
        self.window.bind("<KeyPress-Up>", self.scrollup)

        # Bind mouse wheel events.
        self.window.bind("<MouseWheel>", self.on_mousewheel)  # Windows/macOS
        self.window.bind("<Button-4>", self.on_mousewheel_up)   # Linux scroll up
        self.window.bind("<Button-5>", self.on_mousewheel_down) # Linux scroll down

        # Bind configure event to handle window resizing.
        self.canvas.bind("<Configure>", self.on_configure)

    def load(self, url):
        content = url.request()
        if getattr(url, "view_source", False):
            print(content, end="")
        else:
            text = lex(content)
            self.raw_text = text  # Store raw text for re-layout on resize.
            self.display_list = layout(text, self.canvas.winfo_width())
            self.draw()

    def draw(self):
        self.canvas.delete("all")
        for token in self.display_list:
            # Each token is a tuple: (x, y, char, is_emoji)
            x, y, ch, is_emoji = token
            # Only draw if the token is in the visible area.
            if y - self.scroll > self.canvas.winfo_height() or y - self.scroll < 0:
                continue
            if is_emoji:
                img = get_emoji_image(ch)
                if img is not None:
                    # Draw emoji image; anchor "nw" places the top-left corner at (x, y - scroll).
                    self.canvas.create_image(x, y - self.scroll, image=img, anchor="nw")
            else:
                self.canvas.create_text(x, y - self.scroll, text=ch)
        # Draw scrollbar (see previous implementation) if needed.
        visible_height = self.canvas.winfo_height()
        max_y = max((y for (x, y, ch, is_emoji) in self.display_list), default=0)
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

# Add at the top near the other global definitions:
RTL_MODE = False  # default mode is left-to-right

def layout(text, width):
    display_list = []
    # Split the text into lines based on newline characters.
    lines = text.split("\n")
    cursor_y = VSTEP  # Start vertical position for first line.
    for line in lines:
        # Determine line length in pixels.
        line_length = len(line) * HSTEP
        if RTL_MODE:
            # Right-to-left: compute starting x so that line is right-aligned.
            start_x = max(HSTEP, width - line_length)
            cursor_x = start_x
            for ch in line:
                # Check for emoji support.
                is_emoji = get_emoji_image(ch) is not None
                display_list.append((cursor_x, cursor_y, ch, is_emoji))
                cursor_x += HSTEP
        else:
            # Left-to-right: start at the left margin.
            cursor_x = HSTEP
            for ch in line:
                is_emoji = get_emoji_image(ch) is not None
                display_list.append((cursor_x, cursor_y, ch, is_emoji))
                cursor_x += HSTEP
        # Add extra vertical space to simulate a paragraph break.
        cursor_y += VSTEP * 2
    return display_list

# In your main block, process command-line arguments to set RTL_MODE.
if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    url_str = None
    # Check if the RTL flag is provided.
    if "--rtl" in args:
        RTL_MODE = True
        args.remove("--rtl")
    if args:
        url_str = args[0]
    else:
        url_str = "about:blank"
    Browser().load(URL(url_str))
    tkinter.mainloop()

