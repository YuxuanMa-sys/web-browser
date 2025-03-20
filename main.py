import socket
import ssl
import os
import urllib.parse

# Global connection pool for keep-alive sockets: keys are (scheme, host, port)
connection_pool = {}

def read_line(sock):
    """Read bytes from the socket until a CRLF is encountered."""
    line = b""
    while not line.endswith(b"\r\n"):
        chunk = sock.recv(1)
        if not chunk:
            break
        line += chunk
    return line.decode("utf-8")

def read_exact(sock, n):
    """Read exactly n bytes from the socket."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data

class URL:
    def __init__(self, url):
        self.scheme, rest = url.split("://", 1)
        # Support view-source scheme.
        if self.scheme == "view-source":
            self.view_source = True
            self.inner_url = rest
            self.inner = URL(self.inner_url)
            return
        else:
            self.view_source = False

        assert self.scheme in ["http", "https", "file", "data"]

        if self.scheme == "data":
            # For data URLs, the format is: data:[<mediatype>][;base64],<data>
            meta, data = rest.split(",", 1)
            self.data = urllib.parse.unquote(data)
            return

        if self.scheme == "file":
            # For file URLs, treat the remainder as a file path.
            if not rest.startswith("/"):
                rest = "/" + rest
            self.path = rest
            return

        # For HTTP and HTTPS:
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if "/" not in rest:
            rest = rest + "/"

        self.host, path = rest.split("/", 1)
        self.path = "/" + path

        # Handle custom port if provided.
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def request(self):
        # Handle view-source by delegating to the inner URL.
        if self.view_source:
            return self.inner.request()
        # Handle data URLs.
        if self.scheme == "data":
            return self.data
        # Handle file URLs.
        if self.scheme == "file":
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()

        # For HTTP/HTTPS, attempt to reuse an existing connection.
        key = (self.scheme, self.host, self.port)
        if key in connection_pool:
            s = connection_pool[key]
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            s.connect((self.host, self.port))
            if self.scheme == "https":
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
            connection_pool[key] = s

        # Build an HTTP/1.1 request with keep-alive.
        headers = {
            "Host": self.host,
            "Connection": "keep-alive",
            "User-Agent": "MySimpleBrowser/1.0",
        }
        request_str = "GET {} HTTP/1.1\r\n".format(self.path)
        for key_hdr, value in headers.items():
            request_str += "{}: {}\r\n".format(key_hdr, value)
        request_str += "\r\n"

        s.send(request_str.encode("utf-8"))

        # Read the status line.
        statusline = read_line(s)
        try:
            version, status, explanation = statusline.split(" ", 2)
        except ValueError:
            raise Exception("Malformed status line: " + statusline)

        # Read headers until an empty line.
        response_headers = {}
        while True:
            line = read_line(s)
            if line in ("\r\n", "\n", ""):
                break
            if ": " in line:
                header, value = line.split(": ", 1)
                response_headers[header.casefold()] = value.strip()

        # Ensure we have a Content-Length header.
        if "content-length" not in response_headers:
            raise Exception("No Content-Length header in response.")
        content_length = int(response_headers["content-length"])

        # Read exactly the number of bytes specified.
        body_bytes = read_exact(s, content_length)
        content = body_bytes.decode("utf-8", errors="replace")
        # Do NOT close the socket to allow for reuse.
        return content

def show(body):
    # Process and display the response by stripping HTML tags,
    # and decode &lt; and &gt; entities to < and >.
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
        i += 1
    text = "".join(result)
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    print(text, end="")

def load(url):
    content = url.request()
    # For view-source URLs, output the raw content.
    if hasattr(url, "view_source") and url.view_source:
        print(content, end="")
    else:
        show(content)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        # If no URL is provided, open a default file (e.g., test.html).
        default_file = os.path.abspath("test.html")
        url = "file://" + default_file
    else:
        url = sys.argv[1]
    load(URL(url))
