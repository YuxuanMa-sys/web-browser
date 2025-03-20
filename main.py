import socket
import ssl
import os

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file"]

        if self.scheme == "file":
            # For file URLs, treat the remainder as a file path.
            # If the path isn't absolute (i.e. doesn't start with '/'), add a leading slash.
            if not url.startswith("/"):
                url = "/" + url
            self.path = url
            return

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if "/" not in url:
            url = url + "/"

        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # if ports are given in the host (e.g. example.com:8080)
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def request(self):
        # Handle file scheme separately.
        if self.scheme == "file":
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()

        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        s.connect((self.host, self.port))

        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # Build headers dictionary for easy future modifications.
        headers = {
            "Host": self.host,
            "Connection": "close",
            "User-Agent": "MySimpleBrowser/1.0",
        }
        # Construct the HTTP request using HTTP/1.1.
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
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")


def load(url):
    body = url.request()
    show(body)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        # If no URL is provided, open a default file (e.g., test.html in the current directory)
        default_file = os.path.abspath("test.html")
        url = "file://" + default_file
    else:
        url = sys.argv[1]
    load(URL(url))
