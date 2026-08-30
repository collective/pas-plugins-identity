A `pas.plugins.authomatic` migration can now bring verified addresses across.

The dump carries the provider's `email_verified` claim, which the converter had been discarding, so everyone arrived a stranger to their own address and stayed that way until their next sign-in. The converter carries it in the identity's `claims` now.

Who believes it is deliberately two questions rather than one.

A site that already trusts the provider at a login trusts the same claim in a document, and needs to do nothing: `link` fires `IdentityLinked`, and the subscriber answers it exactly as it answers a login.

A site that does **not** trust the provider at a login may still want the addresses its old site had already collected — a decision about the history being imported, not about every future sign-in. That is `trust_verified_emails`, or `--trust-verified-emails`, asked for per run. It leaves the site's login policy untouched, which is the point: reusing `trust_email_verification` would mean switching that policy on, importing, and remembering to switch it back, with a window in which real logins are judged by the temporary setting and nothing reporting it if the last step were forgotten.

`record_verified_addresses` takes an explicit `trust` argument for this; `None`, the default, still asks the provider record, which is what a login and every event handler must do. Only a literal `true` in the dump counts either way — a string `"true"` is truthy and is not a provider saying yes, and the flag means *believe what the dump claims*, never *call everything verified*. Measured on a real 17-person Google dump: 17 of 17 arrive verified, with the site's login policy unchanged. @ericof
