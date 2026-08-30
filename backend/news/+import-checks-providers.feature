The importer now refuses a document naming a provider this site does not have.

The identity key is `(provider, subject)`. The subject survives a migration untouched, because it belongs to the provider. The name does not: it is `pas.plugins.authomatic`'s `json_config` key on one side and a string an operator types into a control panel on the other, in a different site, after the import has finished.

A mismatch used to raise nothing at all. The import reported success, and then every migrated person signed in, matched no identity, and was handed a second account beside the one waiting for them — while the migrated Profile kept their name and their groups and belonged to nobody who could sign in. On a real 17-person dump that turned 17 migrated accounts into 17 new ones.

The check runs before anything is written, including on a dry run, and the message names what is missing, what is configured, and any name that differs only in case — which is the likeliest mistake and the hardest to see, because the two strings look identical in a control panel listing.

`allow_unknown_providers`, or `--allow-unknown-providers`, is for the deliberate order: import first, configure the providers afterwards. The identities are written either way, so the join starts working the moment a provider exists under the right name. @ericof
