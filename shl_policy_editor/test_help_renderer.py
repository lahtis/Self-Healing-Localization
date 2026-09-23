import tkinter as tk
from tkinter import scrolledtext

from ui.help_renderer import configure_help_text, render_html_help


TEST_HTML = """
<h1>SHL Policy Editor</h1>

<p>
This is a test help page for the SHL Policy Editor.
</p>

<h2>Provider priority</h2>

<p>
Provider priority determines the order in which translation providers are used.
</p>

<ul>
<li><strong>Enabled</strong> controls whether a provider can be used.</li>
<li><strong>Priority</strong> controls the provider order.</li>
<li><strong>Timeout</strong> controls the maximum request time.</li>
</ul>

<h2>Formatting</h2>

<p>
This paragraph contains <strong>bold text</strong>,
<em>italic text</em>, and <code>code text</code>.
</p>

<hr>

<h3>End of test</h3>

<p>
If this page looks correct, the HTML renderer is working.
</p>
"""


root = tk.Tk()
root.title("HTML Renderer Test")
root.geometry("800x600")

text = scrolledtext.ScrolledText(
    root,
    wrap="word",
    padx=20,
    pady=20,
)

text.pack(
    fill="both",
    expand=True,
)

configure_help_text(text)
render_html_help(text, TEST_HTML)

root.mainloop()
