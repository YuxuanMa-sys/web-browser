# main.py
import sys
from url import URL
from browser import Browser
import tkinter

if __name__ == '__main__':
    # If no URL is provided, default to about:blank.
    url_str = sys.argv[1] if len(sys.argv) > 1 else "about:blank"
    Browser().load(URL(url_str))
    tkinter.mainloop()
