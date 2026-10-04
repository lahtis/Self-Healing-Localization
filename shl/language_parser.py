"""
File: shl/language_parser.py
Author: Tuomas Lähteenmäki
License: MIT
Version: 0.2.16
Description:
Language parser for SHL.

Resolves user-provided language identifiers through GLFM,
providing a canonical language identity for SHL and mapping
resolved languages to provider-native language codes when
required.

GLFM is the authoritative source for language identity.
ISO 639-3 is used as SHL's canonical internal language
identifier, while GLFM provides BCP-47 and other language
metadata.

The parser does not contain provider-specific language
aliases. Provider-native codes are resolved through the
provider language cache.

Resolution flow:

    User input
        ↓
    GLFM
        ↓
    Canonical ISO 639-3 identity
        ↓
    ┌───────────────────────────────┐
    │                               │
    ↓                               ↓
SHL language                  Provider cache
   identity                         ↓
    │                         Provider-native
    │                             code
    ↓
Language pairs
and BCP-47
metadata

"""


import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from shl.language_validator import LanguageValidator
from shl.utils.lang_utils import parse_bcp47


logger = logging.getLogger(__name__)


class ParsedLanguage:
    """
    Represents a language resolved through GLFM.
    """


    def __init__(
        self,
        input_value: str,
        iso639_3: str,
        bcp47: Optional[str],
        input_bcp47: Optional[str],
        script: Optional[str],
        region: Optional[str],
        name: Optional[str],
        glfm_info: Dict[str, Any],
    ) -> None:
        self.input = input_value
        self.iso639_3 = iso639_3
        self.bcp47 = bcp47
        self.input_bcp47 = input_bcp47
        self.script = script
        self.region = region
        self.name = name
        self.glfm_info = glfm_info

    def __repr__(self) -> str:
        return (
            "ParsedLanguage("
            f"input={self.input!r}, "
            f"iso639_3={self.iso639_3!r}, "
            f"bcp47={self.bcp47!r}, "
            f"input_bcp47={self.input_bcp47!r}, "
            f"script={self.script!r}, "
            f"region={self.region!r}, "
            f"name={self.name!r}"
            ")"
        )

