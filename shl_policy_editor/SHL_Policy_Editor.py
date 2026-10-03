import json
import configparser
import tkinter as tk
import logging
from tkinter import ttk

from shl.config import get_config_value
from shl import (
    LanguageValidator,
    setup_logging,
    get_logger,
    translate_text,
)
from shl.engine.translation.cache import TranslationCache
from shl.engine.translation.exceptions import (
    TranslationError,
    LanguageNotSupportedError,
)
from shl.config.provider_capabilities import (
    PROVIDER_CAPABILITIES,
    SHL_WHITELIST,
    PROVIDER_ALLOW,
    PROVIDER_DENY,
)
from shl.language_parser import LanguageParser

from .help_content import HELP_CONTENT
from .help_renderer import configure_help_text, render_html_help

# Import version info
from ._version import (
    __version__,
    __author__,
    __license__,
    __description__,
)


POLICY_FILE = "shl-policy-config.json"
CONFIG_FILE = "shl_policy_editor/config.conf"
LOCALES_DIR = "shl_policy_editor/locales"
DEFAULT_RETRY = 2
DEFAULT_RETRY_DELAY = 1.0

# ------------------------------------------------
# Capability catalog
# ------------------------------------------------
#
# These are display names only.
#
# Capability information itself belongs to the main
# provider settings.
#
# The Policy Editor only displays this information.
# The user cannot modify provider capabilities,
# SHL whitelist rules, provider allow rules,
# or provider deny rules.
#
POLICY_TAGS = (
    "html",
    "glossary",
    "formality",
    "contextual_suggestions",
    "honorific",
    "language_detection",
    "document_translation",
    "website_translation",
    "batch_translation",
)


# Initialize logging
setup_logging(console_level="INFO")
logger = get_logger(__name__)


# ------------------------------------------------
# Policy handling
# ------------------------------------------------
def load_policy():
    with open(
        POLICY_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_policy(data):
    with open(
        POLICY_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            indent=4,
        )


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

        self.cache = TranslationCache(
            ttl=cache_ttl,
            max_size=get_config_value("cache.max_size"),
            persist=get_config_value("cache.cache_persist"),
            persist_path=get_config_value(
                "cache.cache_persist_path"
            ),
        )

        self.validator = LanguageValidator(
            base_language=source_language,
            use_lite=True,
        )

        self.parser = LanguageParser(
            validator=self.validator
        )

        self.translations = {}

        # Failed translations are tracked per language.
        #
        # Example:
        # {
        #     "fi": {"Provider", "Enabled"},
        #     "sv": {"Provider"}
        # }
        #
        # This prevents the same failed translation from
        # being requested repeatedly while still allowing
        # another target language to try independently.
        self.failed_translations = {}

        self._ensure_locales_dir()
        self._load_translations()

    def _ensure_locales_dir(self):
        import os

        os.makedirs(
            self.locales_dir,
            exist_ok=True,
        )

    def _get_locale_file(self):
        import os

        return os.path.join(
            self.locales_dir,
            f"{self.target_language}.json",
        )

    def _load_translations(self):
        locale_file = self._get_locale_file()

        try:
            with open(
                locale_file,
                "r",
                encoding="utf-8",
            ) as f:
                self.translations = json.load(f)

        except (
            FileNotFoundError,
            json.JSONDecodeError,
        ):
            self.translations = {}

    def _save_translations(self):
        locale_file = self._get_locale_file()

        with open(
            locale_file,
            "w",
            encoding="utf-8",
        ) as f:
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
                placeholder_pattern=r"\{[^}]*\}|\[[^\]]*\]",
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

        except TranslationError as error:
            logger.error(
                f"Translation failed: {error}"
            )
            return text

    def L(self, text):
        if not text:
            return text

        # Normalize both languages to ISO 639-3.
        try:
            source_iso = self.parser.normalize(
                self.source_language
            )
            target_iso = self.parser.normalize(
                self.target_language
            )

        except (
            ValueError,
            TypeError,
        ):
            source_iso = self.source_language
            target_iso = self.target_language

        # Same language -> do not translate.
        if source_iso == target_iso:
            return text

        existing = self.translations.get(text)

        if existing:
            return existing

        # Get the failed-translation set for the current
        # target language.
        failed = self.failed_translations.setdefault(
            self.target_language,
            set(),
        )

        # Do not retry the same failed translation
        # repeatedly during this application session.
        if text in failed:
            return text

        try:
            translated = self._translate_with_shl(text)

        except LanguageNotSupportedError:
            failed.add(text)
            return text

        except TranslationError as error:
            failed.add(text)

            logger.error(
                f"Translation failed: {error}"
            )

            return text

        # SHL may return the original text when no
        # translation was produced.
        if not translated or translated == text:
            failed.add(text)
            return text

        self.translations[text] = translated
        self._save_translations()

        return translated


# ------------------------------------------------
# Load configuration
# ------------------------------------------------
def load_language():
    config = configparser.ConfigParser()

    try:
        config.read(
            CONFIG_FILE,
            encoding="utf-8",
        )

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

    config.read(
        CONFIG_FILE,
        encoding="utf-8",
    )

    if not config.has_section("SETTINGS"):
        config.add_section("SETTINGS")

    config.set(
        "SETTINGS",
        "language",
        language,
    )

    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8",
    ) as f:
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

