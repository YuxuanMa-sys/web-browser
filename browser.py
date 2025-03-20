import socket
import ssl
import os
import urllib.parse
import time
import gzip
import tkinter

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100

# Global connection pool for persistent connections
connection_pool = {}
# Global cache for HTTP responses: key -> (content, expire_time)
response_cache = {}

class URL:
    def __init__(self, url):
        # Handle view-source URLs first.
        if url.startswith("view-source:"):
            self.view_source = True
            inner_url = url[len("view-source:"):]
            self.inner = URL(inner_url)
            return
        else:
            self.view_source = False

        # Parse the standard scheme://... format.
        self.scheme, rest = url.split("://", 1)
        assert self.scheme in ["http", "https", "file", "data"]

        if self.scheme == "data":
            # data URL: data:[<mediatype>][;base64],<data>
            meta, data = rest.split(",", 1)
            self.data = urllib.parse.unquote(data)
            return

        if self.scheme == "file":
            # file URL: treat remainder as file path.
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

    def request(self, redirects_remaining=5):
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
        # If Transfer-Encoding is chunked, use a chunked reader.
        if response_headers.get("transfer-encoding", "").lower() == "chunked":
            body_bytes = b""
            while True:
                # Read the chunk size line.
                chunk_size_line = response.readline()
                if not chunk_size_line:
                    break
                chunk_size_str = chunk_size_line.decode("utf-8").strip()
                try:
                    chunk_size = int(chunk_size_str, 16)
                except ValueError:
                    raise Exception(f"Invalid chunk size: {chunk_size_str}")
                if chunk_size == 0:
                    # Read and discard any trailing header lines and final CRLF.
                    response.readline()
                    break
                chunk = response.read(chunk_size)
                body_bytes += chunk
                # Read the trailing CRLF after each chunk.
                response.read(2)
        elif "content-length" in response_headers:
            length = int(response_headers["content-length"])
            body_bytes = response.read(length)
        else:
            # No Content-Length or chunked Transfer-Encoding.
            # Read until EOF.
            body_bytes = response.read()

        # If the response is gzip-compressed, decompress it.
        if response_headers.get("content-encoding", "").lower() == "gzip":
            try:
                body_bytes = gzip.decompress(body_bytes)
            except Exception as e:
                raise Exception(f"Failed to decompress gzip data: {e}")

        # Decode the body bytes into a string.
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

        # Do not close the socket (keep-alive).
        return content



class Browser:
    def __init__(self):
        self.display_list = None
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width = WIDTH,
            height = HEIGHT
        )
        self.canvas.pack()
        self.scroll = 0
        self.window.bind("<KeyPress-Down>", self.scrolldown)

    def load(self, url):
        content = url.request()
        if getattr(url, "view_source", False):
            print(content, end="")
        else:
            text = lex(content)
            self.display_list = layout(text)
            self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)

        # self.canvas.create_rectangle(10, 20, 400, 300)
        # self.canvas.create_oval(100, 100, 150, 150)
        # self.canvas.create_text(200, 150, text = 'Hi')


    def scrolldown(self, event):
        self.scroll += SCROLL_STEP
        self.draw()


def lex(body):
    text = ""
    # Remove HTML tags and decode &lt; and &gt; entities.
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

HSTEP, VSTEP = 13, 18

def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP

    return display_list

# if __name__ == "__main__":
#     import sys
#     if len(sys.argv) < 2:
#         default_file = os.path.abspath("test.html")
#         url_str = "file://" + default_file
#     else:
#         url_str = sys.argv[1]
#     load(URL(url_str))

if __name__ == '__main__':
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
