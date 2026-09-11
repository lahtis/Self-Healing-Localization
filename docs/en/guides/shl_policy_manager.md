# SHL Policy Editor - Usage Guide

The SHL Policy Editor allows you to view and configure the translation
provider policy used by the Self-Healing Localization Layer.

## Providers
Each provider represents a translation service that SHL can use when translating text.

### Enabled
The Enabled setting determines whether the provider is allowed to
participate in translation.

### Priority
Priority determines the order in which providers are attempted. A provider with a higher priority is attempted before providers with a lower priority.

### Timeout
Timeout defines the maximum amount of time SHL allows a provider request to run before the request is considered unsuccessful.

### Provider Restrictions
Provider restrictions can be used to control which features a provider is allowed to process.

** Allow Tags**  defines which HTML or markup features the provider is allowed to receive.
** Deny Tags ** defines which tags must not be processed by the provider. SHL handles denied HTML tags and <code>{}</code> placeholders internally, protecting them during translation and restoring them afterwards.


### Policy Changes
Changes made in the editor are saved to the SHL policy configuration. SHL monitors the policy configuration and can automatically reload changes through its hot reload mechanism.

## Language
The user interface language can be changed from the Language menu.
Translations are provided through the SHL localization system.

## Saving Changes
Use the Save command to save the current provider policy.


> Help page is also used to test HTML-aware localization in SHL. The HTML structure should remain intact while the text content is translated.
