Made the profile workflow describe the profile rather than its age. `incomplete` now means "missing information the site requires" and `complete` means it is not, and the add-on moves a profile between the two itself — when it is created, when it is written to, and when its owner signs in.

Nothing used to fire `complete`. Every profile stayed `incomplete` for ever, so the frontend's first-login routing diverted every user on every login, and a user who filled their profile in was sent straight back to the form they had just completed.

Which fields count is `pas.plugins.identity.required_profile_fields`. Empty, which is how it ships, means the fields the profile type itself marks required — `login` and `email` here, and the right answer for a site running its own user type or a behavior that adds a field. Set, it names them. A field counts as filled when it holds something other than `None`, an empty string, whitespace or an empty collection; `0` and `False` are answers somebody gave.

`@types` for the user type reports the site's required fields alongside the type's, so the edit form asks for everything the flow insists on. `plone.restapi` builds that list from the schema and nothing else, and without the correction a field required by the record but optional on the type would hold a profile incomplete while the form accepted a save without it — a loop produced by one registry record. The record only ever adds: a field the type requires stays required, because the type is the one that cannot store an empty value.

This matters because a provider is not obliged to send anything: GitHub withholds an email address the user marked private, a bare OIDC provider may release nothing beyond `sub`, and a magic link knows only the address it was sent to. A profile minted from one of those is missing something, and the site has to be able to insist.

`deactivated` is never entered or left by any of it. That state is a decision about an account, and "nothing is missing" is not an argument against it. @ericof
