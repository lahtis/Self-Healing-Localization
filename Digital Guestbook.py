# -*- coding: utf-8 -*-
"""
Digital Guestbook.py
Author: Tuomas Lähteenmäki
License: GNU GPLv3
Vesion: 1.0.0
Description: SHL-based UI localization. Only UI texts are translated,
user messages remain in their original language. And it is working guestbook. 
"""

import flet as ft
import configparser
import json
import sys
import os
import sqlite3
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from pathlib import Path
import time
import threading

# Import version info
from _version import __version__, __author__, __license__, __description__

# SHL components (used as designed)
from shl import (
    LanguageValidator,
    setup_logging,
    get_logger,
    translate_text,
)
from shl.engine.translation.cache import TranslationCache
from shl.engine.translation.exceptions import TranslationError

# Initialize logging
setup_logging(console_level="INFO")
logger = get_logger(__name__)

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# --- 1. LOCALIZATION CONFIGURATION ---
@dataclass
class LocalizationConfig:
    """Localization settings following SHL's pattern."""
    source_language: str = "en"
    target_language: str = "en"
    locales_dir: str = "locales"
    cache_ttl: int = 3600
    fallback_language: str = "en"
    use_glfm_lite: bool = True
    glfm_path: Optional[str] = None


# --- 2. LOCALIZATION PROVIDER ---
class UILocalizationProvider:
    """UI localization provider following SHL's provider architecture."""

    def __init__(self, config: LocalizationConfig):
        self.config = config
        self._cache = TranslationCache(ttl=config.cache_ttl)
        self._validator = LanguageValidator(
            base_language=config.fallback_language,
            use_lite=config.use_glfm_lite,
            glfm_path=config.glfm_path
        )
        self._translations: Dict[str, str] = {}
        self._load_translations()

        if not self._validator.is_valid(config.target_language):
            logger.warning(f"Invalid language '{config.target_language}', falling back to '{config.fallback_language}'")
            self.config.target_language = config.fallback_language

    def _get_locale_file(self, lang_code: str) -> str:
        return os.path.join(self.config.locales_dir, f"{lang_code}.json")

    def _ensure_locales_dir(self):
        """Ensures the locales directory exists."""
        Path(self.config.locales_dir).mkdir(parents=True, exist_ok=True)
        readme_path = os.path.join(self.config.locales_dir, "README.md")
        if not os.path.exists(readme_path):
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(f"""# Translations - Digital Guestbook v{__version__}

This folder contains translations for the Digital Guestbook.

## How SHL Handles Translations
SHL does not modify existing translations after they have been created.
- You can edit these files manually to customize translations
- Your changes are permanent - SHL respects them
- SHL only adds new translations when it encounters untranslated text
- SHL never overwrites existing translations

## Files
- en.json - English translations
- fi.json - Finnish translations
- sv.json - Swedish translations
- etc.

## Translation Workflow
1. First run: SHL translates all UI text and saves to this folder
2. Manual editing: You can edit any translation in these files
3. Subsequent runs: SHL uses your manual translations
4. New text: SHL adds translations for previously unseen text

## Example
{{
  "Empty": "Tyhjennä",
  "Message": "Viesti"
}}

If you want to reset translations to SHL's defaults, simply delete this file and restart the application.

---
Version: {__version__}
Author: {__author__}
License: {__license__}
""")

    def _load_translations(self):
        """Loads translations following SHL's cache pattern."""
        self._ensure_locales_dir()
        locale_file = self._get_locale_file(self.config.target_language)

        if os.path.exists(locale_file):
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self._translations = json.load(f)
                    logger.info(f"Loaded {len(self._translations)} UI translations from {locale_file}")
            except Exception as e:
                logger.error(f"Failed to load translations: {e}")
                self._translations = {}
        else:
            logger.info(f"No UI translations found for '{self.config.target_language}', will create new")
            self._translations = {}

    def _save_translations(self):
        """Saves translations following SHL's cache pattern."""
        locale_file = self._get_locale_file(self.config.target_language)
        try:
            with open(locale_file, 'w', encoding='utf-8') as f:
                json.dump(self._translations, f, ensure_ascii=False, indent=2)
                logger.debug(f"Saved {len(self._translations)} UI translations to {locale_file}")
        except Exception as e:
            logger.error(f"Failed to save translations: {e}")

    def _translate_with_shl(self, text: str) -> str:
        """Uses SHL's translate_text function for machine translation."""
        try:
            cached = self._cache.get(text, self.config.source_language, self.config.target_language)
            if cached:
                return cached

            result = translate_text(
                text=text,
                target_lang=self.config.target_language,
                source_lang=self.config.source_language
            )
            self._cache.set(text, result, self.config.source_language, self.config.target_language)
            return result
        except TranslationError as e:
            logger.error(f"Translation failed: {e}")
            return text
        except Exception as e:
            logger.error(f"Unexpected translation error: {e}")
            return text

    def L(self, text: str, default_text: Optional[str] = None) -> str:
        """Main method for UI text localization."""
        if self.config.target_language == "en" or self.config.target_language.startswith("en"):
            return text

        if text in self._translations:
            return self._translations[text]

        try:
            cached = self._cache.get(text, self.config.source_language, self.config.target_language)
            if cached:
                self._translations[text] = cached
                self._save_translations()
                return cached
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")

        logger.info(f"Translating UI text: '{text}' -> {self.config.target_language}")
        translated = self._translate_with_shl(text)

        if translated != text:
            self._translations[text] = translated
            self._save_translations()
            return translated

        if default_text:
            self._translations[text] = default_text
            self._save_translations()
            return default_text

        return text

    def set_language(self, lang_code: str):
        """Changes language using SHL's LanguageValidator."""
        if self._validator.is_valid(lang_code):
            old_lang = self.config.target_language
            self.config.target_language = lang_code
            self._load_translations()
            logger.info(f"Language changed from '{old_lang}' to '{lang_code}'")
        else:
            logger.warning(f"Invalid language '{lang_code}', keeping current")

    def get_available_languages(self) -> List[str]:
        """Returns list of languages that have translations."""
        languages = []
        if os.path.exists(self.config.locales_dir):
            for file in os.listdir(self.config.locales_dir):
                if file.endswith('.json'):
                    lang = file.replace('.json', '')
                    languages.append(lang)
        return sorted(languages)

    def get_stats(self) -> Dict:
        """Returns statistics."""
        cache_size = 0
        try:
            cache_size = self._cache.size()
            if not isinstance(cache_size, int):
                cache_size = 0
        except Exception as e:
            logger.debug(f"Could not get cache size: {e}")

        return {
            "ui_translations": len(self._translations),
            "language": self.config.target_language,
            "source_language": self.config.source_language,
            "locales_dir": self.config.locales_dir,
            "cache_size": cache_size,
            "available_languages": self.get_available_languages()
        }


