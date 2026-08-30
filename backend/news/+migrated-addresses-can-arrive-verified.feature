A `pas.plugins.authomatic` migration can now bring verified addresses across.

The dump carries the provider's `email_verified` claim, which the converter had been discarding, so everyone arrived a stranger to their own address and stayed that way until their next sign-in.

The converter puts the claim in the identity's `claims` now, and that is the entire fix: `link` fires `IdentityLinked`, and the subscriber answers it exactly as it answers a login — applying the claims to the Profile and asking `record_verified_addresses` whether this site takes that provider's word. Nothing in the importer writes the record, and nothing should; a second path to the same write is the wrong one to maintain.

So the decision stays where it belongs. The address is recorded as proved only when the target provider's `trust_email_verification` is on, and only when the dump says a literal `true` — a string `"true"` is truthy and is not a provider saying yes. Measured on a real 17-person Google dump: 17 of 17 arrive verified with trust on, 0 of 17 with it off.

Switch the setting on before importing. Turning it on afterwards changes nothing retroactively; each person is verified at their next sign-in instead. @ericof
