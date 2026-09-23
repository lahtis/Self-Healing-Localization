HELP_CONTENT = """
<h1>SHL Policy Editor</h1>
<p>The SHL Policy Editor allows you to view and configure the translation
provider policy used by the Self-Healing Localization Layer.</p>
<h2>Providers</h2>
<p>Each provider represents a translation service that SHL can use when
translating text.</p>
<h3>Enabled</h3>
<p>The Enabled setting determines whether the provider is allowed to
participate in translation.</p>
<h3>Priority</h3>
<p>Priority determines the order in which providers are attempted.
A provider with a higher priority is attempted before providers with
a lower priority.</p>
<h3>Timeout</h3>
<p>Timeout defines the maximum amount of time SHL allows a provider request
to run before the request is considered unsuccessful.</p>
<h2>Provider Restrictions</h2>
<p>Provider restrictions can be used to control which features a provider
is allowed to process.</p>
<ul>
<li><strong>Allow Tags</strong> defines which HTML or markup features the provider is allowed to receive.</li>
<li><strong>Deny Tags</strong> defines which tags must not be processed by the provider. SHL handles denied HTML tags and <code>{}</code> placeholders internally, protecting them during translation and restoring them afterwards.</li>
</ul>
<h2>Policy Changes</h2>
<p>Changes made in the editor are saved to the SHL policy configuration.
SHL monitors the policy configuration and can automatically reload
changes through its hot reload mechanism.</p>
<h2>Language</h2>
<p>The user interface language can be changed from the Language menu.
Translations are provided through the SHL localization system.</p>
<h2>Saving Changes</h2>
<p>Use the Save command to save the current provider policy.</p>
<hr>
<p>This help page is also used to test HTML-aware localization in SHL.
The HTML structure should remain intact while the text content is
translated.</p>
"""