# --- 3. LOCALIZATION MANAGER ---
class LocalizationManager:
    """Localization manager connecting SHL components to the application."""

    def __init__(self, config: LocalizationConfig):
        self.config = config
        self.provider = UILocalizationProvider(config)
        self._validator = LanguageValidator(
            base_language=config.fallback_language,
            use_lite=config.use_glfm_lite
        )

    def L(self, text: str, default_text: Optional[str] = None) -> str:
        return self.provider.L(text, default_text)

    def set_language(self, lang_code: str):
        self.provider.set_language(lang_code)
        self.config.target_language = lang_code

    def get_language(self) -> str:
        return self.config.target_language

    def get_available_languages(self) -> List[str]:
        return self.provider.get_available_languages()

    def get_stats(self) -> Dict:
        return self.provider.get_stats()

    def get_validator(self) -> LanguageValidator:
        return self._validator

    def get_supported_languages(self) -> List[str]:
        try:
            from shl import get_all_supported_languages
            return get_all_supported_languages()
        except:
            return ["en", "fi", "sv", "de", "fr", "es", "it", "nl", "ru", "zh", "ja", "ko"]


# --- 4. FLET 0.80+ COMPATIBILITY ---
def create_button(text: str, on_click, icon=None, color=None):
    """Creates a Flet 0.80+ compatible button."""
    content_items = []
    if icon:
        content_items.append(ft.Icon(icon))
    content_items.append(ft.Text(text))
    return ft.Button(
        content=ft.Row(
            content_items,
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=on_click,
        style=ft.ButtonStyle(color=color) if color else None,
    )


def create_elevated_button(text: str, on_click, icon=None):
    """Creates an elevated button (Flet 0.80+ compatible)."""
    content_items = []
    if icon:
        content_items.append(ft.Icon(icon))
    content_items.append(ft.Text(text))
    return ft.FilledButton(
        content=ft.Row(
            content_items,
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=on_click,
    )


# --- 5. APPLICATION ---
class DigitalGuestbookApp:
    """Main application following SHL's design pattern."""

    FLAGS = {
        "en": ("🇬🇧", "English"),
        "fi": ("🇫🇮", "Suomi"),
        "sv": ("🇸🇪", "Svenska"),
        "de": ("🇩🇪", "Deutsch"),
        "fr": ("🇫🇷", "Français"),
        "es": ("🇪🇸", "Español"),
        "it": ("🇮🇹", "Italiano"),
        "nl": ("🇳🇱", "Nederlands"),
        "ru": ("🇷🇺", "Русский"),
        "zh": ("🇨🇳", "中文"),
        "ja": ("🇯🇵", "日本語"),
        "ko": ("🇰🇷", "한국어"),
    }

    def __init__(self, page: ft.Page):
        self.page = page
        self._init_paths()
        self._init_config()
        self._init_localization()
        self._init_storage()
        self._init_ui()
        self._timeout_seconds = self.timeout_minutes * 60
        self._last_activity = time.time()
        self._timer_running = False
        self._show_language_selection()

    def _init_paths(self):
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.config_path = os.path.join(self.base_path, "config.conf")
        self.locales_dir = os.path.join(self.base_path, "locales")
        self.db_path = os.path.join(self.base_path, "data.db")

    def _init_config(self):
        self.config = configparser.ConfigParser()
        if not os.path.exists(self.config_path):
            self.config['SETTINGS'] = {
                'password': '1234',
                'theme': 'dark',
                'language': 'en',
                'timeout_minutes': '3'
            }
            with open(self.config_path, 'w') as f:
                self.config.write(f)

        self.config.read(self.config_path)
        self.admin_password = self.config.get('SETTINGS', 'password', fallback='1234')
        self.lang_code = self.config.get('SETTINGS', 'language', fallback='en')
        self.theme = self.config.get('SETTINGS', 'theme', fallback='dark')
        self.timeout_minutes = self.config.getint('SETTINGS', 'timeout_minutes', fallback=3)

    def _save_config(self):
        self.config['SETTINGS']['language'] = self.lang_code
        self.config['SETTINGS']['timeout_minutes'] = str(self.timeout_minutes)
        with open(self.config_path, 'w') as f:
            self.config.write(f)

    def _init_localization(self):
        loc_config = LocalizationConfig(
            source_language="en",
            target_language=self.lang_code,
            locales_dir=self.locales_dir,
            fallback_language="en",
            use_glfm_lite=True
        )
        self.loc = LocalizationManager(loc_config)
        stats = self.loc.get_stats()
        logger.info(f"Localization initialized: {stats}")

    def _init_storage(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def _init_ui(self):
        self.page.title = f"Digital Guestbook v{__version__}"
        self.page.theme_mode = ft.ThemeMode.DARK if self.theme == 'dark' else ft.ThemeMode.LIGHT
        self.page.window_width = 450
        self.page.window_height = 650

        self.title = None
        self.input_field = None
        self.info_text = None
        self.message_list = None
        self.save_button = None
        self.clear_button = None
        self.search_field = None
        self.status_text = None

    def _reset_activity(self):
        self._last_activity = time.time()

    def _start_timeout_timer(self):
        if self._timer_running:
            return
        self._timer_running = True

        def check_timeout():
            while self._timer_running:
                time.sleep(5)
                if time.time() - self._last_activity > self._timeout_seconds:
                    logger.info("Time limit expired – returning to the flag page")
                    self._timer_running = False
                    self.page.run_task(self._return_to_language_selection)
                    break

        t = threading.Thread(target=check_timeout, daemon=True)
        t.start()

    async def _return_to_language_selection(self):
        self._timer_running = False
        self._show_language_selection()

    def _show_language_selection(self):
        self._timer_running = False
        self.page.controls.clear()

        title = ft.Text(
            "Valitse kieli / Select language",
            size=22,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )

        flag_buttons = []
        for code, (flag, name) in self.FLAGS.items():
            btn = ft.Button(
                content=ft.Column(
                    [
                        ft.Text(flag, size=36),
                        ft.Text(name, size=12),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                width=110,
                height=90,
                on_click=lambda e, c=code: self._on_language_selected(c),
            )
            flag_buttons.append(btn)

        rows = []
        for i in range(0, len(flag_buttons), 3):
            rows.append(
                ft.Row(
                    flag_buttons[i:i+3],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                )
            )

        timeout_info = ft.Text(
            f"The session will end automatically in {self.timeout_minutes} minutes",
            size=12,
            color="grey",
            text_align=ft.TextAlign.CENTER,
        )

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=30),
                        title,
                        ft.Container(height=20),
                        *rows,
                        ft.Container(height=20),
                        timeout_info,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                expand=True,
                padding=20,
            )
        )
        self.page.update()

    def _on_language_selected(self, lang_code: str):
        logger.info(f"Language selected: {lang_code}")
        self.lang_code = lang_code
        self.loc.set_language(lang_code)
        self._save_config()
        self._show_translation_progress(lang_code)

    def _show_translation_progress(self, lang_code: str):
        """Näyttää indikaattorin käännösten haun aikana."""
        self.page.controls.clear()

        ui_texts = [
            "Guestbook",
            "Message",
            "Ready",
            "Save",
            "Empty",
            "Search Messages...",
            "Change language",
            "Saved messages",
            "Password",
            "Admin password required",
            "Wrong password!",
            "Cancel",
            "OK",
            "The field is empty!",
            "Database cleared.",
            "Saved: {}",
        ]

        progress_text = ft.Text(
            f"Looking for translations ({lang_code})...",
            size=16,
            text_align=ft.TextAlign.CENTER,
        )
        progress_bar = ft.ProgressBar(width=280, color="blue")
        status_text = ft.Text("", size=13, color="grey", text_align=ft.TextAlign.CENTER)
        current_text = ft.Text("", size=12, color="bluegrey", text_align=ft.TextAlign.CENTER)

        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=80),
                        ft.Text("SHL", size=28, weight=ft.FontWeight.BOLD),
                        ft.Text("Translating UI...", size=16),
                        ft.Container(height=20),
                        progress_bar,
                        ft.Container(height=12),
                        progress_text,
                        status_text,
                        current_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.Alignment(0, 0),
                padding=30,
            )
        )
        self.page.update()

        def do_translations():
            total = len(ui_texts)
            translated_count = 0

            for i, text in enumerate(ui_texts, 1):
                progress_bar.value = i / total
                progress_text.value = f"Let's translate it {i}/{total}"
                current_text.value = f'"{text}"'
                status_text.value = f"Language: {lang_code}"
                self.page.update()

                _ = self.loc.L(text)
                translated_count += 1
                time.sleep(0.12)

            progress_text.value = "Done!"
            current_text.value = f"{translated_count} translation ready"
            self.page.update()
            time.sleep(0.5)

            self.page.run_task(self._finish_language_selection)

        threading.Thread(target=do_translations, daemon=True).start()

    async def _finish_language_selection(self):
        self._build_main_page()
        self._reset_activity()
        self._start_timeout_timer()

    def _build_main_page(self):
        self.page.controls.clear()

        self.title = ft.Text(self.loc.L("Guestbook"), size=25, weight=ft.FontWeight.BOLD)

        self.input_field = ft.TextField(
            label=self.loc.L("Message"),
            on_submit=self._on_save,
            multiline=True,
            min_lines=1,
            max_lines=3
        )

        self.info_text = ft.Text(self.loc.L("Ready"), color="blue")

        self.message_list = ft.ListView(expand=1, spacing=10, padding=10)

        self.save_button = create_elevated_button(
            self.loc.L("Save"),
            self._on_save,
            ft.Icons.SAVE
        )

        self.clear_button = create_button(
            self.loc.L("Empty"),
            self._on_clear,
            ft.Icons.DELETE_SWEEP,
            "red"
        )

        self.search_field = ft.TextField(
            label=self.loc.L("Search Messages..."),
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=self._on_search
        )

        stats = self.loc.get_stats()
        translation_count = stats.get('ui_translations', 0)

        self.status_text = ft.Text(
            f"{self.loc.L('Ready')} | {translation_count} UI translations | Language: {self.loc.get_language()}",
            size=12,
            color="grey"
        )

        change_lang_btn = ft.TextButton(
            self.loc.L("Change language"),
            icon=ft.Icons.LANGUAGE,
            on_click=lambda e: self._show_language_selection()
        )

        footer = ft.Column(
            [
                ft.Divider(height=1),
                ft.Row(
                    [
                        ft.Text(f"v{__version__}", size=10, color="grey"),
                        ft.Text("|", size=10, color="grey"),
                        ft.Text(__author__, size=10, color="grey"),
                        ft.Text("|", size=10, color="grey"),
                        ft.Text(__license__, size=10, color="grey"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=5,
                ),
            ],
            spacing=2,
        )

        self.page.add(
            self.title,
            self.input_field,
            self.info_text,
            ft.Row([
                self.save_button,
                self.clear_button,
                change_lang_btn,
            ], wrap=True),
            ft.Divider(),
            ft.Row([
                self.search_field,
                ft.IconButton(icon=ft.Icons.CLEAR, on_click=self._on_clear_search)
            ]),
            ft.Text(self.loc.L("Saved messages"), size=20),
            self.message_list,
            ft.Divider(),
            self.status_text,
            footer,
        )
        self._load_messages()
        self.page.update()

    def _update_status(self):
        if self.status_text is None:
            return
        stats = self.loc.get_stats()
        count = stats.get('ui_translations', 0)
        lang = self.loc.get_language()
        self.status_text.value = f"{self.loc.L('Ready')} | {count} UI translations | Language: {lang}"
        self.page.update()

    def _load_messages(self):
        if self.message_list is None:
            return
        self.message_list.controls.clear()
        cursor = self.conn.execute("SELECT id, text FROM messages ORDER BY id DESC")
        for row in cursor.fetchall():
            self.message_list.controls.append(
                ft.ListTile(
                    title=ft.Text(row[1]),
                    subtitle=ft.Text(f"ID: {row[0]}", size=10, color="grey"),
                )
            )
        self.page.update()

    def _ask_password(self, on_success):
        password_field = ft.TextField(
            label=self.loc.L("Password"),
            password=True,
            can_reveal_password=True,
            autofocus=True,
            on_submit=lambda e: check_password(e),
        )

        def check_password(e):
            if password_field.value == self.admin_password:
                dialog.open = False
                self.page.update()
                on_success()
            else:
                password_field.error_text = self.loc.L("Wrong password!")
                self.page.update()

        def close_dialog(e):
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(self.loc.L("Admin password required")),
            content=password_field,
            actions=[
                ft.TextButton(self.loc.L("Cancel"), on_click=close_dialog),
                ft.FilledButton(self.loc.L("OK"), on_click=check_password),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _on_save(self, e):
        self._reset_activity()
        text = self.input_field.value
        if text and text.strip():
            try:
                self.conn.execute("INSERT INTO messages (text) VALUES (?)", (text.strip(),))
                self.conn.commit()
                self.info_text.value = self.loc.L("Saved: {}").format(text.strip())
                self.info_text.color = "green"
                self.input_field.value = ""
                self._load_messages()
                self._update_status()
            except Exception as err:
                self.info_text.value = f"Error: {err}"
                self.info_text.color = "red"
        else:
            self.info_text.value = self.loc.L("The field is empty!")
            self.info_text.color = "red"
        self.page.update()

    def _on_clear(self, e):
        self._reset_activity()

        def do_clear():
            try:
                self.conn.execute("DELETE FROM messages")
                self.conn.commit()
                self.info_text.value = self.loc.L("Database cleared.")
                self.info_text.color = "orange"
                self._load_messages()
                self._update_status()
            except Exception as err:
                self.info_text.value = f"Error: {err}"
                self.info_text.color = "red"
            self.page.update()

        self._ask_password(do_clear)

    def _on_search(self, e):
        self._reset_activity()
        query = self.search_field.value
        if query and query.strip():
            self.message_list.controls.clear()
            cursor = self.conn.execute(
                "SELECT id, text FROM messages WHERE text LIKE ? ORDER BY id DESC",
                (f"%{query.strip()}%",)
            )
            for row in cursor.fetchall():
                self.message_list.controls.append(
                    ft.ListTile(
                        title=ft.Text(row[1]),
                        subtitle=ft.Text(f"ID: {row[0]}", size=10, color="grey"),
                    )
                )
            self.page.update()
        else:
            self._load_messages()

    def _on_clear_search(self, e):
        self._reset_activity()
        self.search_field.value = ""
        self._load_messages()
        self.page.update()

    def run(self):
        self.page.update()


# --- 6. MAIN ---
def main(page: ft.Page):
    app = DigitalGuestbookApp(page)
    app.run()


if __name__ == "__main__":
    ft.run(main=main, assets_dir="assets")
