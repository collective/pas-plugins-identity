"""PAS integration."""

#: Object id of the plugin inside ``acl_users``.
PLUGIN_ID = "identity"

#: Title shown in the ZMI.
PLUGIN_TITLE = "Identity: multi-provider external authentication"

#: Request key the callback view writes resolved credentials to. Extraction
#: reads only this key, which is what keeps the plugin off the per-request
#: path: an ordinary request never carries it.
CREDENTIALS_KEY = "__pas_plugins_identity_credentials__"

#: Marker put on extracted credentials so ``authenticateCredentials`` can tell
#: its own credentials from those of every other extractor in the chain.
EXTRACTOR = "pas.plugins.identity"
