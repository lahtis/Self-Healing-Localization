import json
import configparser
import tkinter as tk
import logging
from tkinter import ttk

from shl import LanguageValidator, setup_logging, get_logger, translate_text
from shl.engine.translation.cache import TranslationCache
from shl.engine.translation.exceptions import (
    TranslationError,
    LanguageNotSupportedError,
)

from ui.help_content import HELP_CONTENT
from ui.help_renderer import configure_help_text, render_html_help

# Import version info
from ui._version import __version__, __author__, __license__, __description__


POLICY_FILE = "shl-policy-config.json"
CONFIG_FILE = "ui/config.conf"
LOCALES_DIR = "ui/locales"

# Initialize logging
setup_logging(console_level="INFO")
logger = get_logger(__name__)

# ------------------------------------------------
# Policy handling
# ------------------------------------------------

def load_policy():
    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_policy(data):
    with open(POLICY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ------------------------------------------------
# UI localization
# ------------------------------------------------

class UILocalization:
    def __init__(
        self,
        source_language="en",
        target_language="en",
        locales_dir=LOCALES_DIR,
        cache_ttl=3600,
        use_glfm_lite: bool = True,
        fallback_language="en",
    ):
        self.source_language = source_language
        self.target_language = target_language
        self.locales_dir = locales_dir
        self.fallback_language = fallback_language

        self.cache = TranslationCache(ttl=cache_ttl)
        self.validator = LanguageValidator(
            base_language=source_language,
            use_lite=True,
        )

        self.translations = {}
        self._ensure_locales_dir()
        self._load_translations()

    def _ensure_locales_dir(self):
        import os

        os.makedirs(self.locales_dir, exist_ok=True)

    def _get_locale_file(self):
        import os

        return os.path.join(
            self.locales_dir,
            f"{self.target_language}.json",
        )

    def _load_translations(self):
        locale_file = self._get_locale_file()

        try:
            with open(locale_file, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.translations = {}

    def _save_translations(self):
        locale_file = self._get_locale_file()

        with open(locale_file, "w", encoding="utf-8") as f:
            json.dump(
                self.translations,
                f,
                ensure_ascii=False,
                indent=4,
            )

    def _translate_with_shl(self, text):
        cached = self.cache.get(
            text,
            self.source_language,
            self.target_language,
        )

        if cached:
            return cached

        try:
            translated = translate_text(
                text=text,
                target_lang=self.target_language,
                source_lang=self.source_language,
                placeholder_pattern=r"\{\}",
                raise_on_language_not_supported=True,
            )

            if not translated:
                return text

            self.cache.set(
                text,
                translated,
                self.source_language,
                self.target_language,                
            )

            return translated

        except LanguageNotSupportedError:
            raise

        except TranslationError:
            logger.error(f"Translation failed: {error}")
            return text

    def L(self, text):
        if self.target_language == self.source_language:
            return text

        existing = self.translations.get(text)

        if existing:
            return existing

        try:
            translated = self._translate_with_shl(text)

        except LanguageNotSupportedError:
            self.target_language = self.fallback_language
            self._load_translations()
            return text

        if translated != text:
            self.translations[text] = translated
            self._save_translations()

        return translated


# ------------------------------------------------
# Load configuration
# ------------------------------------------------

def load_language():
    config = configparser.ConfigParser()

    try:
        config.read(CONFIG_FILE, encoding="utf-8")

        language = config.get(
            "SETTINGS",
            "language",
            fallback="en",
        )

        language = language.strip().lower()

        if not language:
            return "en"

        return language

    except Exception:
        return "en"


def save_language(language):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if not config.has_section("SETTINGS"):
        config.add_section("SETTINGS")

    config.set("SETTINGS", "language", language)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        config.write(f)


# ------------------------------------------------
# Initialize policy and localization
# ------------------------------------------------

policy = load_policy()

language = load_language()

localizer = UILocalization(
    source_language="en",
    target_language=language,
    locales_dir=LOCALES_DIR,
    cache_ttl=3600,
    fallback_language="en",
)


def L(text):
    return localizer.L(text)


# ------------------------------------------------
# Main window
# ------------------------------------------------

root = tk.Tk()
root.title(L("SHL Policy Editor"))
root.geometry("1200x700")


# ------------------------------------------------
# Menu
# ------------------------------------------------

menu_bar = tk.Menu(root)


# File menu

file_menu = tk.Menu(
    menu_bar,
    tearoff=0,
)

menu_bar.add_cascade(
    label=L("File"),
    menu=file_menu,
)


# Language menu

language_menu = tk.Menu(
    menu_bar,
    tearoff=0,
)

menu_bar.add_cascade(
    label=L("Language"),
    menu=language_menu,
)


# Help menu

help_menu = tk.Menu(
    menu_bar,
    tearoff=0,
)

menu_bar.add_cascade(
    label=L("Help"),
    menu=help_menu,
)

root.config(menu=menu_bar)


# ------------------------------------------------
# Layout
# ------------------------------------------------

main_frame = tk.PanedWindow(
    root,
    orient=tk.HORIZONTAL,
)

main_frame.pack(
    fill="both",
    expand=True,
)

left_frame = tk.Frame(main_frame)

right_frame = tk.Frame(
    main_frame,
    padx=20,
    pady=20,
)

main_frame.add(
    left_frame,
    stretch="always",
)

main_frame.add(
    right_frame,
    stretch="always",
)


# ------------------------------------------------
# Treeview
# ------------------------------------------------

tree = ttk.Treeview(
    left_frame,
    columns=(
        "provider",
        "enabled",
        "priority",
        "timeout",
    ),
    show="headings",
    selectmode="browse",
)

tree.heading(
    "provider",
    text=L("Provider"),
)

tree.heading(
    "enabled",
    text=L("Enabled"),
)

tree.heading(
    "priority",
    text=L("Priority"),
)

tree.heading(
    "timeout",
    text=L("Timeout"),
)

tree.column(
    "provider",
    anchor="w",
    width=200,
)

tree.column(
    "enabled",
    anchor="center",
    width=100,
)

tree.column(
    "priority",
    anchor="center",
    width=100,
)

tree.column(
    "timeout",
    anchor="center",
    width=100,
)

tree.pack(
    fill="both",
    expand=True,
)

providers = {
    name: cfg
    for name, cfg in policy.items()
    if isinstance(cfg, dict) and "priority" in cfg
}

providers_sorted = sorted(
    providers.items(),
    key=lambda x: x[1]["priority"],
)

for name, cfg in providers_sorted:
    tree.insert(
        "",
        "end",
        iid=name,
        values=(
            name,
            cfg["enabled"],
            cfg["priority"],
            cfg["timeout"],
        ),
    )


# ------------------------------------------------
# Drag and drop
# ------------------------------------------------

dragging_item = None


def on_button_press(event):
    global dragging_item

    dragging_item = tree.identify_row(event.y)


def on_motion(event):
    global dragging_item

    if dragging_item:
        target = tree.identify_row(event.y)

        if target and target != dragging_item:
            items = list(tree.get_children())

            tree.move(
                dragging_item,
                "",
                items.index(target),
            )


def on_button_release(event):
    global dragging_item

    if dragging_item:
        items = list(tree.get_children())

        for idx, iid in enumerate(items):
            policy[iid]["priority"] = idx + 1

            tree.item(
                iid,
                values=(
                    iid,
                    policy[iid]["enabled"],
                    policy[iid]["priority"],
                    policy[iid]["timeout"],
                ),
            )

        save_policy(policy)

    dragging_item = None


tree.bind(
    "<ButtonPress-1>",
    on_button_press,
)

tree.bind(
    "<B1-Motion>",
    on_motion,
)

tree.bind(
    "<ButtonRelease-1>",
    on_button_release,
)


# ------------------------------------------------
# Editor pane
# ------------------------------------------------

provider_editor_label = tk.Label(
    right_frame,
    text=L("Provider Editor"),
    font=("Arial", 18, "bold"),
)

provider_editor_label.pack(
    anchor="nw",
    pady=(0, 20),
)


current_provider = None


# ------------------------------------------------
# Enabled / Priority
# ------------------------------------------------

enabled_priority_frame = tk.Frame(
    right_frame,
)

enabled_priority_frame.pack(
    anchor="nw",
    pady=(0, 15),
)


enabled_label = tk.Label(
    enabled_priority_frame,
    text=L("Enabled"),
    font=("Arial", 12),
)

enabled_label.pack(
    side="left",
)


enabled_var = tk.BooleanVar()

tk.Checkbutton(
    enabled_priority_frame,
    variable=enabled_var,
    font=("Arial", 12),
).pack(
    side="left",
    padx=(5, 20),
)


priority_label = tk.Label(
    enabled_priority_frame,
    text=L("Priority:"),
    font=("Arial", 12),
)

priority_label.pack(
    side="left",
)


priority_var = tk.IntVar()

tk.Label(
    enabled_priority_frame,
    textvariable=priority_var,
    font=("Arial", 12, "bold"),
).pack(
    side="left",
    padx=(5, 0),
)


# ------------------------------------------------
# Timeout
# ------------------------------------------------

timeout_label = tk.Label(
    right_frame,
    text=L("Timeout"),
    font=("Arial", 12),
)

timeout_label.pack(
    anchor="nw",
)


timeout_var = tk.IntVar()

tk.Entry(
    right_frame,
    textvariable=timeout_var,
    width=25,
    font=("Arial", 12),
).pack(
    anchor="nw",
    pady=(0, 20),
)


# ------------------------------------------------
# Allow tags
# ------------------------------------------------

allow_label = tk.Label(
    right_frame,
    text=L("Allow Tags"),
    font=("Arial", 12),
)

allow_label.pack(
    anchor="nw",
)


allow_box = tk.Listbox(
    right_frame,
    selectmode="multiple",
    height=8,
    width=40,
    font=("Arial", 12),
)

allow_box.pack(
    anchor="nw",
    pady=(0, 20),
)


# ------------------------------------------------
# Deny tags
# ------------------------------------------------

deny_label = tk.Label(
    right_frame,
    text=L("Deny Tags"),
    font=("Arial", 12),
)

deny_label.pack(
    anchor="nw",
)


deny_box = tk.Listbox(
    right_frame,
    selectmode="multiple",
    height=8,
    width=40,
    font=("Arial", 12),
)

deny_box.pack(
    anchor="nw",
    pady=(0, 20),
)


# ------------------------------------------------
# Provider selection
# ------------------------------------------------

def on_select(event):
    global current_provider

    selection = tree.selection()

    if not selection:
        return

    item = selection[0]

    current_provider = item

    cfg = policy[item]

    enabled_var.set(
        cfg["enabled"]
    )

    priority_var.set(
        cfg["priority"]
    )

    timeout_var.set(
        cfg["timeout"]
    )

    allow_box.delete(
        0,
        "end",
    )

    for tag in cfg.get("allow", []):
        allow_box.insert(
            "end",
            tag,
        )

        allow_box.selection_set(
            "end",
        )

    deny_box.delete(
        0,
        "end",
    )

    for tag in cfg.get("deny", []):
        deny_box.insert(
            "end",
            tag,
        )

        deny_box.selection_set(
            "end",
        )


tree.bind(
    "<<TreeviewSelect>>",
    on_select,
)


# ------------------------------------------------
# Save changes
# ------------------------------------------------

def save_changes():
    if not current_provider:
        return

    cfg = policy[current_provider]

    cfg["enabled"] = enabled_var.get()

    cfg["timeout"] = timeout_var.get()

    cfg["allow"] = [
        allow_box.get(i)
        for i in allow_box.curselection()
    ]

    cfg["deny"] = [
        deny_box.get(i)
        for i in deny_box.curselection()
    ]

    save_policy(policy)

    tree.item(
        current_provider,
        values=(
            current_provider,
            cfg["enabled"],
            cfg["priority"],
            cfg["timeout"],
        ),
    )


# ------------------------------------------------
# Help window
# ------------------------------------------------


def localize_help_content():
    """Localize the complete HTML help content through UILocalization."""
    if (
        localizer.target_language == "en"
        or localizer.target_language.startswith("en")
    ):
        return HELP_CONTENT

    try:
        return localizer.L(HELP_CONTENT)

    except LanguageNotSupportedError:
        logger.error(
            "Language not supported for help content: %s",
            localizer.target_language,
        )
        return HELP_CONTENT

    except TranslationError as error:
        logger.error(
            "Translation failed for help content: %s",
            error,
        )
        return HELP_CONTENT


def show_help():
    help_window = tk.Toplevel(root)
    help_window.title(L("Help"))
    help_window.geometry("800x600")

    help_text = tk.Text(
        help_window,
        wrap="word",
        padx=20,
        pady=20,
    )

    help_text.pack(
        fill="both",
        expand=True,
    )

    configure_help_text(help_text)

    render_html_help(
        help_text,
        localize_help_content(),
    )

# ------------------------------------------------
# About window
# ------------------------------------------------

def show_about():
    about_window = tk.Toplevel(root)
    about_window.title(L("About"))
    about_window.geometry("500x300")
    about_window.resizable(False, False)

    ttk.Label(
        about_window,
        text=__description__,
        font=("Arial", 14, "bold"),
    ).pack(
        pady=(30, 15),
    )

    ttk.Label(
        about_window,
        text=f"{L('Version')}: {__version__}",
        font=("Arial", 11),
    ).pack(
        pady=3,
    )

    ttk.Label(
        about_window,
        text=f"{L('Author')}: {__author__}",
        font=("Arial", 11),
    ).pack(
        pady=3,
    )

    ttk.Label(
        about_window,
        text=f"{L('License')}: {__license__}",
        font=("Arial", 11),
    ).pack(
        pady=3,
    )


# ------------------------------------------------
# Language switching
# ------------------------------------------------

def update_ui_language():
    root.title(L("SHL Policy Editor"))

    file_menu.entryconfigure(
        0,
        label=L("Save"),
    )

    file_menu.entryconfigure(
        2,
        label=L("Exit"),
    )

    help_menu.entryconfigure(
        0,
        label=L("Help"),
    )

    help_menu.entryconfigure(
        1,
        label=L("About"),
    )

    tree.heading(
        "provider",
        text=L("Provider"),
    )

    tree.heading(
        "enabled",
        text=L("Enabled"),
    )

    tree.heading(
        "priority",
        text=L("Priority"),
    )

    tree.heading(
        "timeout",
        text=L("Timeout"),
    )

    provider_editor_label.config(
        text=L("Provider Editor"),
    )

    enabled_label.config(
        text=L("Enabled"),
    )

    priority_label.config(
        text=L("Priority:"),
    )

    timeout_label.config(
        text=L("Timeout"),
    )

    allow_label.config(
        text=L("Allow Tags"),
    )

    deny_label.config(
        text=L("Deny Tags"),
    )

    save_button.config(
        text=L("Save"),
    )

    # Rebuild the main menu so cascade labels are localized.
    menu_bar.delete(0, "end")

    menu_bar.add_cascade(
        label=L("File"),
        menu=file_menu,
    )

    menu_bar.add_cascade(
        label=L("Language"),
        menu=language_menu,
    )

    menu_bar.add_cascade(
        label=L("Help"),
        menu=help_menu,
    )

def set_ui_language(language):
    if language == localizer.target_language:
        return

    localizer.target_language = language
    localizer._load_translations()

    save_language(language)

    update_ui_language()


# ------------------------------------------------
# Menu commands
# ------------------------------------------------

file_menu.add_command(
    label=L("Save"),
    command=save_changes,
)

file_menu.add_separator()

file_menu.add_command(
    label=L("Exit"),
    command=root.destroy,
)


language_menu.add_command(
    label="English",
    command=lambda: set_ui_language("en"),
)

language_menu.add_command(
    label="Suomi",
    command=lambda: set_ui_language("fi"),
)


help_menu.add_command(
    label=L("Help"),
    command=show_help,
)

help_menu.add_command(
    label=L("About"),
    command=show_about,
)


# ------------------------------------------------
# Save button
# ------------------------------------------------

save_button = tk.Button(
    right_frame,
    text=L("Save"),
    font=("Arial", 14),
    width=15,
    command=save_changes,
)

save_button.pack(
    anchor="nw",
    pady=20,
)


# ------------------------------------------------
# Start application
# ------------------------------------------------

root.mainloop()
