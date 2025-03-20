import socket
import ssl
import os
import urllib.parse

# A global pool for persistent connections, keyed by (scheme, host, port)
connection_pool = {}


class URL:
    def __init__(self, url):
        # 1) Check for "view-source:" prefix first.
        if url.startswith("view-source:"):
            self.view_source = True
            inner_url = url[len("view-source:"):]
            self.inner = URL(inner_url)
            return
        else:
            self.view_source = False

        # 2) Parse the normal scheme://... format.
        self.scheme, rest = url.split("://", 1)
        assert self.scheme in ["http", "https", "file", "data"]

        if self.scheme == "data":
            # For data URLs: data:[<mediatype>][;base64],<data>
            meta, data = rest.split(",", 1)
            self.data = urllib.parse.unquote(data)
            return

        if self.scheme == "file":
            # For file URLs, treat the remainder as a file path.
            if not rest.startswith("/"):
                rest = "/" + rest
            self.path = rest
            return

        # For HTTP and HTTPS, figure out host, port, and path.
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if "/" not in rest:
            rest += "/"

        self.host, path = rest.split("/", 1)
        self.path = "/" + path

        # If the host contains a port, parse it out.
        if ":" in self.host:
            self.host, port_str = self.host.split(":", 1)
            self.port = int(port_str)

    def request(self):
        # 1) If this is a view-source URL, delegate to the inner URL.
        if self.view_source:
            return self.inner.request()

        # 2) data URL
        if self.scheme == "data":
            return self.data

        # 3) file URL
        if self.scheme == "file":
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()

        # 4) HTTP/HTTPS
        # Check if we already have a socket for this (scheme, host, port).
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

        # Build and send an HTTP/1.1 request with keep-alive.
        headers = {
            "Host": self.host,
            "Connection": "keep-alive",
            "User-Agent": "MySimpleBrowser/1.0",
        }
        request_data = f"GET {self.path} HTTP/1.1\r\n"
        for hdr, val in headers.items():
            request_data += f"{hdr}: {val}\r\n"
        request_data += "\r\n"
        s.sendall(request_data.encode("utf-8"))

        # We’ll use a file-like object in binary mode to ensure exact byte reading.
        response = s.makefile("rb", newline=None)

        # Read the status line (e.g. b"HTTP/1.1 200 OK\r\n")
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

        # Read headers until an empty line.
        response_headers = {}
        while True:
            line = response.readline()
            if not line or line in (b"\r\n", b"\n"):
                break
            line_str = line.decode("utf-8", errors="replace")
            if ": " in line_str:
                header, value = line_str.split(": ", 1)
                response_headers[header.lower()] = value.strip()

        # Make sure we have a Content-Length so we know how many bytes to read.
        if "content-length" not in response_headers:
            raise Exception("No Content-Length header in response.")
        length = int(response_headers["content-length"])

        # Read exactly 'length' bytes from the body.
        body = response.read(length)
        content = body.decode("utf-8", errors="replace")

        # IMPORTANT: Do not close the socket => keep-alive
        # response.close() also is not called, so the socket remains open for reuse.

        return content


def show(body):
    # Remove HTML tags, decode &lt; and &gt; to < and >.
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
    body = url.request()
    # If view-source, print the raw HTML source instead of stripping tags.
    if getattr(url, "view_source", False):
        print(body, end="")
    else:
        show(body)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        url_str = "http://example.com"
    else:
        url_str = sys.argv[1]

    # Make multiple requests in the same process to observe connection reuse.
    for i in range(2):
        print(f"\nRequest #{i + 1}")
        load(URL(url_str))
        print("\n--- Request complete ---\n")