class LanguageParser:
    """
    Resolves language identifiers using GLFM.

    The parser does not contain provider-specific language aliases.
    GLFM determines the language identity and ISO 639-3 is used as
    SHL's canonical internal language identifier.
    """

    DEFAULT_CACHE_FILENAME = ".languages_cache.json"

    def __init__(
        self,
        validator: Optional[LanguageValidator] = None,
        cache_path: Optional[str | Path] = None,
    ) -> None:
        self.validator = validator or LanguageValidator()

        if cache_path is None:
            self.cache_path = (
                Path(__file__).resolve().parent.parent
                / self.DEFAULT_CACHE_FILENAME
            )
        else:
            self.cache_path = Path(cache_path).expanduser().resolve()

        self._provider_cache: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Language parsing
    # ------------------------------------------------------------------

    def parse(self, language: str) -> ParsedLanguage:
        """
        Resolve a language identifier through GLFM.

        The input may be a recognized language identifier supported
        by GLFM, including:

            - language name
            - ISO 639-1 code
            - ISO 639-3 code
            - BCP-47 language tag
            - GLFM language identifier

        GLFM is the authoritative source for language identity.
        The resolved language is represented internally by its
        ISO 639-3 identifier.

        Returns:
            ParsedLanguage:
                The resolved language identity and related GLFM
                language metadata.

        Raises:
            ValueError:
            If the language cannot be resolved through GLFM.
            TypeError:
                If language is not a string.
        """

        if not isinstance(language, str):
            raise TypeError("Language identifier must be a string.")

        value = language.strip()

        if not value:
            raise ValueError("Language identifier cannot be empty.")

        info = self.validator.get_language_info(value)

        if not info:
            raise ValueError(
                f"Unknown language identifier: {language}"
            )

        iso639_3 = info.get("iso639_3")

        if not iso639_3:
            raise ValueError(
                f"GLFM record does not contain ISO 639-3 code: {language}"
            )

        bcp47 = info.get("bcp47")
        name = info.get("name")

        input_bcp47 = None
        script = None
        region = None

        parsed_language, parsed_script, parsed_region = parse_bcp47(value)

        if parsed_language:
            input_bcp47 = value.replace("_", "-")

            if parsed_script:
                script = parsed_script.title()

            if parsed_region:
                region = parsed_region.upper()

        parsed = ParsedLanguage(
            input_value=language,
            iso639_3=iso639_3.lower(),
            bcp47=bcp47,
            input_bcp47=input_bcp47,
            script=script,
            region=region,
            name=name,
            glfm_info=info,
        )

        logger.debug(
            "Language parsed: '%s' -> '%s' (%s)",
            language,
            parsed.iso639_3,
            parsed.bcp47,
        )

        return parsed

    # ------------------------------------------------------------------
    # Canonical identity
    # ------------------------------------------------------------------

    def normalize(self, language: str) -> str:
        """
        Resolve a language to SHL's canonical ISO 639-3 identifier.
        """
        return self.parse(language).iso639_3

    def normalize_pair(
        self,
        source_language: str,
        target_language: str,
    ) -> str:
        """
        Resolve a source/target language pair to SHL's canonical
        ISO 639-3 identifiers.
        """
        source = self.normalize(source_language)
        target = self.normalize(target_language)

        return f"{source}-{target}"

    def normalize_bcp47_pair(
        self,
        source_language: str,
        target_language: str,
    ) -> str:
        """
        Resolve a source/target language pair to GLFM's canonical BCP-47 tags.
        """
        source = self.get_bcp47(source_language)
        target = self.get_bcp47(target_language)

        if not source:
            raise ValueError(
                f"Unable to resolve BCP-47 language tag: {source_language}"
            )

        if not target:
            raise ValueError(
                f"Unable to resolve BCP-47 language tag: {target_language}"
            )

        return f"{source}-{target}"

    # ------------------------------------------------------------------
    # BCP 47
    # ------------------------------------------------------------------

    def get_bcp47(self, language: str) -> Optional[str]:
        """
        Return the GLFM BCP-47 tag for a language.
        """
        return self.parse(language).bcp47

    # ------------------------------------------------------------------
    # Provider cache
    # ------------------------------------------------------------------

    def load_provider_cache(self) -> Dict[str, Any]:
        """
        Load the provider language cache.

        The cache contains provider-native language codes. The parser
        does not modify or rewrite those codes.
        """
        if self._provider_cache is not None:
            return self._provider_cache

        if not self.cache_path.exists():
            logger.warning(
                "Language provider cache not found: %s",
                self.cache_path,
            )
            self._provider_cache = {
                "providers": {},
                "last_updated": None,
            }
            return self._provider_cache

        try:
            with self.cache_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Failed to load language provider cache '%s': %s",
                self.cache_path,
                exc,
            )
            self._provider_cache = {
                "providers": {},
                "last_updated": None,
            }
            return self._provider_cache

        if not isinstance(data, dict):
            logger.warning(
                "Invalid language provider cache format: %s",
                self.cache_path,
            )
            self._provider_cache = {
                "providers": {},
                "last_updated": None,
            }
            return self._provider_cache

        self._provider_cache = data
        return data

    # ------------------------------------------------------------------
    # Provider language resolution
    # ------------------------------------------------------------------


    def get_provider_code(
        self,
        language: str,
        provider: str,
    ) -> Optional[str]:
        """
        Resolve a language to a provider-native language code.

        Resolution is based on:
            1. GLFM language identity
            2. Provider language cache

        The provider cache remains authoritative for the provider's
        actual language code.
        """
        parsed = self.parse(language)
        cache = self.load_provider_cache()

        providers = cache.get("providers", {})

        if not isinstance(providers, dict):
            return None

        provider_key = provider.lower()

        provider_data = None

        for key, value in providers.items():
            normalized_key = str(key).lower()

            if (
                normalized_key == provider_key
                or normalized_key.startswith(provider_key + "_")
            ):
                provider_data = value
                break

        if provider_data is None:
            logger.debug(
                "Provider '%s' not found in language cache.",
                provider,
            )
            return None

        if isinstance(provider_data, dict):
            supported_codes = list(provider_data.keys())
        elif isinstance(provider_data, list):
            supported_codes = provider_data
        else:
            return None

        return self._find_best_provider_match(
            parsed,
            supported_codes,
            provider_data if isinstance(provider_data, dict) else None,
        )


    # ------------------------------------------------------------------
    # Provider matching
    # ------------------------------------------------------------------

    def _find_best_provider_match(
        self,
        language: ParsedLanguage,
        supported_codes: list[Any],
        provider_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Find the best provider-native code for a parsed language.

        Provider codes are returned exactly as stored in the cache.
        """

        codes = [
            str(code)
            for code in supported_codes
            if isinstance(code, str)
        ]

        if not codes:
            return None

        # --------------------------------------------------------------
        # 1. Match explicit input BCP 47 variant
        # --------------------------------------------------------------

        if language.input_bcp47 and (
            language.script or language.region
        ):
            input_tag = language.input_bcp47

            exact = self._find_case_insensitive(
                input_tag,
                codes,
            )

            if exact is not None:
                return exact

        # --------------------------------------------------------------
        # 2. Match explicit script/region variant
        # --------------------------------------------------------------

        if language.script or language.region:
            # First prefer an exact script + region match.
            if language.script and language.region:
                for code in codes:
                    code_parts = code.split("-")

                    if len(code_parts) >= 2:
                        if (
                            code_parts[-2].casefold()
                            == language.script.casefold()
                            and code_parts[-1].casefold()
                            == language.region.casefold()
                        ):
                            return code

            # Then prefer a provider code matching the explicit region.
            if language.region:
                for code in codes:
                    code_parts = code.split("-")

                    if code_parts:
                        if (
                            code_parts[-1].casefold()
                            == language.region.casefold()
                        ):
                            return code

            # Finally try a provider code matching the explicit script.
            if language.script:
                for code in codes:
                    code_parts = code.split("-")

                    if len(code_parts) >= 2:
                        if (
                            code_parts[-1].casefold()
                            == language.script.casefold()
                        ):
                            return code

        # --------------------------------------------------------------
        # 3. Exact BCP 47 match
        # --------------------------------------------------------------

        if language.bcp47:
            exact = self._find_case_insensitive(
                language.bcp47,
                codes,
            )

            if exact is not None:
                return exact

        # --------------------------------------------------------------
        # 4. Match ISO 639-1 / ISO 639-3 through GLFM identity
        # --------------------------------------------------------------

        iso639_1 = language.glfm_info.get("iso639_1")
        iso639_3 = language.iso639_3

        iso_candidates = []

        if isinstance(iso639_1, str) and iso639_1:
            iso_candidates.append(iso639_1)

        if isinstance(iso639_3, str) and iso639_3:
            iso_candidates.append(iso639_3)

        for candidate in iso_candidates:
            exact = self._find_case_insensitive(
                candidate,
                codes,
            )

            if exact is not None:
                return exact

        # --------------------------------------------------------------
        # 5. Match BCP 47 base language
        # --------------------------------------------------------------

        if language.bcp47:
            base = language.bcp47.split("-", 1)[0]

            exact = self._find_case_insensitive(
                base,
                codes,
            )

            if exact is not None:
                return exact

        # --------------------------------------------------------------
        # 6. Match provider code using BCP 47 language prefix
        # --------------------------------------------------------------

        if language.bcp47:
            base = language.bcp47.split("-", 1)[0].casefold()

            for code in codes:
                if code.split("-", 1)[0].casefold() == base:
                    return code

        # --------------------------------------------------------------
        # 7. Match provider language by GLFM language name
        # --------------------------------------------------------------

        if provider_data and language.name:
            glfm_name = language.name.casefold().strip()

            for code, provider_name in provider_data.items():
                if (
                    isinstance(provider_name, str)
                    and provider_name.casefold().strip() == glfm_name
                ):
                    return str(code)

        logger.debug(
            "No provider language match for '%s' (%s).",
            language.input,
            language.iso639_3,
        )

        return None

    @staticmethod
    def _find_case_insensitive(
        value: str,
        candidates: list[str],
    ) -> Optional[str]:
        """
        Find a candidate without changing its stored representation.
        """
        value_folded = value.casefold()

        for candidate in candidates:
            if candidate.casefold() == value_folded:
                return candidate

        return None