root.title(
    L("SHL Policy Editor")
)

root.geometry(
    "1025x600"
)


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


root.config(
    menu=menu_bar
)


# ------------------------------------------------
# Layout
# ------------------------------------------------
#
# Three columns:
#
#   1. VIEW / MENU
#   2. PROVIDER EDITOR
#   3. PROVIDER CAPABILITIES
#
# The same Provider Editor is used for both
# Translation and Detection.
#
# Translation uses:
#     enabled
#     priority
#
# Detection uses:
#     detection_enabled
#     detection_priority
#
# The right-side capabilities panel remains
# independent from the selected view.
# ------------------------------------------------
main_frame = tk.PanedWindow(
    root,
    orient=tk.HORIZONTAL,
)

main_frame.pack(
    fill="both",
    expand=True,
)


# ------------------------------------------------
# Left: View / Menu
# ------------------------------------------------
view_frame = tk.Frame(
    main_frame,
    padx=10,
    pady=10,
)


# ------------------------------------------------
# Center: Provider Editor
# ------------------------------------------------
center_frame = tk.Frame(
    main_frame,
    padx=20,
    pady=20,
)


# ------------------------------------------------
# Right: Provider Capabilities
# ------------------------------------------------
right_frame = tk.Frame(
    main_frame,
    padx=20,
    pady=20,
)


main_frame.add(
    view_frame,
    stretch="always",
    minsize=220,
)

main_frame.add(
    center_frame,
    stretch="always",
    minsize=450,
)

main_frame.add(
    right_frame,
    stretch="always",
    minsize=450,
)


# ------------------------------------------------
# View state
# ------------------------------------------------
VIEW_TRANSLATION = "Translation"
VIEW_DETECTION = "Language detection"
VIEW_MEMORY = "Memory"

current_view = VIEW_TRANSLATION


# ------------------------------------------------
# View / Menu
# ------------------------------------------------
view_label = tk.Label(
    view_frame,
    text=L("View"),
    font=("Arial", 12, "bold"),
)

view_label.pack(
    anchor="nw",
    pady=(0, 8),
)


view_var = tk.StringVar()


view_menu = ttk.Combobox(
    view_frame,
    textvariable=view_var,
    state="readonly",
)

view_menu.pack(
    fill="x",
    pady=(0, 15),
)


def view_labels():
    return (
        L("Translation"),
        L("Detection"),
        L("Memory"),
    )


view_menu["values"] = view_labels()
view_menu.current(0)


