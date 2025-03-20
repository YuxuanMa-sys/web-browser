import socket
import ssl
import os
import urllib.parse

class URL:
    def __init__(self, url):
        # Check for the 'view-source:' prefix manually
        if url.startswith("view-source:"):
            self.view_source = True
            inner_url = url[len("view-source:"):]  # everything after 'view-source:'
            self.inner = URL(inner_url)
            return
        else:
            self.view_source = False

        # From here on, parse the usual schemes: http, https, file, data
        self.scheme, rest = url.split("://", 1)
        assert self.scheme in ["http", "https", "file", "data"]

        if self.scheme == "data":
            # For data URLs, the format is: data:[<mediatype>][;base64],<data>
            meta, data = rest.split(",", 1)
            # Decode percent-encoded data (if any)
            self.data = urllib.parse.unquote(data)
            return

        if self.scheme == "file":
            # For file URLs, treat the remainder as a file path.
            if not rest.startswith("/"):
                rest = "/" + rest
            self.path = rest
            return

        # For HTTP and HTTPS schemes:
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
        if self.view_source:
            # Delegate to the inner URL.
            return self.inner.request()
        if self.scheme == "data":
            return self.data
        if self.scheme == "file":
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        s.connect((self.host, self.port))

        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # Build HTTP/1.1 request with custom headers.
        headers = {
            "Host": self.host,
            "Connection": "close",
            "User-Agent": "MySimpleBrowser/1.0",
        }
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        for key, value in headers.items():
            request += "{}: {}\r\n".format(key, value)
        request += "\r\n"

        s.send(request.encode("utf-8"))

        response = s.makefile("r", encoding="utf-8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(": ", 1)
            response_headers[header.casefold()] = value.strip()

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        content = response.read()
        s.close()
        return content

def show(body):
    # Extract text content by removing HTML tags and decoding certain entities.
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
    # For view-source URLs, print the raw HTML source.
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
