import tkinter as tk
from html.parser import HTMLParser


class HelpHTMLRenderer(HTMLParser):
    """Render basic HTML content into a Tkinter Text widget."""

    def __init__(self, text_widget):
        super().__init__(convert_charrefs=True)
        self.text_widget = text_widget
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag in ("h1", "h2", "h3"):
            self._insert_block_start()

            self.tag_stack.append(tag)
            self.text_widget.insert("end", "", tag)

        elif tag == "p":
            self._insert_block_start()
            self.tag_stack.append(tag)

        elif tag in ("strong", "b"):
            self.tag_stack.append("bold")

        elif tag in ("em", "i"):
            self.tag_stack.append("italic")

        elif tag == "code":
            self.tag_stack.append("code")

        elif tag == "li":
            self._insert_block_start()
            self.text_widget.insert("end", "• ")
            self.tag_stack.append("li")

        elif tag == "br":
            self.text_widget.insert("end", "\n")

        elif tag == "hr":
            self._insert_block_start()
            self.text_widget.insert("end", "────────────────────\n")

        elif tag in ("ul", "ol"):
            self._insert_block_start()
            self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in ("h1", "h2", "h3"):
            self._remove_tag(tag)
            self.text_widget.insert("end", "\n")

        elif tag == "p":
            self._remove_tag("p")
            self.text_widget.insert("end", "\n")

        elif tag in ("strong", "b"):
            self._remove_tag("bold")

        elif tag in ("em", "i"):
            self._remove_tag("italic")

        elif tag == "code":
            self._remove_tag("code")

        elif tag == "li":
            self._remove_tag("li")
            self.text_widget.insert("end", "\n")

        elif tag in ("ul", "ol"):
            self._remove_tag(tag)
            self.text_widget.insert("end", "\n")

    def handle_data(self, data):
        if not data:
            return

        active_tags = self._active_text_tags()

        self.text_widget.insert(
            "end",
            data,
            tuple(active_tags),
        )

    def _active_text_tags(self):
        tags = []

        for tag in self.tag_stack:
            if tag in ("h1", "h2", "h3"):
                tags.append(tag)
            elif tag in ("bold", "italic", "code"):
                tags.append(tag)

        return tags

    def _remove_tag(self, tag):
        for index in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[index] == tag:
                del self.tag_stack[index]
                return

    def _insert_block_start(self):
        if self.text_widget.index("end-1c") != "1.0":
            self.text_widget.insert("end", "\n")


def configure_help_text(text_widget):
    """Configure visual styles for the help Text widget."""

    text_widget.tag_configure(
        "h1",
        font=("TkDefaultFont", 18, "bold"),
        spacing3=8,
    )

    text_widget.tag_configure(
        "h2",
        font=("TkDefaultFont", 14, "bold"),
        spacing1=8,
        spacing3=4,
    )

    text_widget.tag_configure(
        "h3",
        font=("TkDefaultFont", 12, "bold"),
        spacing1=6,
        spacing3=3,
    )

    text_widget.tag_configure(
        "bold",
        font=("TkDefaultFont", 10, "bold"),
    )

    text_widget.tag_configure(
        "italic",
        font=("TkDefaultFont", 10, "italic"),
    )

    text_widget.tag_configure(
        "code",
        font=("TkFixedFont", 10),
    )


def render_html_help(text_widget, html_content):
    """Render HTML help content into a Tkinter Text widget."""

    text_widget.config(state="normal")
    text_widget.delete("1.0", "end")

    parser = HelpHTMLRenderer(text_widget)
    parser.feed(html_content)
    parser.close()

    text_widget.config(state="disabled")