# ------------------------------------------------
# Treeview
# ------------------------------------------------
tree = ttk.Treeview(
    center_frame,
    columns=(
        "provider",
        "enabled",
        "priority",
        "timeout",
        "retry",
        "retry_delay",
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

tree.heading(
    "retry",
    text=L("Retry"),
)

tree.heading(
    "retry_delay",
    text=L("Retry delay"),
)


tree.column(
    "provider",
    anchor="w",
    width=180,
    minwidth=160,
    stretch=True,
)

tree.column(
    "enabled",
    anchor="center",
    width=80,
    minwidth=70,
    stretch=False,
)

tree.column(
    "priority",
    anchor="center",
    width=140,
    minwidth=120,
    stretch=True,
)

tree.column(
    "timeout",
    anchor="center",
    width=90,
    minwidth=80,
    stretch=True,
)

tree.column(
    "retry",
    anchor="center",
    width=80,
    minwidth=70,
    stretch=True,
)

tree.column(
    "retry_delay",
    anchor="center",
    width=100,
    minwidth=90,
    stretch=True,
)

tree.pack(
    fill="both",
    expand=True,
)


# ------------------------------------------------
# Provider data
# ------------------------------------------------
providers = policy.get(
    "providers",
    {}
)


# Normalize missing fields so every provider has
# the required common keys.
#
# detection_enabled and detection_priority are
# intentionally separate from translation settings.
for name, cfg in providers.items():
    if not isinstance(cfg, dict):
        providers[name] = cfg = {}

    cfg.setdefault(
        "enabled",
        False,
    )

    cfg.setdefault(
        "detection_enabled",
        False,
    )

    cfg.setdefault(
        "priority",
        999,
    )

    cfg.setdefault(
        "detection_priority",
        None,
    )

    cfg.setdefault(
        "timeout",
        30,
    )

    cfg.setdefault(
        "retry",
        DEFAULT_RETRY,
    )

    cfg.setdefault(
        "retry_delay",
        DEFAULT_RETRY_DELAY,
    )


# ------------------------------------------------
# Provider view helpers
# ------------------------------------------------
def active_priority_key():
    """
    Return the priority field used by the active view.
    """
    if current_view == VIEW_DETECTION:
        return "detection_priority"

    return "priority"


def active_enabled_key():
    """
    Return the enabled field used by the active view.
    """
    if current_view == VIEW_DETECTION:
        return "detection_enabled"

    return "enabled"


def active_priority_label():
    """
    Return the localized priority label used by
    the active provider view.
    """
    if current_view == VIEW_DETECTION:
        return L("Detection Priority")

    return L("Priority")


def provider_priority(provider):
    """
    Return the priority for the active provider view.
    """
    cfg = providers.get(
        provider,
        {},
    )

    return cfg.get(
        active_priority_key()
    )


def provider_visible_in_current_view(name, cfg):
    """
    Return whether a provider belongs to the active
    provider view.

    Translation providers use 'priority'.

    Detection providers use 'detection_priority'.

    Memory is handled separately.
    """
    if current_view == VIEW_TRANSLATION:
        return cfg.get("priority") is not None

    if current_view == VIEW_DETECTION:
        return cfg.get("detection_priority") is not None

    return False


# ------------------------------------------------
# Provider list
# ------------------------------------------------
def refresh_provider_tree():
    """
    Rebuild the provider Treeview according to the
    currently selected view.
    """
    tree.selection_remove(
        tree.selection()
    )

    for item in tree.get_children():
        tree.delete(item)

    if current_view == VIEW_MEMORY:
        return

    priority_key = active_priority_key()
    enabled_key = active_enabled_key()

    visible = []

    for name, cfg in providers.items():
        if not provider_visible_in_current_view(
            name,
            cfg,
        ):
            continue

        priority = cfg.get(
            priority_key
        )

        if priority is None:
            continue

        visible.append(
            (
                name,
                cfg,
                priority,
            )
        )

    visible.sort(
        key=lambda item: item[2]
    )

    for name, cfg, priority in visible:
        tree.insert(
            "",
            "end",
            iid=name,
            values=(
                name,
                cfg.get(
                    enabled_key,
                    False,
                ),
                priority,
                cfg.get(
                    "timeout",
                    30,
                ),
                cfg.get(
                    "retry",
                    DEFAULT_RETRY,
                ),
                cfg.get(
                    "retry_delay",
                    DEFAULT_RETRY_DELAY,
                ),
            ),
        )

    tree.heading(
        "priority",
        text=active_priority_label(),
    )


# Initial provider list
refresh_provider_tree()


# ------------------------------------------------
# Drag and drop
# ------------------------------------------------
dragging_item = None
dragging_target = None


def on_button_press(event):
    global dragging_item
    global dragging_target

    if current_view == VIEW_MEMORY:
        return

    dragging_item = tree.identify_row(
        event.y
    )

    dragging_target = None


def on_motion(event):
    global dragging_target

    if current_view == VIEW_MEMORY:
        return

    if not dragging_item:
        return

    target = tree.identify_row(
        event.y
    )

    if not target or target == dragging_item:
        return

    items = list(
        tree.get_children()
    )

    try:
        target_index = items.index(
            target
        )
    except ValueError:
        return

    current_index = items.index(
        dragging_item
    )

    if target_index == current_index:
        return

    tree.move(
        dragging_item,
        "",
        target_index,
    )

    dragging_target = target


def on_button_release(event):
    global dragging_item
    global dragging_target

    if current_view == VIEW_MEMORY:
        dragging_item = None
        dragging_target = None
        return

    if not dragging_item:
        return

    items = list(
        tree.get_children()
    )

    priority_key = active_priority_key()

    for idx, iid in enumerate(items):
        providers[iid][priority_key] = idx + 1

    refresh_provider_tree()

    save_policy(policy)

    dragging_item = None
    dragging_target = None


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
# Provider Editor
# ------------------------------------------------
provider_editor_label = tk.Label(
    center_frame,
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
    center_frame,
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
    center_frame,
    text=L("Timeout"),
    font=("Arial", 12),
)

timeout_label.pack(
    anchor="nw",
)


timeout_var = tk.IntVar()


tk.Entry(
    center_frame,
    textvariable=timeout_var,
    width=25,
    font=("Arial", 12),
).pack(
    anchor="nw",
    pady=(0, 20),
)


# ------------------------------------------------
# Retry
# ------------------------------------------------
retry_label = tk.Label(
    center_frame,
    text=L("Retry"),
    font=("Arial", 12),
)

retry_label.pack(
    anchor="nw",
)


retry_var = tk.IntVar(
    value=DEFAULT_RETRY,
)


tk.Spinbox(
    center_frame,
    from_=1,
    to=10,
    textvariable=retry_var,
    width=23,
    font=("Arial", 12),
).pack(
    anchor="nw",
    pady=(0, 20),
)

# ------------------------------------------------
# Retry delay
# ------------------------------------------------
retry_delay_label = tk.Label(
    center_frame,
    text=L("Retry delay"),
    font=("Arial", 12),
)

retry_delay_label.pack(
    anchor="nw",
)


retry_delay_var = tk.DoubleVar(
    value=DEFAULT_RETRY_DELAY,
)


tk.Entry(
    center_frame,
    textvariable=retry_delay_var,
    width=25,
    font=("Arial", 12),
).pack(
    anchor="nw",
    pady=(0, 20),
)

# ------------------------------------------------
# Provider information — READ ONLY
# ------------------------------------------------
#
# Provider information comes from the main SHL
# provider settings.
#
# The Policy Editor only displays this information.
#
# The user cannot modify:
#
#   PROVIDER_CAPABILITIES
#   SHL_WHITELIST
#   PROVIDER_ALLOW
#   PROVIDER_DENY
#
# These are SHL configuration information, not
# user-editable policy settings.
# ------------------------------------------------
capabilities_label = tk.Label(
    right_frame,
    text=L("Provider Capabilities"),
    font=("Arial", 18, "bold"),
)

capabilities_label.pack(
    anchor="nw",
    pady=(0, 20),
)


capabilities_frame = tk.Frame(
    right_frame,
)

capabilities_frame.pack(
    anchor="nw",
    pady=(0, 20),
)


capability_widgets = []


def clear_capabilities():
    """Remove the current read-only provider information."""
    for widget in capability_widgets:
        widget.destroy()

    capability_widgets.clear()


def capability_value(value):
    """
    Convert a capability value into a display string and color.

    True  = supported / enabled
    False = not supported / disabled
    None  = unknown / not yet defined
    """
    if value is True:
        return L("Yes"), "green"

    if value is False:
        return L("No"), "red"

    return L("Unknown"), "orange"


def show_capabilities(provider):
    """
    Display provider capability and SHL handling information.

    All displayed values are read-only.

    The information is read from the main provider
    settings, not from shl-policy-config.json.
    """
    clear_capabilities()

    provider_capabilities = PROVIDER_CAPABILITIES.get(
        provider,
        {},
    )

    shl_whitelist = SHL_WHITELIST.get(
        provider,
        {},
    )

    provider_allow = PROVIDER_ALLOW.get(
        provider,
        {},
    )

    provider_deny = PROVIDER_DENY.get(
        provider,
        {},
    )

    # ------------------------------------------------
    # Source
    # ------------------------------------------------
    source_label = tk.Label(
        capabilities_frame,
        text=f"{L('Source')}: {provider}",
        font=("Arial", 10, "bold"),
        anchor="w",
    )

    source_label.grid(
        row=0,
        column=0,
        columnspan=5,
        sticky="w",
        pady=(0, 10),
    )

    capability_widgets.append(
        source_label
    )

    # ------------------------------------------------
    # Table headers
    # ------------------------------------------------
    headers = (
        L("Capability"),
        L("Provider"),
        L("SHL"),
        L("Allow"),
        L("Deny"),
    )

    for column, text in enumerate(headers):
        label = tk.Label(
            capabilities_frame,
            text=text,
            font=("Arial", 10, "bold"),
            anchor="w",
        )

        label.grid(
            row=1,
            column=column,
            sticky="w",
            padx=(0, 20),
            pady=(0, 5),
        )

        capability_widgets.append(
            label
        )

    # ------------------------------------------------
    # Capability values
    # ------------------------------------------------
    for row, tag in enumerate(
        POLICY_TAGS,
        start=2,
    ):
        provider_value = provider_capabilities.get(
            tag,
            None,
        )

        shl_value = shl_whitelist.get(
            tag,
            False,
        )

        allow_value = provider_allow.get(
            tag,
            False,
        )

        deny_value = provider_deny.get(
            tag,
            False,
        )

        values = (
            tag.replace(
                "_",
                " ",
            ).title(),
            provider_value,
            shl_value,
            allow_value,
            deny_value,
        )

        for column, value in enumerate(values):
            if column == 0:
                label_text = value
                label_fg = "black"
            else:
                label_text, label_fg = capability_value(
                    value
                )

            label = tk.Label(
                capabilities_frame,
                text=label_text,
                font=("Arial", 10),
                anchor="w",
                fg=label_fg,
            )

            label.grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0, 20),
                pady=2,
            )

            capability_widgets.append(
                label
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

    cfg = providers[item]

    enabled_var.set(
        cfg.get(
            active_enabled_key(),
            False,
        )
    )

    priority = cfg.get(
        active_priority_key()
    )

    if priority is None:
        priority = 0

    priority_var.set(
        priority
    )

    timeout_var.set(
        cfg.get(
            "timeout",
            30,
        )
    )

    retry_var.set(
        cfg.get(
            "retry",
            DEFAULT_RETRY,
        )
    )

    retry_delay_var.set(
        cfg.get(
            "retry_delay",
            DEFAULT_RETRY_DELAY,
        )
    )

    priority_label.config(
        text=f"{active_priority_label()}:"
    )

    show_capabilities(item)


tree.bind(
    "<<TreeviewSelect>>",
    on_select,
)


# ------------------------------------------------
# View switching
# ------------------------------------------------
def switch_view(event=None):
    global current_view
    global current_provider

    index = view_menu.current()

    if index == 0:
        current_view = VIEW_TRANSLATION

    elif index == 1:
        current_view = VIEW_DETECTION

    elif index == 2:
        current_view = VIEW_MEMORY

    else:
        return

    current_provider = None

    enabled_var.set(False)
    priority_var.set(0)
    timeout_var.set(30)
    retry_var.set(DEFAULT_RETRY)
    retry_delay_var.set(DEFAULT_RETRY_DELAY)

    if current_view == VIEW_MEMORY:
        tree.selection_remove(
            tree.selection()
        )

        for item in tree.get_children():
            tree.delete(item)

        priority_label.config(
            text=L("Priority:")
        )

        return

    refresh_provider_tree()

    priority_label.config(
        text=f"{active_priority_label()}:"
    )


view_menu.bind(
    "<<ComboboxSelected>>",
    switch_view,
)


# ------------------------------------------------
# Save changes
# ------------------------------------------------
def save_changes():
    if not current_provider:
        return

    if current_view == VIEW_MEMORY:
        return

    cfg = providers[current_provider]

    cfg[active_enabled_key()] = enabled_var.get()

    cfg["timeout"] = timeout_var.get()

    cfg["retry"] = retry_var.get()

    cfg["retry_delay"] = retry_delay_var.get()

    # Priority is controlled by the Treeview order.
    #
    # Translation:
    #     cfg["priority"]
    #
    # Detection:
    #     cfg["detection_priority"]
    #
    # Enabled state is also view-specific:
    #
    # Translation:
    #     cfg["enabled"]
    #
    # Detection:
    #     cfg["detection_enabled"]
    #
    # Provider capabilities, SHL whitelist rules,
    # provider allow rules, and provider deny rules
    # are never modified here.
    save_policy(policy)

    refresh_provider_tree()

    try:
        tree.selection_set(
            current_provider
        )
        tree.focus(
            current_provider
        )
    except tk.TclError:
        pass


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
        return localizer.L(
            HELP_CONTENT
        )

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

    help_window.title(
        L("Help")
    )

    help_window.geometry(
        "800x600"
    )

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

    configure_help_text(
        help_text
    )

    render_html_help(
        help_text,
        localize_help_content(),
    )


# ------------------------------------------------
# About window
# ------------------------------------------------
def show_about():
    about_window = tk.Toplevel(root)

    about_window.title(
        L("About")
    )

    about_window.geometry(
        "500x300"
    )

    about_window.resizable(
        False,
        False,
    )

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
    root.title(
        L("SHL Policy Editor")
    )

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

    view_label.config(
        text=L("View")
    )

    view_menu["values"] = view_labels()

    if current_view == VIEW_TRANSLATION:
        view_menu.current(0)

    elif current_view == VIEW_DETECTION:
        view_menu.current(1)

    elif current_view == VIEW_MEMORY:
        view_menu.current(2)

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
        text=active_priority_label(),
    )

    tree.heading(
        "timeout",
        text=L("Timeout"),
    )

    tree.heading(
        "retry",
        text=L("Retry"),
    )

    tree.heading(
        "retry_delay",
        text=L("Retry delay"),
    )

    provider_editor_label.config(
        text=L("Provider Editor")
    )

    enabled_label.config(
        text=L("Enabled")
    )

    priority_label.config(
        text=f"{active_priority_label()}:"
    )

    timeout_label.config(
        text=L("Timeout")
    )

    retry_label.config(
        text=L("Retry")
    )

    retry_delay_label.config(
        text=L("Retry delay")
    )

    capabilities_label.config(
        text=L("Provider Capabilities")
    )

    if current_provider:
        show_capabilities(
            current_provider
        )

    save_button.config(
        text=L("Save")
    )

    # Rebuild the provider list because localized
    # headings and active view may have changed.
    if current_view != VIEW_MEMORY:
        refresh_provider_tree()

    # Rebuild the main menu so cascade labels are localized.
    menu_bar.delete(
        0,
        "end",
    )

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

    # Do not clear failed translations here.
    # They are stored per target language.
    localizer._load_translations()

    save_language(language)

    update_ui_language()


# ------------------------------------------------
# Menu commands ISO 639-3
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
    command=lambda: set_ui_language("eng"),
)

language_menu.add_command(
    label="Suomi",
    command=lambda: set_ui_language("fin"),
)

language_menu.add_command(
    label="Swedish",
    command=lambda: set_ui_language("swe"),
)

language_menu.add_command(
    label="Norway",
    command=lambda: set_ui_language("nor"),
)

language_menu.add_command(
    label="Denmark",
    command=lambda: set_ui_language("dan"),
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
    center_frame,
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
