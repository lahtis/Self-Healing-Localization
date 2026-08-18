# SHL Configuration

SHL uses a small, dependency-free configuration layer for provider settings
and environment variables.

The configuration manager is located at:

```text
shl/
└── config/
    ├── __init__.py
    └── manager.py
```

The application configuration itself is normally kept in the project root:

```text
my_project/
├── shl-config.json
├── .env
└── shl/
    └── ...
```

## Configuration file

By default, SHL looks for `shl-config.json` in the current project directory.

A provider can be configured with `enabled`, `allow`, and `deny` settings.

Example:

```json
{
    "MyMemory": {
        "enabled": true,
        "allow": [],
        "deny": ["html"]
    },
    "DeepL": {
        "enabled": true,
        "allow": [],
        "deny": ["html"]
    },
    "Google": {
        "enabled": true,
        "allow": [],
        "deny": ["html"]
    }
}
```

There is no separate `fallback` flag.

## Provider `enabled`

`enabled` determines whether a provider is available to SHL.

```json
"DeepL": {
    "enabled": true
}
```

When `enabled` is `false`, the provider is not included among the
providers available for translation or fallback.

The enabled providers are available through:

```python
config.get_enabled_providers()
```

## Automatic fallback

SHL treats other enabled providers as possible fallback providers.

A provider can never be its own fallback.

For example, when the current provider is `DeepL`:

```python
config.get_fallback_providers("DeepL")
```

returns the other enabled providers.

If the configuration is:

```json
{
    "MyMemory": {
        "enabled": true
    },
    "DeepL": {
        "enabled": true
    },
    "Google": {
        "enabled": false
    }
}
```

the fallback relationship is effectively:

```text
MyMemory → DeepL
DeepL    → MyMemory
```

Google is not included because it is disabled.

If only one provider is enabled:

```json
{
    "MyMemory": {
        "enabled": true
    },
    "DeepL": {
        "enabled": false
    },
    "Google": {
        "enabled": false
    }
}
```

then MyMemory has no alternative provider.

In that situation, SHL does not attempt to use MyMemory as its own fallback. If the provider cannot produce a translation, the runtime may show the `base_lang` text.

## `base_lang` is not a stored translation

The `base_lang` fallback is a runtime display fallback.

If no provider can produce a translation, SHL may display the base-language
text to keep the application usable.

That value must not be written into the target-language translation file.

For example:

```text
Requested: fi → de

Translation file:
    German translation is missing

Provider:
    MyMemory fails

Fallback providers:
    none

Runtime:
    display base_lang (the original text)
```

The Finnish text is displayed, but it is not saved as the German translation.

This is important for SHL's self-healing behavior. When a translation provider becomes available again, SHL can generate the real translation and store it in the appropriate target-language file.

The flow is therefore:

```text
translation exists
    ↓
use translation

translation missing
    ↓
provider succeeds
    ↓
use translation
    ↓
store target-language translation

translation missing
    ↓
all suitable providers fail
    ↓
display base_lang text

base_lang → fi
text      → "Tervetuloa sovellukseen"

    ↓
do NOT store base_lang text as translation
```

## `allow` and `deny`

`allow` and `deny` control whether a provider is suitable for a particular
item, such as a format.

Example:

```json
"DeepL": {
    "enabled": true,
    "allow": [],
    "deny": ["html"]
}
```

The rules are evaluated in this order:

1. An item on `deny` is rejected.
2. If `allow` is empty, the configured default is used.
3. If `allow` contains the item, it is accepted.
4. Otherwise, the item is rejected.

For example:

```python
config.is_allowed("DeepL", "html")
```

returns `False` when `html` is present in the provider's `deny` list.

This allows the router to select another enabled provider when the current
provider is not suitable for the request.

## `.env` support

`ConfigManager` can load a `.env` file without requiring an external
dependency.

By default:

```text
.env
```

is loaded from the project directory.

Example:

```text
DEEPL_API_KEY=your-key
GOOGLE_API_KEY=your-key
MYMEMORY_EMAIL=example@example.com
```

The values are made available through the process environment.

They can be accessed with:

```python
config.get_env("DEEPL_API_KEY")
```

An explicit default can also be supplied:

```python
config.get_env("DEEPL_API_KEY", default=None)
```

The `.env` file is monitored by the configuration watcher. When it changes,
SHL reloads its environment values.

Do not commit secret keys to source control.

## Using `ConfigManager`

Import the manager through the configuration package:

```python
from shl.config import ConfigManager
```

Create an instance:

```python
config = ConfigManager()
```

The default paths are:

```text
shl-config.json
.env
```

Custom paths can be supplied:

```python
from pathlib import Path

config = ConfigManager(
    path=Path("shl-config.json"),
    env_path=Path(".env"),
    check_interval=1.0,
)
```

## Reading provider settings

Get a complete provider configuration:

```python
deepl = config.get_provider("DeepL")
```

Get one setting:

```python
enabled = config.get_provider_setting(
    "DeepL",
    "enabled",
    default=False,
)
```

Or simply:

```python
enabled = config.is_enabled("DeepL")
```

Get all enabled providers:

```python
providers = config.get_enabled_providers()
```

Get fallback candidates for a provider:

```python
fallbacks = config.get_fallback_providers("DeepL")
```

Get all providers:

```python
providers = config.get_provider_list()
```

## Configuration reload

`ConfigManager` monitors `shl-config.json` automatically.

When the file changes, SHL attempts to reload it.

If the new JSON is invalid, the previous valid configuration is retained.
This prevents a temporary or incomplete file write from replacing a working
configuration with invalid data.

Manual reload is also possible:

```python
config.reload()
```

A forced reload can be requested with:

```python
config.reload(force=True)
```

## Reload callbacks

Code can register a callback that runs after a successful configuration
reload:

```python
def on_config_reload(new_config):
    print("Configuration changed")


config.on_reload(on_config_reload)
```

The callback receives a copy of the new configuration.

A callback can be removed with:

```python
config.remove_reload_callback(on_config_reload)
```

## Thread safety

`ConfigManager` protects its internal configuration with a re-entrant lock.

Returned configuration structures are deep copies, so callers cannot
accidentally modify the internal configuration through a returned
dictionary or list.

This allows the configuration watcher and application code to use the
manager concurrently.

## Watcher lifecycle

The watcher starts automatically when `ConfigManager` is created.

It can be stopped explicitly:

```python
config.stop_watcher()
```

It can also be restarted:

```python
config.start_watcher()
```

For explicit resource management:

```python
with ConfigManager() as config:
    # use SHL configuration
    ...
```

Leaving the context stops the watcher.

Alternatively:

```python
config.close()
```

## Configuration responsibility

`ConfigManager` is responsible for configuration state and provider
availability.

The router remains responsible for translation routing.

In particular, `ConfigManager` does not:

- perform translations
- decide the semantic quality of a translation
- write translation files
- save `base_lang` as a target translation
- retry the same provider as its own fallback

The intended separation is:

```text
ConfigManager
    │
    ├── provider enabled?
    ├── provider allowed?
    ├── available fallback providers?
    └── environment variables
             │
             ▼
          Router
             │
             ├── select provider
             ├── try fallback provider
             └── decide runtime fallback
                       │
                       └── display base_lang text
```

This keeps provider configuration separate from routing logic and preserves
SHL's self-healing behavior.
