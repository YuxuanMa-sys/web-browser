# url.py
import socket
import ssl
import os
import urllib.parse
import time
import gzip
import tkinter

# Global connection pool for persistent connections.
connection_pool = {}
# Global cache for HTTP responses: key -> (content, expire_time).
response_cache = {}
# Global cache for emoji images.
emoji_images = {}

def get_emoji_image(ch):
    """
    Given a character, if an emoji image exists for it in the 'emoji' folder,
    load it using Tk's PhotoImage and cache it.
    Only single-character strings are considered for emoji rendering.
    The filename is based on the Unicode codepoint in uppercase (e.g., "1F600.png").
    """
    if len(ch) != 1:
        return None
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
            # Check for view-source: prefix
            if url.lower().startswith("view-source:"):
                self.view_source = True
                url = url[len("view-source:"):]
                
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
            # Get the original content
            inner_url = URL(self.get_url_without_view_source())
            content = inner_url.request(redirects_remaining)
            # Return the syntax highlighted version
            return self.highlight_html_source(content)
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

    def get_url_without_view_source(self):
        """Return the URL string without the view-source: prefix"""
        if self.about_blank:
            return "about:blank"
        if self.scheme == "data":
            meta_data = ""  # You'd need to reconstruct the metadata part here
            return f"data:{meta_data},{self.data}"
        if self.scheme == "file":
            return f"file://{self.path}"
        # Reconstruct HTTP and HTTPS URLs
        port_str = "" if (self.scheme == "http" and self.port == 80) or (self.scheme == "https" and self.port == 443) else f":{self.port}"
        return f"{self.scheme}://{self.host}{port_str}{self.path}"
        
    def highlight_html_source(self, html_content):
        """Syntax highlight HTML content"""
        from html_parser import HTMLParser
        
        # Create a syntax highlighter that extends the HTML parser
        class SyntaxHighlighter(HTMLParser):
            def __init__(self, html):
                super().__init__(html)
                self.result = []
                
            def add_tag(self, text):
                tag, attributes = self.get_attributes(text)
                # Don't ignore DOCTYPE or comments in the view-source mode
                if tag.startswith("!"):
                    self.result.append(f"<span style='color:blue'>&lt;!{text[1:]}&gt;</span>")
                    return
                    
                # Process tag with appropriate highlighting
                if tag.startswith("/"):
                    # Closing tag
                    self.result.append(f"<span style='color:blue'>&lt;/{tag[1:]}&gt;</span>")
                else:
                    # Opening tag
                    if attributes:
                        attr_str = " ".join(f'{k}="{v}"' for k, v in attributes.items())
                        self.result.append(f"<span style='color:blue'>&lt;{tag} {attr_str}&gt;</span>")
                    else:
                        self.result.append(f"<span style='color:blue'>&lt;{tag}&gt;</span>")
                
            def add_text(self, text):
                if text.isspace():
                    self.result.append(text)
                else:
                    # Make text content bold
                    self.result.append(f"<span style='font-weight:bold'>{text}</span>")
                
            def parse(self):
                # Override parse to just collect the highlighted elements
                text = ""
                in_tag = False
                in_comment = False
                
                i = 0
                while i < len(self.body):
                    c = self.body[i]
                    
                    # Special handling for '<' and '>' to convert them to HTML entities
                    # outside of our special spans
                    if c == '<' and not in_tag and not in_comment:
                        # Check for comment start
                        if i + 3 < len(self.body) and self.body[i:i+4] == '<!--':
                            if text:
                                self.add_text(text)
                                text = ""
                            in_comment = True
                            self.result.append("<span style='color:green'>&lt;!--")
                            i += 4
                            continue
                        else:
                            # Regular tag
                            if text:
                                self.add_text(text)
                                text = ""
                            in_tag = True
                            text = ""
                    elif c == '>' and in_tag:
                        # Complete the tag
                        self.add_tag(text)
                        text = ""
                        in_tag = False
                    elif in_comment and i + 2 < len(self.body) and self.body[i:i+3] == '-->':
                        # End of comment
                        self.result.append("--&gt;</span>")
                        in_comment = False
                        i += 3
                        continue
                    else:
                        # Accumulate text
                        text += c
                    i += 1
                
                # Handle any remaining text
                if text:
                    if in_tag:
                        self.add_tag(text)
                    elif in_comment:
                        self.result.append(text + "</span>")
                    else:
                        self.add_text(text)
                        
                # Return the highlighted HTML wrapped in a pre tag to preserve formatting
                return "<pre style='white-space:pre-wrap;font-family:monospace;'>" + "".join(self.result) + "</pre>"
        
        # Use our syntax highlighter
        highlighter = SyntaxHighlighter(html_content)
        return highlighter.parse()
