# Change log

<!-- You should *NOT* be adding new change log entries to this file.
     You should create a file in the news directory instead.
     For helpful instructions, please see:
     https://6.docs.plone.org/contributing/index.html#contributing-change-log-label
-->

<!-- towncrier release notes start -->
## 1.0.0a6 (2026-09-10)

### Backend


#### Feature

- Released the server layer's claims through one serializer per scope, registered as a named multi-adapter on the site and the request, so a downstream package can add a claim or a whole scope without editing this one. It was two module-level dicts in `server/claims.py` — a scope-to-claim-names mapping and a claim-name-to-lambda mapping — which a site could only extend by mutating at import time, while the scopes vocabulary's own docstring advertised the extension as though it were supported. A serializer declares its claim names as a class attribute and produces their values in `__call__`, and both halves are needed: `scopes_supported`, `claims_supported` and the consent screen all ask what a scope releases with no user in hand, so a scope that could only serialize somebody would be released without ever being offered or consented to. A new scope reaches the discovery document, the client registration form, the consent screen and issued tokens from that one registration. `sub`, `iss`, `aud`, `exp` and `iat` are reserved and a serializer returning one is ignored on that key. Empty values are dropped for every serializer alike, and the rule is absence rather than falsehood, so `email_verified` still reports `False`. @ericof [#69](https://github.com/collective/pas-plugins-identity/issues/69)
- Offered `@my-profile` as a `plone.restapi` expandable component, so a signed-in user's profile state rides along with the content request Volto was already making rather than costing a second round trip on every navigation. It is registered on any content rather than on the site root alone, and publishes the site's own `@my-profile` URL whatever page carries it — the endpoint is registered for the site root and resolves nowhere else. For an anonymous caller the component is absent entirely rather than an `@id`: Volto's `apiExpanders` cannot mark an entry authenticated-only, so the expansion is asked for on every page of a public site, and answering with nothing leaves such a response exactly as it was. `test_zero_wake.py` now covers an expanded content request, because a catalog-only read matters more when it runs on every page view than when it ran once. `services/myprofile.py` became a package, with the endpoint, the component and the body they share in separate modules. @ericof [#71](https://github.com/collective/pas-plugins-identity/issues/71)
- Added `pas.plugins.identity.api`, a public façade carrying the interfaces, events, content classes and functions a downstream package needs, so nothing has to reach into `core` or `server` to find them. @ericof [#73](https://github.com/collective/pas-plugins-identity/issues/73)
- Added `server_unreleased_groups`, so a site can keep chosen groups out of the `groups` claim without subclassing a serializer. `AuthenticatedUsers` stays out whatever it says. @ericof [#75](https://github.com/collective/pas-plugins-identity/issues/75)
- Added a `global_roles` behavior to user groups, carrying the site-wide roles a group grants. It reads and writes the groups control panel rather than storing a copy, so the two cannot drift, and it is guarded by a new Manager-only permission. Export and import carry it. @ericof [#76](https://github.com/collective/pas-plugins-identity/issues/76)



### Frontend


#### Feature

- Asked for the caller's profile with the content request instead of separately. `@my-profile` is registered in `apiExpanders` for `GET_CONTENT`, and the profile gate now prefers the answer that arrived with the page, falling back to its own request on a route that fetches no content — `/login`, `/identities`, a control panel — or against a backend too old to offer the component. The expanded answer is used only when the content in the store is the page being rendered: Volto keeps the last content it loaded, so trusting it anywhere else would read a stale answer to a question whose whole point is freshness. `FirstLogin` and `Identities` no longer ask at all while anonymous; both routes are registered like any other, so an anonymous visitor opening them directly fired requests that could only answer 401. @ericof [#71](https://github.com/collective/pas-plugins-identity/issues/71)



### Project


#### Documentation

- Added a how-to for serializing a claim, covering both shapes of the job: adding a claim to a scope the package ships, and registering a scope of your own. Two pages said a site adding a field to its `UserProfile` type had no claim to put it in, and that the extension point for it was deliberately not built; both are corrected, and the claims reference gained the contract a downstream serializer is written against. @ericof [#69](https://github.com/collective/pas-plugins-identity/issues/69)
- Documented `my-profile` as an expandable component in the endpoints reference — where it is registered, which URL it publishes, and why it is the one component here that answers an anonymous caller with nothing rather than a URL — and added an API expanders table to the frontend reference. @ericof [#71](https://github.com/collective/pas-plugins-identity/issues/71)
- Documented the public Python API in a new reference page, and pointed the driver, enricher, claim-serializer and events guides at `pas.plugins.identity.api` instead of the modules their names are implemented in. @ericof [#73](https://github.com/collective/pas-plugins-identity/issues/73)
- Documented `server_unreleased_groups` on the claims and settings reference pages. @ericof [#75](https://github.com/collective/pas-plugins-identity/issues/75)
- Documented the group `global_roles` behavior and its Manager-only permission. @ericof [#76](https://github.com/collective/pas-plugins-identity/issues/76)
- Corrected the dispatch example in the profile enricher guide. The walrus bound the result of the `is None` comparison rather than the handler, so the example raised `TypeError: 'bool' object is not callable` on every login it matched a driver on — the only case it existed for — and `enrich_profile` caught it, leaving a logged traceback and an enricher that appeared never to run. @ericof 



## 1.0.0a5 (2026-09-09)

### Backend


#### Breaking

- A provider's property map may only write the four Profile fields a login actually writes: `fullname`, `home_page`, `description` and `location`. The target is a `Choice` over `pas.plugins.identity.UserFields` rather than free text, so a row naming anything else is refused by the API with a 400 and by GenericSetup on import, where before it was stored, exported, and dropped on every login without a word. `MAPPABLE_FIELDS` is now the single definition the login filter, the principal document format and the control panel all read. The default maps lost the rows that did nothing: no driver seeds `email` any more, and `plone-identity` no longer seeds `picture_url`. Neither was ever applied — an address is appended by `sync_addresses` and a portrait is synced from the `picture_url` claim. Profile version 1004 removes such rows from a site that has them, logging each one. @ericof [#43](https://github.com/collective/pas-plugins-identity/issues/43)
- `@group-members` rows now point `@id` at the member's Profile. It was the listing's own URL with the userid appended, which is not a resource: the service takes exactly one path segment, so following it answered `400`. `profile_url` is unchanged and now holds the same URL, so a client already following it needs no change. @ericof [#44](https://github.com/collective/pas-plugins-identity/issues/44)


#### Feature

- Order a group's membership in the catalog. The identity catalog gained a `sortable_title` index, filled by Plone's own indexer from a Profile's title, and `@group-members` sorts on it. It previously read every member of a group and sorted the whole list in Python to render a page of it. @ericof [#40](https://github.com/collective/pas-plugins-identity/issues/40)
- Grouped the identity settings into tabs. `IIdentitySettings` declared thirteen fields and no fieldset, so the settings form was one flat column; it is now four — Login, User and group content, Portraits and Audit log. `IProfileSettings` is grouped into the same three the settings reference already documents it in: where principals are filed, which states count, and the profile gate. @ericof [#41](https://github.com/collective/pas-plugins-identity/issues/41)
- Put the profile and group settings on the control panel. The thirteen records in `IProfileSettings` decide where principals are filed, which of their workflow states count for enumeration, and what a profile must carry before its owner is let past the gate — and the panel named `IIdentitySettings` alone, so they were reachable through the generic registry editor and nowhere else. Both the REST panel and the Classic form now serve a schema derived from the two, which addresses the records that already exist rather than creating any. @ericof [#42](https://github.com/collective/pas-plugins-identity/issues/42)
- Moved a `@group-members` row behind `IGroupMemberSerializer`, a multi-adapter on the site and the request, so a deployment can add a field to a membership row by subclassing `GroupMemberSerializer` and registering it for its own browser layer. Adding a field previously meant replacing the service. It adapts the site rather than the brain because a brain carries no `__provides__` and cannot be marked, and the only registration a brain could carry would answer for every brain in the site. @ericof [#45](https://github.com/collective/pas-plugins-identity/issues/45)
- Added `GET @identity-providers/<id>/export`, which returns one provider as a self-contained registry fragment ready to paste into a profile's `registry/` directory: the `IProviderRecords` fields as one grouped node, and a `<record>` per driver setting carrying its own field type, since those belong to no interface. Exporting the whole registry was not a substitute — `runExportStep` dumps every package's records, and importing that document fails on one of them. A trailing path segment on `@identity-providers/<id>` is now refused rather than ignored. @ericof [#47](https://github.com/collective/pas-plugins-identity/issues/47)
- A driver now carries the connection facts about its own provider: `static_metadata` for a provider that publishes fixed endpoints, and `issuer` for one whose issuer the driver knows. Both were tables keyed by driver id in `core/flows/metadata.py`, which no driver mentioned and no third-party driver could add a row to. GitHub's four endpoints are now on `GitHubDriver`, beside the `enrichment_endpoint()` that reads one of them, and Google's issuer is on `GoogleDriver`. `GitHubDriver` also seeds the map GitHub can actually fill: `bio`, `blog` and `location`. @ericof [#66](https://github.com/collective/pas-plugins-identity/issues/66)


#### Bugfix

- Show a driver's own defaults on the add-provider form. `@identity-drivers` now serves each driver's real starting values as the schema defaults Volto seeds an add form from, so choosing Google no longer presents an empty scope box and an unticked "this provider's email verification counts" while saving a provider that has both. The form and the stored record are filled from one function and can no longer disagree. A `Tuple` field's default is also serialized as a JSON array rather than a Python tuple. @ericof [#37](https://github.com/collective/pas-plugins-identity/issues/37)
- Stop this package's indexers from answering for every catalog. `login` and `SearchableText` were declared for the Profile alone, which registers an indexer against any catalog that asks — and a Profile is ordinary content, catalogued in `portal_catalog` as well. So a Profile's entry in site search was its full name, login and email, and its biography was not searchable at all. Both are now bound to the identity catalog, where they are unchanged, and site search gets an answer of its own: the title, the userid and the biography. Neither the login nor the address, which have no business in a site's search box. @ericof [#38](https://github.com/collective/pas-plugins-identity/issues/38)
- `@group-members` no longer wakes one object per row. Rendering a row filled `profile_url` by userid, which searches the catalog a second time and then activates the Profile to ask for its URL, so drawing a page of a group cost one activation per person on it — on the endpoint whose whole premise is that a group of a thousand is one query rather than a thousand object loads. A brain already knows its URL. The endpoint has also joined the activation-counting suite that covered the PAS plugins and never covered it, which is where the regression landed unseen. @ericof [#57](https://github.com/collective/pas-plugins-identity/issues/57)


#### Internal

- Replaced `authlib.jose` with `joserfc` everywhere a JWT is minted or read: the authorization server's tokens and key ring, the `id_token` a provider returns, the magic link's own signature, and a back-channel logout token. `authlib.jose` is deprecated and Authlib keeps it only until 2.0.0; the OAuth client that carries every request is not deprecated and stays. `joserfc` is now declared as a dependency rather than arriving through Authlib. Two tokens are refused that were not before: an `id_token` and a magic link with no `exp` claim, which the old library treated as a token that never expires. `tests/test_protocol_libraries.py` fails when either library is imported outside the five modules that own a protocol boundary. @ericof [#48](https://github.com/collective/pas-plugins-identity/issues/48)


#### Tests

- Added `tests/core/indexers/test_declarations.py`, asserting that everything the identity catalog declares is actually answered, and that nothing this package declares answers for a catalog it should not.

  The issue asked for an explicit indexer per index and per metadata column. Ten of the fourteen would have restated an attribute name the `IIndexableObject` wrapper already resolves, and a pass-through indexer that has itself gone stale is exactly as silent as no indexer at all. So the risk is tested instead of restated: a fully filled Profile and Group are required to leave a value in every index and every column, which `core.doctor` cannot check for itself — it reads the object through the same attribute the catalog does, and finds both sides equally empty.

  The other half is which catalog answers. `@indexer(IUserProfile)` does not register for one argument; it registers for every catalog in the site, which is what made the leak fixed in #38 invisible. Every `IIndexer` this package registers is now required to name the identity catalog, with the site-search answer the single exception, pinned by identity rather than by name. @ericof [#39](https://github.com/collective/pas-plugins-identity/issues/39)
- Extended the registry export tests to prove the export can be read back, rather than only that it mentions a provider. The fixture provider now carries an icon, both claim maps and colours, and the module exports it, wipes the site, imports this package's records and compares every field. It also covers the `<records interface= prefix=>` form a hand-written profile uses, which is not the form the exporter emits. @ericof [#46](https://github.com/collective/pas-plugins-identity/issues/46)



### Frontend


#### Feature

- The property map's target column is a picker over the fields a login writes, built from the vocabulary the provider schema serves rather than from a list held here. It was a text box, which accepted `email`, `portrait` and `username` alike and stored rows that did nothing. A backend that serves no vocabulary still gets the text box. @ericof [#43](https://github.com/collective/pas-plugins-identity/issues/43)
- Both content views now render a `belowTitle` slot, under the heading and above the description, so a deployment can put its own component on a profile or a group page without shadowing either view. `aboveContent` and `belowContent` already reached both pages, because Volto renders those around any view registered in `config.views.contentTypesViews`; nothing outside a view can place anything inside one, which is what the new slot is for. @ericof [#51](https://github.com/collective/pas-plugins-identity/issues/51)


#### Bugfix

- Label the rows of a provider's property and group maps. Volto's object-list widget takes a row's label and the add button's noun from the row schema's own title, and neither map declared one, so the Mapping tab read `UNDEFINED #1` above `+ Add undefined`. The two columns of each row are labelled and translated as well, where they had been the raw field names. @ericof [#53](https://github.com/collective/pas-plugins-identity/issues/53)
- `ProfileView` shows the login when a Profile has no full name, instead of "Unnamed user". It fell back to `content.title`, which a Profile never carries: `title` is computed on the backend rather than stored, so `plone.restapi` does not serialize it, and the test fixture supplied one no real payload has. The heading now follows the same order the backend's own `Title()` does — full name, login, userid. @ericof [#60](https://github.com/collective/pas-plugins-identity/issues/60)


#### Internal

- Split `actions/index.ts` and `reducers/index.ts` into one module per domain — login, magic link, identities, profile, groups, account, drivers, providers, clients, keys and consent — with the request-lifecycle factory the reducers share in `reducers/factory.ts`. Both `index.ts` files stay as the re-export surface, so nothing importing from the package root changes. The tests moved with them: 46 test files became 55, and the count is unchanged at 563. @ericof [#49](https://github.com/collective/pas-plugins-identity/issues/49)
- Split `src/types.ts` into `src/types/api.ts` and a new `src/types/content.ts`, re-exported from `src/types/index.ts` so every existing import keeps resolving. The new file describes `UserProfile` and `UserGroup` as Plone content, tied to `@plone/types` with `Pick` rather than `extends`: neither type carries Dublin Core or blocks behaviors, so most of `Content` is absent from the payload and inheriting it would promise fields no view can read. Every deviation is documented against a measured serialization. `providerFormSchema` and `clientFormSchema` are no longer `Record<string, any>`. @ericof [#50](https://github.com/collective/pas-plugins-identity/issues/50)



### Project


#### Documentation

- Grouped the site-wide settings reference under the control panel's own tabs, so a reader working through the page and an operator working through the form are looking at the same four questions in the same order. @ericof [#41](https://github.com/collective/pas-plugins-identity/issues/41)
- Documented how to map a provider's claims onto profile fields, in the guide to configuring a provider: the four targets, why an address and a portrait need no row, and what happens to one that names something else. Corrected the claim, repeated on four pages, that this add-on ships no GenericSetup upgrade steps — the default profile is at version 1004 and each step is now listed. @ericof [#43](https://github.com/collective/pas-plugins-identity/issues/43)
- Documented what a `@group-members` row holds, key by key, how a deployment adds one, and why the serializer adapts the site rather than the brain. The endpoints reference described what the endpoint was for and never said what came back. @ericof [#44](https://github.com/collective/pas-plugins-identity/issues/44)
- Documented how to ship a provider in a profile, using the new per-provider export, and why the fragment has one grouped node for the provider's own fields and a typed `<record>` per driver setting. @ericof [#47](https://github.com/collective/pas-plugins-identity/issues/47)
- Said which library does what, in the two READMEs and the documentation index: authlib carries the OAuth requests and `joserfc` reads the tokens. The security guarantees named a grep-level CI rule enforcing that protocol messages are never constructed by hand; no such rule existed, and the table now names the test that does it. @ericof [#48](https://github.com/collective/pas-plugins-identity/issues/48)
- Added a how-to guide covering the three slots a profile page and a group page expose, with a worked example of a downstream package registering a row of badges into `belowTitle` and narrowing it to profiles with a predicate. The frontend reference lists the three. @ericof [#51](https://github.com/collective/pas-plugins-identity/issues/51)
- Corrected the claim that a GenericSetup export omits provider secrets. It carries them as their stored values, and the `plone.registry.field.Password` type marks a record rather than encrypting it — so an export of a provider is a credential, not a document. The statement appeared eight times, including in the threat model, where the leak was listed as prevented, and in the security guarantees table. What limits exposure is who may take an export, which needs `Manage portal`. @ericof [#59](https://github.com/collective/pas-plugins-identity/issues/59)
- The driver contract now lists `static_metadata` and `issuer`, with two rules covering them, and explains why a provider's endpoints belong to its driver. The how-to guide's example driver declared a `base_url` of its own and would have been refused at login for having no metadata source; it now extends `IOIDCSettings` and the guide opens by asking where the endpoints come from. @ericof [#66](https://github.com/collective/pas-plugins-identity/issues/66)


#### Tests

- Added a Playwright script that drives the add-provider form through Volto, chooses a driver, and photographs every tab it produces. It writes to the Sphinx build directory rather than to the documentation's screens, so it reports what an operator sees without adding an image any page has to reference. @ericof [#37](https://github.com/collective/pas-plugins-identity/issues/37)



## 1.0.0a4 (2026-09-08)

### Backend


#### Bugfix

- The four sign-in endpoints answer on a site whose anonymous visitors cannot view it.

  `@login-providers`, `@identity-callback`, `@magic-link` and `@magic-link-confirm` each said "anonymous by design" in their own registration and were each declared against `zope2.View`, which is not that. `zope2.View` is looked up as a permission and inherited from the root, so a site that takes `View` away from `Anonymous` — a closed intranet, which is the kind of site most likely to want federated login — answered every one of them with a 401. The login page could not list its providers, a provider redirect could not be completed, and neither half of the magic link could be reached; local login kept working throughout, because `plone.restapi` declares its own `@login` as `zope.Public`. All four are declared that way now, which `AccessControl.security.protectClass` special-cases into `declareObjectPublic()` so that no role is required at all. Nothing else moved: the callback is still authorized by the single-use state bound to its signed flow cookie, and the magic link by its rate limiter and its signed, single-use, short-lived token. @ericof [#34](https://github.com/collective/pas-plugins-identity/issues/34)
- A migrated account reaches the profile enrichers with the provider's payload.

  Both authomatic paths — `migration.authomatic.migrate` on a live site, and the `--from-authomatic` dump conversion — link each identity through the plugin, which fires `IdentityLinked`, whose subscriber runs the site's installed `IProfileEnricher` utilities. That much always worked. What those enrichers were handed did not: each path built its claims snapshot with an empty `raw`, and `raw` is the whole contract, because the property map deliberately refuses a structured claim and an enricher is what a site has instead. So every enricher ran against an empty document, wrote nothing, reported nothing wrong, and a migration produced Profiles missing exactly the fields the enricher had been installed to fill. The payload now comes across: for a live migration, the attributes authomatic parsed out of the provider's response layered over the document it kept in `data`, in the order its own property sheet resolves them; for a dump, the `properties` the documented extraction wrote. Credentials do not come with it. Authomatic keeps a serialized `Credentials` holding the account's access and refresh tokens on every identity, and a claims snapshot is stored on the identity record and written out again by the exporter, so a new `core.utils.claims.scrub_payload` strips that and the other credential-bearing key names on the way in. An identity already linked is still skipped, so re-running an import does not enrich the accounts that arrived the first time. @ericof [#35](https://github.com/collective/pas-plugins-identity/issues/35)



### Frontend

No significant changes.




### Project


#### Documentation

- The profile enricher guide says what a migration hands you.

  Its table of payload shapes listed both authomatic paths as `Empty`, which described the behaviour accurately and made it look intended. It is a fourth shape now — authomatic's own record for that account, closest to the plain OAuth2 row — with the two things an enricher author has to know beside it: the snapshot dates from whenever that person last signed in to the old site, so it can lack a key the provider sends today, and an enricher runs once per identity the import actually links, so re-running an import does not reach accounts that arrived on the first one. @ericof [#35](https://github.com/collective/pas-plugins-identity/issues/35)



## 1.0.0a3 (2026-09-07)

### Backend


#### Breaking

- A login may be changed by a Manager, and only after the account exists.

  `login` was declared with the same write permission as `fullname`, which the owner of a Profile holds on their own Profile because that is what self-service means. Correcting your name and becoming somebody else were the same action, and a Site Administrator could rename anybody. It is half of the case-folded index user enumeration queries, so rewriting it moves an account away from every sign-in, every Sharing entry written against the old name, and every provider that maps a user by it. It now has a permission of its own, `pas.plugins.identity.content.editlogin`, and the interesting part is where it applies: `user_profile_workflow` grants it to `Manager` alone in every state, while the container Profiles are filed in grants it to `Manager` and `Site Administrator` beside the add permission. An add form checks a field against the container and an edit form against the object, so anybody who may create an account may name it and only a Manager may rename one afterwards. The machine paths are untouched — `doAddUser` elevates to Manager and writes through the Dexterity factory, which consults no field permission. Existing sites need the 1002 upgrade step: a workflow import does not touch content that already exists, and until its permission maps are rewritten the new permission is acquired rather than managed on every Profile a site already has. @ericof 
- The Profile's fields moved onto behaviors, and the addresses onto a tab of their own.

  `emails` and `email` are now declared by `pas.plugins.identity.email_addresses`, and `home_page`, `location` and `image` by `pas.plugins.identity.profile_details`. The type itself declares `login`, `fullname` and `description` and nothing else. Both behaviors are schema-only, so nothing about storage changed: a Profile still answers `profile.emails`, the catalog still indexes `email`, and the properties that normalize a write and derive the single address are still what runs. A stock site sees the same fields, with the two addresses moved to an **Email** tab — which is where they belong, being the only fields read under `View Personal Identifiable Information` rather than the ordinary view permission. A site running its own user type now composes the same Profile out of the same parts rather than redeclaring five fields and keeping their permissions in step by hand. What breaks is code that read those fields off `IUserProfileSchema`: they are on the behaviors' schemata now, and `iterSchemata` is what sees all of them. `completeness` was one such reader, and would have judged a profile with no address complete. @ericof 
- `INDEXES` and `METADATA` no longer exist in `pas.plugins.identity.core.catalog`.

  They described the user catalog's shape, and `identity-catalog.xml` describes it now, so keeping a Python copy would only have meant two lists that agree until they do not. `PROFILE_METADATA` and `GROUP_METADATA` stay where they are: they say which columns mean something on which of the two types, which is not something the catalog's own XML can express. Also removes `pas.plugins.identity.setuphandlers.catalog` and the three builders in it, which the import step replaces. @ericof 


#### Feature

- A deployment can now write its own fields onto a Profile at login, through a named `IProfileEnricher` utility.

  The claim-to-field property map carries a scalar from a provider document to one of four fields, and an add-on whose behavior adds a field of its own could express nothing through it: the target has to be in `WRITABLE_FIELDS`, and a claim resolving to a list or a mapping is read as an absent claim rather than written as a Python representation. That refusal is deliberate — it is what stops an OIDC `address` object landing in somebody's location — so the answer is a second path rather than a wider map. An enricher runs after this package's own writes and after the addresses have been recorded, is handed the Profile, the whole normalized claims mapping including the provider's `raw` payload, and the provider configuration the login came through, writes what it likes, and returns the names of the fields it changed. The provider is what keeps a site running several of them from turning into guesswork: `driver_id` says what shape the payload is, `provider_id` tells two deployments of one kind apart, and the provider itself is `None` on the paths that carry no payload either. One modification event is fired for all of them together, before `reconcile`, so a required field an enricher fills counts towards completeness in the same login. Each enricher gets a persistent mapping private to its registered name, because this package's own "the provider may replace only what it wrote" fence compares scalars and answers the wrong question about a list — an enricher that ignores the mapping will hand back an entry its owner deleted, on every login. One that raises is logged and skipped: an add-on defect must not lock out the site's users, including whoever would remove it. See the new `docs/how-to-guides/write-a-profile-enricher.md`. @ericof 
- The user catalog's indexes, columns and lexicon are declared in GenericSetup XML, with import and export steps of their own.

  `profiles/default/identity-catalog.xml` is now the source of truth, applied by a new `identity-catalog` import step and readable back out by the matching export step. Adding an index or a metadata column is an edit to that file: no Python, and `remove="True"` takes one away, which the hand-written handlers could never do. The stock GenericSetup `catalog` step cannot reach this catalog -- it resolves its target with `queryUtility(ICatalogTool)`, which answers `portal_catalog` and has no notion of a second catalog -- so a step of our own is what was missing. The adapter was not: `ZCatalogXMLAdapter` is registered for `IZCatalog` and has adapted this catalog all along, so `IdentityCatalogXMLAdapter` subclasses it to change one thing, the filename. That name is load-bearing rather than cosmetic: a `catalog.xml` in this profile would not be ignored, it would be applied to the site catalog. Applying the profile still does not populate what it creates, so `pas.plugins.identity:rebuild-catalog` remains the second half of any such change. @ericof 


#### Bugfix

- Group membership written by an import now takes effect.

  The importer wrote the fields and called `reindexObject()`, which maintains `portal_catalog` and fires no event. The identity catalog is maintained entirely by the subscribers in `core.indexers`, which answer `IObjectModifiedEvent` and three others, so every object came out of an import correct and every brain stayed stale. `getGroupsForPrincipal` reads `group_ids` off the brain, so an import wrote the membership and nobody was in the group; a re-imported login or address was equally invisible, which meant an account could still be enumerated under the name it had stopped using. Newly created principals were never affected, because `api.content.create` fires `ObjectAddedEvent` and the catalog does listen for that: it was only the subsequent field writes that were lost, and applying membership is always one of those. The three call sites now fire `zope.lifecycleevent.modified`, which is what the rest of the package already did. The existing tests missed it because they assert the object, or a count, and the count was right. @ericof [#30](https://github.com/collective/pas-plugins-identity/issues/30)
- Converting a `pas.plugins.authomatic` dump now reads the target site's property map.

  `convert_authomatic` mapped the dump onto Profile fields with its own hardcoded table, which never consulted the provider record the site had configured. A dump carries the provider's own vocabulary, so that table was a guess, and where it disagreed with the site the site lost. GitHub is the worked example: authomatic's parser sets `link` from `html_url`, so `link` to `home_page` gave every migrated person their GitHub profile page as their homepage and discarded the real one in `blog`, while a `bio` the table had no name for was dropped entirely. The site's map for the provider each user signed in with is now applied first, and the built-in table fills only the fields it leaves unset. `identity-importer --from-authomatic` therefore converts inside the site rather than on the way in; the dump's shape is still checked before Zope starts, so pointing it at the wrong file is still answered in a second. A provider with no record in the target site still converts on the built-in table, and is now counted and warned about rather than losing fields quietly. @ericof 


#### Internal

- The three behaviors mark themselves with `@provider(IFormFieldProvider)` rather than a trailing `alsoProvides`.

  Identical in effect -- a `model.Schema` subclass directly provides nothing, so the `directlyProvides` the decorator performs discards nothing an `alsoProvides` would have kept -- and it is what the behaviors in `plone.app.contenttypes` and `plone.app.dexterity` use. The marker now sits on the class instead of sixty lines below the schema, where its absence is the thing to notice: without it the fields store, index and serialize correctly and appear on no form. @ericof 



### Frontend

No significant changes.




### Project


#### Documentation

- Added a how-to for adding an index or a metadata column to the user catalog, and documented the `identity-catalog` import and export steps. @ericof 
- Added a how-to for writing a profile enricher.

  Covers when the property map is the right answer and when it runs out, the four arguments an enricher is handed, why it keys on the provider rather than on a key it hopes means something, why it has to remember what it wrote, and what `claims["raw"]` actually holds — which is the userinfo document only for a plain OAuth2 provider such as GitHub, the token's claims for any provider issuing an `id_token`, and nothing at all on a magic-link confirmation or an address verification. @ericof 
- Documented that an authomatic conversion reads the target site's property map, and that configuring the providers first decides which fields survive it. @ericof 
- Split the two concept pages on the boundary they already declared.

  `About users as content` is the mechanism: what the marker contracts promise, and why the plugin creates a type it has never heard of. `About profiles and groups` is what the fields a Profile owns are used for. The comparison with `Products.membrane` and the reason membership is kept on the member had been written out in full on both, so a reader met the same argument twice in slightly different words, and a correction had two places to land — including the version the membrane reading was verified against. Each argument now has one home, and the other page points at it rather than restating it. @ericof 



## 1.0.0a2 (2026-09-07)

### Backend


#### Feature

- Groups nest by containment: a `UserGroup` may be added inside a `UserGroup`, and everybody in the inner group is in the outer one.

  The tree is now a second way of writing the edge `group_ids` already carried, and the two are unioned — a group can be filed inside one group and name others, and a group that does both contributes the edge once. Everything that reads membership walks one graph and cannot tell which way an edge was written, so `getGroupsForPrincipal`, `getGroupMembers`, `getNestedGroupIds` and `@group-members` all follow with no change to their contracts. A contained group is a group of the site like any other: enumerated, grantable on the Sharing tab, and resolvable by id, which it was not before. Because group ids are what local roles and memberships are stored in terms of and object ids are only unique within a folder, a second group claiming an id already in use is now refused when it is created or renamed. Export and import carry the hierarchy in a new optional `container_group` key, so a restored site comes back with the shape it had rather than flat. @ericof 


#### Bugfix

- Added the upgrade step that lets an existing site nest groups by containment.

  An FTI is a persistent object written into `portal_types` at install, so a site installed before containment kept an empty `allowed_content_types` on the `UserGroup` type: the add menu offered nothing inside a group, and nothing said why. The profile is now at version `1001`, and a site behind it is offered a step that re-imports `typeinfo`. Upgrade steps live one package per version under `upgrades/`, each with its own `configure.zcml` — this is the first of them, so it sets the shape for the next. @ericof 
- Deleting a Plone site that holds a Profile no longer fails with `CannotGetPortalError`.

  The indexing subscribers asked the *current* site for the catalog, which is a different question from the one they had the answer to: they are handed the object, and the object knows which site it is in. The two agree on every request and disagree exactly where nothing has called `setSite` — a `zconsole` script working on `app`, and the deletion of a site from the Zope root, which is what `DELETE_EXISTING=1 make create-site` does. There the lookup raised out of the handler and took the deletion with it, naming neither the site nor the catalog. The catalog is now acquired from the object, so the unindex happens rather than merely not raising, and `query_catalog` answers `None` instead of raising when there is no current site at all. @ericof 


#### Documentation

- Added the PyPI badges to the README.

  The package is on PyPI as of `1.0.0a1`, and `pyproject.toml` names this file as the long description — so the version and the interpreters it declares are now visible at the top of the page somebody lands on before deciding to install it. @ericof 



### Frontend


#### Documentation

- Added the registry badges to the README.

  The package is on npm as of `1.0.0-alpha.1`. The README carries its version badge and, beside it, the version of the backend package it requires — the two are released together, and a reader on npm cannot otherwise see whether the halves they are about to install match. @ericof 



### Project


#### Documentation

- Documented that groups nest by containment as well as by `group_ids`.

  The concepts page now states both ways of writing the edge and that the graph unions them, along with the two consequences a reader will otherwise meet as surprises: clearing `group_ids` does not un-nest a group that is nested by containment, and a group id is unique across the site rather than within a folder. The reference tables, the glossary entry and the principal-document format gained the same, the last of them describing the new optional `container_group` key and the import pass that reads it. @ericof 
- Said in the READMEs that the packages are published.

  `1.0.0a1` is on PyPI and on npm, so `uv add pas.plugins.identity` and adding `@plone-collective/volto-identity` are now instructions that work rather than instructions for later. All three READMEs carry the registry badge for what they describe, and the packages table names each registry as a link rather than as a word. @ericof 



## 1.0.0a1 (2026-09-05)

### Backend


#### Breaking

- A registered OAuth client's `scope` is a list picked from a vocabulary rather than one line of space-separated text. The control panel offers the scopes this server releases claims for, which is what the discovery document advertises. A stored string is still read, so nothing needs migrating, but `@identity-clients` now serializes `scope` as a list and `ClientConfig.scope` holds one; the space-joined wire form is `ClientConfig.scope_string`. @ericof [#9](https://github.com/collective/pas-plugins-identity/issues/9)
- An OAuth client is an interface, and its redirect URIs are validated.

  `POST @identity-clients` stored `redirect_uris` exactly as it received them. No scheme check, no rejection of fragments, no loopback rule — so `javascript:alert(document.cookie)` could be registered and would later be handed to a browser redirect at the end of an authorization flow. `grant_types` was likewise stored unchecked and refused much later at the token endpoint, where it reads as a client bug rather than as a registration mistake.

  `IClientRecords` is the schema now, with the rules on the fields: a redirect URI must be absolute, must carry no fragment, must use `https`, a loopback address or a private-use scheme, and may not contain a wildcard that exact matching can never satisfy. RFC 6761 reserves the whole `.localhost` name space to loopback, so a development host such as `http://id.localhost` is accepted and `http://anything.else` is not. Grants are a `Choice` over what the token endpoint actually implements, which is what discovery advertises.

  `redirect_uris` and `grant_types` are validating properties rather than plain attributes, because a rule only the constructor enforces is a rule with a door in it — this package's own demo assigns to one of them directly.

  `@identity-clients` serves the schema beside the listing, so the panel is built from it rather than from a second description in TypeScript. @ericof 
- Driver and provider settings are `zope.schema` interfaces, serialized by `plone.restapi`.

  `BaseDriver.config_schema()` returned a dict this package had invented — `{"type": "string", "title": "Client ID", "required": True, "secret": False, "order": 20}` — and the Volto add-on turned it into a form in 529 lines of TypeScript. It was wrong four ways at once: not a title in it could ever reach a `.po` file, no form could be built from it except by whoever reimplemented it, nothing validated a request against it, and `order`, `secret`, `choices` and `type` each reinvented something `zope.schema` already had.

  A driver now names a `settings_schema`. `IOAuth2Settings` carries the fields every OAuth2 provider needs; `IOIDCSettings`, `IGitHubSettings`, `IPloneIdentitySettings` and `IEmailSettings` extend or replace it. `client_secret` is a `Password`, so the field type *is* the secret flag and there is none to forget; `userid_source` is a `Choice` over a vocabulary; `scope` a `Tuple`; the issuer is placed with `order_before` rather than by spacing numbers ten apart. Per-driver defaults stay on the driver class, because a subinterface redeclaring a field to change its default would give it a fresh creation order and the field would silently jump to the end of the form.

  `@identity-drivers` and `@identity-providers` now serve ordinary JSON schemas, built with the same three `plone.restapi` calls that answer `@controlpanels`. The provider's own half comes from `IProviderRecords` — the interface its registry records were already bound to, so the form and the storage cannot describe different things — and it gained a Style fieldset, `color_picker` on both colours, and an `icon` that is a `schema.Bytes` holding the upload envelope Plone stores `site_logo` in. An icon that is not a parseable SVG is refused by a field constraint that runs the real parser, and what is stored is the sanitized document.

  **The consumers read fields rather than dict keys**: coercion on `ICollection`, masking on `IPassword`, the registry field on the field type, and discovery on whether `issuer` is in the schema. A site's own driver must declare `settings_schema` instead of `config_schema()`. @ericof 
- Users and groups as content is no longer an extra. Installing the add-on installs it, and there is no `pas.plugins.identity.content:default` profile any more.

  **A site installed by an earlier version must reinstall the add-on.** There is no upgrade step, deliberately: the package is `1.0.0a0` and nothing is released. Until it is reinstalled such a site looks installed and has no content types, no catalog and no `identity_profile` plugin — uninstall and install it again from the add-ons control panel, or apply `pas.plugins.identity:default` from `portal_setup`. Reinstalling leaves every existing `UserProfile` where it is.

  The `[content]` extra is gone from `pyproject.toml` and `plone.app.dexterity` is an ordinary dependency. It always was one in practice: it ships with Plone, so the extra spared nobody anything while creating a second configuration of every code path that touches a user. Every bug found in the last week of that arrangement was in the seam.

  `pas.plugins.identity.content` merged into `pas.plugins.identity.core`, flat: `content/catalog.py` is `core/catalog.py`, `content/pas.py` is `core/pas/profile.py`, the markers and the settings schema moved into `core/interfaces.py` and `core/controlpanel/interfaces.py`, and the two `setuphandlers` modules became one package with the catalog builders and the PAS plugin installers in modules of their own. `IIdentityContentLayer` is gone and every registration that was bound to it is bound to `pas.plugins.identity.interfaces.IBrowserLayer`. The `IProfileSupport` utility is gone too — it existed only so core could ask the other layer a question without importing it, and there is nothing on the other side of that boundary any more.

  The GenericSetup profiles merged the same way. One `default` installs the control panel, both PAS plugins, both content types with their workflows, and the catalog; one `uninstall` removes them; `rebuild-catalog` is now `pas.plugins.identity:rebuild-catalog`. The uninstall profile also removes the registry records the old one left behind — the four naming the user and group types, and the gate's three.

  What follows from the merge, rather than from the move:

  *   A federated first login never writes a `source_users` row. It used to, on a site without the extra, because there the row was the only record the user had; now the Profile is, and a row beside it is a second record of the same person that nothing keeps in step.
  *   `api.user.create` mints a Profile on a site nobody has signed in to yet. The container is created by whoever needs it first rather than at install time, so the gap where the first user added to a fresh site got a `source_users` row and no Profile is closed.
  *   An offered address list is never settled by guessing. A driver that returned several addresses and no answer used to have the first one taken on a site with nowhere to ask; every site can ask now.
  *   A login through an identity whose account is gone is restored by the subscriber that mints Profiles, and says so at warning level first — an account reappearing is not what an operator who deleted one expects. @ericof 


#### Feature

- Added `allowed_groups`, a per-provider list restricting sign-in to members of named groups. An entry matches either a name the provider sends or a local group id the map turns one into. It is checked on every sign-in, so a membership revoked at the provider stops granting access. The person refused is told only that the sign-in failed; the reason, naming both what arrived and what it mapped to, goes to the log and to the manager-only audit trail. @ericof [#4](https://github.com/collective/pas-plugins-identity/issues/4)
- Added `accept_string_booleans`, a per-provider switch for a provider that sends `email_verified` as the string `"true"` rather than as a boolean, as Oracle Access Manager and some Keycloak configurations do. Against such a provider every address silently arrived unverified. Only `"true"` and `"false"` are read; `1` and `yes` are still refused, and the strict comparison every gate makes is unchanged. @ericof [#5](https://github.com/collective/pas-plugins-identity/issues/5)
- Added `create_user`, a per-provider switch for authenticating against a provider while admitting only people who already have an account here. The account is found by matching a verified address, so saving it without the two linking switches is refused rather than leaving a provider nobody can sign in through. @ericof [#6](https://github.com/collective/pas-plugins-identity/issues/6)
- Added `sync_groups`, a per-provider switch for keeping a provider to sign in with while deciding group membership locally. Groups it already granted stay, exactly as they do when the map is emptied. @ericof [#7](https://github.com/collective/pas-plugins-identity/issues/7)
- Moved three hard-coded network limits into the registry: `portrait_timeout`, `portrait_max_bytes` and `discovery_timeout`. How long a login may wait for a provider, and how much of a user-supplied URL the backend will read, are facts about where the provider is rather than about this package. @ericof [#10](https://github.com/collective/pas-plugins-identity/issues/10)
- Audit records now go to every destination a site names, rather than to a single replaceable utility. Sinks are named utilities listed in order by `pas.plugins.identity.audit_sinks`, and one that fails or no longer resolves is logged and stepped over rather than allowed to fail the sign-in it was auditing. A new `IAuditSource` splits reading from writing, so a write-only destination is possible and a site with nothing readable is told so rather than shown an empty log. @ericof [#23](https://github.com/collective/pas-plugins-identity/issues/23)
- A Profile carries a list of addresses, and `email` is derived from it.

  A person has more than one address, signs in with more than one of them, and which one is theirs *here* is a question whose answer changes. So `emails` is what a Profile stores -- an ordered, required tuple -- and `email`, the single value every property sheet, every OIDC claim and every enumeration still reads, is computed: the first verified address, or the first address at all when none is verified. It is read-only, so `plone.restapi` leaves it out of the edit form altogether and there is no second value to disagree with the list. Everything that writes it keeps working: a write moves that address to the front of the list rather than replacing a field, and an empty write is ignored, because a provider that stopped sending an address has not said the person no longer has one.

  **Verification is not a field.** An address counts as verified when this site holds an `email` identity for it owned by that userid, which is exactly what a magic link creates and exactly what `auto_link_by_email` already consults. A second `verified` flag beside it would be a copy of that fact, and the two would drift the first time an identity was unlinked. Linking or unlinking an email identity reindexes the owner's Profile, because `email` is served from catalog metadata everywhere it matters and confirming a link never touches the Profile.

  **Verifying an address now requires it to be yours.** `POST @identities` with the email provider refuses an address that is not on the caller's profile. A magic link proves control of whatever was typed, so the free-text box the identities page used to offer verified *any* mailbox -- and a verified address is what `auto_link_by_email` attaches a new provider account to. Naming the address on your profile first makes it a claim somebody can see and an administrator can audit. A caller with no Profile is not held to it.

  The Profile catalog gains an `emails` KeywordIndex and `emails` / `verified_emails` metadata, so "whose profile carries this address" is one query. `@my-profile` reports `emails` -- each address with whether this site has verified it and which one `email` resolves to. 
- A `pas.plugins.authomatic` migration can now bring verified addresses across.

  The dump carries the provider's `email_verified` claim, which the converter had been discarding, so everyone arrived a stranger to their own address and stayed that way until their next sign-in. The converter carries it in the identity's `claims` now.

  Who believes it is deliberately two questions rather than one.

  A site that already trusts the provider at a login trusts the same claim in a document, and needs to do nothing: `link` fires `IdentityLinked`, and the subscriber answers it exactly as it answers a login.

  A site that does **not** trust the provider at a login may still want the addresses its old site had already collected — a decision about the history being imported, not about every future sign-in. That is `trust_verified_emails`, or `--trust-verified-emails`, asked for per run. It leaves the site's login policy untouched, which is the point: reusing `trust_email_verification` would mean switching that policy on, importing, and remembering to switch it back, with a window in which real logins are judged by the temporary setting and nothing reporting it if the last step were forgotten.

  `record_verified_addresses` takes an explicit `trust` argument for this; `None`, the default, still asks the provider record, which is what a login and every event handler must do. Only a literal `true` in the dump counts either way — a string `"true"` is truthy and is not a provider saying yes, and the flag means *believe what the dump claims*, never *call everything verified*. Measured on a real 17-person Google dump: 17 of 17 arrive verified, with the site's login policy unchanged. @ericof 
- A client's redirect URIs may carry a wildcard, in two positions.

  Registering every host a site answers on, one at a time, is the thing this avoids. `https://*.example.org/callback` stands for exactly one further label — `app.example.org`, and deliberately not `a.b.example.org` nor the bare `example.org`. `https://example.org/*` stands for any path on that host, and any query string with it. The two combine.

  A registration without a `*` is unchanged: compared as a string and nothing else, because matching a redirect URI is what binds an authorization code to the client it was issued for. No prefix matching, no ignoring the query string, no treating a trailing slash as equivalent.

  The refusals are the more important half. A `*` is rejected in a port, a user name, a query string, in the middle of a label such as `https://a*.example.org`, in the middle of a path, and directly under a public suffix such as `https://*.com` — which would hand every site with such a name a valid redirect target. The scheme and the port are never widened, so a wildcard registration cannot be downgraded to plain HTTP.

  This is a deliberate widening, and the documentation says so plainly: every name a wildcard covers is somewhere this server will send a browser carrying an authorization code, so a subdomain that is taken over, forgotten, or serving somebody else's content is a valid target for as long as the registration stands. Érico asked for it knowing that, because listing hosts one by one is its own kind of mistake. @ericof 
- A login now says so in the transaction it commits.

  Zope writes a transaction's description in `ZPublisher.utils.recordMetaData`, which runs after traversal and *before* the view is called. On a federated login the view is where authentication happens, so the one transaction that mints an account, writes several hundred objects and joins a person to a userid was committing as a bare `/plone/@identity-callback` attributed to nobody. The undo log could not say who signed in, or that a login was what it had been looking at.

  `core/txn.py` adds a line per fact, and `Transaction.note` appends rather than replaces, so Zope's path stays where it was:

  ```text
  /plone/@identity-callback
  identity: login 8f2c1e... via github (new user, new identity)
  identity: profile created at /plone/users/8f2c1e...
  ```

  A login against a local password is recorded the same way, naming the login offered. The transaction is also attributed to the userid, which Zope could not do because at traversal time the person was still anonymous — unless it already names somebody, so a request genuinely made by an administrator keeps its own attribution.

  No claims, no address, no provider subject. A transaction record is never purged short of packing the storage, which makes it the worst available home for personal data; the userid is opaque and a provider id is site configuration. Nothing here joins the transaction either, so a request that wrote nothing goes on writing nothing. @ericof 
- A person can now see which applications use their data, and cut one off. `GET @oauth-grants` lists the caller's own standing agreements — the application, when they agreed, and what each scope actually releases — and `DELETE @oauth-grants/<client_id>` withdraws one.

  It is the mirror image of `@identities`, and the gap it closes was a real one: a user could see the providers they sign in *with* and unlink one, and had no way at all to see the applications they had signed in *to*. The consent store has recorded exactly this since the consent screen shipped; nothing could read it back, and nothing could forget an entry.

  Not the admin API. `@identity-clients` is the operator asking "who may log in to this site" and needs `Manage portal`; this is a person asking "who did I let in", and needs only that they are the caller.

  Withdrawing does two things, because either alone would be a lie. Forgetting the agreement decides what happens the next time that client asks — it is prompted, as it was the first time; it is not blocked, which is a different thing and an operator's to do. Revoking that client's refresh tokens for that user is what ends the access it already has, and it is narrower than the revocation a back-channel logout performs: the user said no to *this* application, and ending their sessions with every other one would answer a question they did not ask.

  What it cannot reach is reported rather than hidden. Access tokens are self-encoded with no denylist, so one already minted lives out its lifetime whatever anybody withdraws; both endpoints return `access_token_ttl` so a screen can say how long that is instead of implying a cutoff this server cannot deliver. An agreement with a client the operator has since unregistered is still listed and still withdrawable — the record outlived the registration, and hiding it would leave something the user can neither see nor undo. @ericof 
- Added OpenID Connect back-channel logout. A provider can tell this site directly — server to server, with no browser involved — that somebody's session there has ended, which is exactly why it still works after the user has closed the tab. Register `@@backchannel-logout` as the client's back-channel logout URI; one endpoint serves every configured provider, since the logout token names its issuer and that is how the verifying key is chosen.

  The `sub` in a logout token is the *provider's* subject rather than a Plone userid, so the identity store is what turns one into the other. A logout for an identity this site has never seen answers `200`: there is nothing to end, and answering differently would tell an unauthenticated caller which of a provider's subjects have accounts here. Validation follows the specification — signature, issuer, audience, `iat` and `jti`; the token must declare the back-channel logout event, must carry a `sub` or a `sid`, and must **not** carry a `nonce`, since a nonce means somebody is trying to pass an `id_token` off as a logout instruction. A `jti` already acted on is refused as a replay, recorded before any work is done so a token cannot be acted on twice even if the first attempt failed halfway.

  Ending the session needs `plone.session`'s **`per_user_keyring`**, which is off by default: without it every ticket in the site is signed from one ring, so ending one person's would end everybody's. This package refuses to do that, logs an error naming the switch, and reports `sessions_ended: False` rather than silently doing nothing.

  A logout also revokes the refresh tokens the `[server]` layer issued for that user across every client, because the logout was about the person rather than one application. That crosses a boundary core is forbidden to cross, so it goes through a `SessionsRevoked` event core fires and the server layer subscribes to. Access tokens are **not** revoked: they are self-encoded with no denylist and live out their lifetime, at most the configured TTL. That is the cost of the self-encoded design, and it is documented rather than hidden. @ericof 
- Added Python 3.14 support. The supported range is now 3.12 to 3.14; the full stack installs on 3.14 against the Plone 6.2 constraints and the whole test suite passes there. @ericof 
- Added `pas.plugins.identity.exportimport`: a site's users, groups and identity join as a single JSON file, and the same file back into a site.

  `pas.plugins.identity.migration` moves a site in place, with both plugins installed in one instance. It cannot help when the old site is a database you were handed, when the new site is somewhere else, or when what you want is a copy of your accounts that outlives the instance. This is for those.

  Two console scripts, taking the same `zope.conf` and site arguments as `plone-exporter` and `plone-importer`:

  ```shell
  identity-exporter etc/zope.conf plone var/principals.json
  identity-importer etc/zope.conf plone var/principals.json --dry-run
  identity-importer etc/zope.conf plone var/authomatic.json --from-authomatic
  ```

  Both are a thin wrapper over `export_site()` and `import_site()`, which take and return plain data, so anything the commands do can be scripted.

  Migrating from `pas.plugins.authomatic` offline is the ordinary import: a dump extracted from the old site is converted into a document and read by the same importer, so there is one importer to get right rather than two. The dump format and a working extraction are documented; the script is not shipped, because it has to run where that package is installed.

  The userid travels verbatim in every direction. Every local role, ownership and sharing entry in a site is written against it, so an import that minted new ids would produce a site full of content belonging to nobody, silently.

  No passwords, no client secrets and no audit entries are in the format at all, in either direction — a document is a file that gets copied around, and the one thing it must never be is a way in. A refusal stops the whole run and writes nothing; a single bad record is skipped and reported, so one identity already linked to somebody else does not stop the other nine hundred. A dry run never attempts the write. @ericof 
- Added a `pas.plugins.identity.Groups` vocabulary, and a Profile's `Groups` field now chooses from it instead of taking free text.

  The field stores group ids, and nothing checked that one named a group. The groups plugin filters an unknown id out rather than failing, so a typo produced a membership that granted nothing and said nothing — the worst shape a mistake about who is in which group can take. Every group PAS knows is offered, not only the ones that are content, because membership names an id without caring which plugin answers for it; `AuthenticatedUsers` is left out, since nobody is explicitly a member of it.

  A Profile that already names a group which has since been deleted stays readable: the vocabulary constrains what may be written, and the doctor goes on reporting the stale id as `unknown-group`. @ericof 
- Added a container of their own for groups. `group_container_id` and its three companions mirror the profile container's records, and they default to the profile container — so a site that has not asked for anything keeps filing principals together, with no migration and nothing to set.

  Core is now told about the two separately: users resolve through the profile container's path and groups through the group container's. Until this, both records were pointed at one derived path, and a site that put its groups anywhere else got a half-working result rather than a refusal — enumeration reads the catalog, which is not scoped to a container, so the groups listed correctly and every write to one failed. @ericof 
- Added an optional behavior keeping a user's password on their own content object, off by default.

  Without it a new user's password goes to `source_users`, which is where Plone has always kept one. Turning it on gives a site whose users are content a single object per person holding everything about them, and makes Profile workflow into account suspension: a `deactivated` Profile stops authenticating, which `source_users` cannot do at all.

  The hash is an annotation, not a Dexterity field. A field is serialized by `plone.restapi`, exported by GenericSetup, indexable, and snapshotted by versioning — four separate paths that each fail by disclosing the credential, and each of which would have to be remembered independently. An annotation is invisible to all four without anything being excluded anywhere. Hashing is `AccessControl.AuthEncoding`, so the stored form is one the rest of the stack already understands. Copying a Profile clears it, because copy and paste is a normal thing to do to content and must not hand the copy somebody else's credential.

  Core does the authenticating, through a new `ICredentialStorage` contract the behavior provides. The `[content]` layer serves properties, enumeration and groups and never becomes a way to log in — the plugin that authenticates a userid is the one `@users` reports as its source, and an optional property store must not change a site's answer to where an account came from.

  Nothing is migrated. A user whose credential is already in `source_users` keeps it, and turning this on changes where the *next* password is written rather than moving existing ones behind an operator's back. @ericof 
- Added email addresses as something you can link to an existing account. `POST @identities` with the email provider mails a confirmation link instead of answering an authorize URL, and `POST @magic-link-confirm` attaches the address to the account that asked for it rather than signing its holder in.

  The two purposes are kept apart in the token itself. A magic link is minted for one or the other, and each endpoint names the purposes it accepts rather than taking anything correctly signed: a confirmation link that could be redeemed as a login would hand the account to whoever holds the mailbox, which is the takeover the flow exists to prevent. The account is recorded in the token rather than in the flow cookie, because a link is very often opened somewhere else — a phone, a webmail tab in another profile — where no cookie of ours exists; the same-session guarantee is kept by requiring the redeeming session to be that user, checked when the link is clicked. A link the wrong person clicks is refused and spent, not left retryable.

  Sending is rate-limited on the same counters as magic-link login, per address and per IP. An authenticated caller is not exempt: an account is cheap, and the mailbox being flooded belongs to somebody else. @ericof 
- Added identity linking. `GET @identities` lists the identities you own, `POST @identities` starts a flow attaching another provider to your account, and `DELETE @identities/<provider>/<subject>` unlinks one — unless it is your last way in, which is refused rather than allowed to lock somebody out of their own account.

  `@users` now reports `identities`, `source` and `profile_url` for a user. An administrator looking at an account could see its roles and its groups but not the one thing this package exists for: which external identities resolve to it, and which PAS plugin the userid actually came from. @ericof 
- Added migrations from `pas.plugins.authomatic` and `pas.plugins.oidc`. Both are hard cutovers, dry-run by default, and idempotent.

  The authomatic migration is the straightforward one: that package already stores exactly the `(provider, subject) → userid` mapping this one does, so the migration reads it rather than reconstructing it, and userids come across verbatim — so every local role, sharing setting and piece of content ownership keeps pointing at the right person, whichever of its four user-id factories the site used.

  The OIDC migration is harder and may refuse. `pas.plugins.oidc` stores no identity mapping at all, so the join only reconstructs when its `user_property_as_userid` is the default `sub`; a site that changed it never stored the subject anywhere, and the migration refuses rather than producing a plausible-looking wrong join that would surface months later as somebody logging into somebody else's account. Nothing marks an account as OIDC-created either, so the accounts to claim are named explicitly or defaulted to every local account, with the dry-run report listing exactly which. @ericof 
- Added optional copying of a provider's avatar into Plone's portrait storage, **off by default**. When switched on, a changed `picture_url` claim is fetched during claims sync and stored as the user's picture.

  Where that is depends on the site, and it is the same answer a preferences upload gets: the Profile on a site running the `[content]` layer, `portal_memberdata` everywhere else. One store per user, whichever writer — an avatar in the other one would leave the Profile content object showing an empty picture field on a site that was displaying a picture. A picture somebody chose is never replaced: the Profile remembers which URL the provider supplied and a provider may replace only its own, so uploading your own ends its claim and clearing yours hands it back.

  Off by default because `picture_url` is a claim, and at plenty of providers a claim is whatever the user typed: turning it into a server-side fetch makes the login path a request forger, and a user who sets their avatar URL to an address only the backend can reach gets the backend to fetch it and reads the bytes back through their own portrait. When it is on, the guards are HTTPS only, a short timeout, a size cap read from the stream rather than trusted from a header, and a content type the server actually claims is an image. None of that makes fetching a user-supplied URL safe, which is why the switch exists rather than a longer list of guards.

  A provider can be configured to allow plain HTTP as well, off unless somebody sets it. It is per provider rather than a second site-wide record because "this issuer is a container on my own machine with no certificate" is a statement about that issuer; it exists because a development or demo stack could not exercise this path at all otherwise, and a feature nobody can run is a feature nobody has tested. It relaxes exactly one scheme — `file://` is refused either way.

  The fetch runs *after* the successful-authentication event rather than before it, and so does the provider's property map. Both are fallbacks — each asks whether something else owns this user's data and writes into core's own store only when the answer is no — and on a first login neither question has an honest answer until the event has been delivered, because the thing that would claim the user is created by a subscriber to it. Asked too early, both were told "nobody owns this user" and wrote to `portal_memberdata`, leaving the claimed store empty on exactly the login that created it; and neither self-corrects, since the property map skips a field that already holds a value and the avatar is refetched only when the provider changes its URL. A fallback runs after everyone entitled to claim has been told.

  Every failure is logged and swallowed. An avatar that would not load is a missing picture, and refusing the login over it would be a far worse bug. @ericof 
- Added the `[content]` extra: users backed by content objects, installed by its own `pas.plugins.identity.content:default` GenericSetup profile.

  An `UserProfile` Dexterity type, a three-state workflow (`incomplete` / `complete` / `deactivated`), and a dedicated `portal_identity_catalog` carrying the whole PAS property sheet as metadata. Where Profiles live is configuration rather than a constant — the container's parent, id, title and type are four registry records — and the catalog indexes a Profile wherever it actually is, so reorganising content is not a deauthentication. Drift is reported by a read-only consistency check and repaired by a re-runnable import step, kept apart so the check can be scheduled without a side effect. Uninstalling removes the catalog, the type and the workflow and leaves every Profile untouched: uninstalling an add-on is a configuration change, not an instruction to delete accounts.

  Its PAS plugin serves member properties and user enumeration entirely from catalog brains, so a site can back its users with content objects and still answer "what is this user's full name" and "who matches 'liddell'" without loading a single Profile from the ZODB. That is measured rather than asserted: the tests patch `ZODB.Connection.setstate` and require the load count to be zero while enumeration and property reads run, having first proved the objects were ghosts and the counter works. The plugin sits above `mutable_properties`, so a field the user edited is what the site shows rather than the claim their provider sent — including a field they deliberately cleared. Login names match regardless of case at both ends. A `deactivated` Profile stops being enumerated without being deleted, and which states count is a registry setting. Property *writes* go back to the Profile through the same plugin, so changing a name through user preferences, through `@users`, or on the login path is stored rather than silently discarded.

  First login mints a Profile in the `incomplete` state, seeded from the provider's claims through the provider's own attribute mapping — the one the control panel edits — and files it in the configured container. Later logins refresh only the fields the provider still owns: rather than a flag per field the Profile remembers what the provider last wrote, and the provider may write a field only while the current value still equals that. Editing a field ends the provider's claim on it, and so does clearing one — the case a flag-based design usually gets wrong, where a value reappearing at the next login is indistinguishable from a bug. The login name is never synced: it is half of the case-folded index enumeration queries, and a provider renaming somebody should not silently move their account.

  A user gets `Owner` on their own Profile and nothing on anybody else's, computed by a local-role provider rather than assigned at creation so there is nothing to keep in step. `Owner` is what Plone means by "this object is yours", and it carries more than editing: stock Plone hands it sixteen permissions with acquisition on, so `user_profile_workflow` states the ones that matter and stops them at the site administrator. Deleting is the one to keep in mind — a user deleting their own Profile would break their account while their login kept working — and adding content inside somebody's profile, rewriting its view template, editing its ZODB properties and opening it in the management screens are the same shape. Every field declares a read and a write permission, and those permissions are granted to somebody. `GET @my-profile` answers the frontend's first-login routing question from the catalog, so the check every login performs costs no object load.

  The type also carries the picture, in a field named `image`, and it wins over the member portrait: a picture somebody chose beats one a provider supplied. The name is load-bearing rather than a matter of taste — `plone.volto`'s indexer looks for exactly `preview_image_link`, `preview_image` and `image`, and what it finds becomes the `image_field` catalog metadata every Volto listing and summary view reads, so a field called anything else is invisible to all of them however correctly it is stored. Both the read and the write path honour the precedence — a portrait uploaded through user preferences lands on the Profile for a user whose account is one, and on `portal_memberdata` for a user whose account is not, and `@portrait/<id>` serves whichever store answered. One store per user, and it does not change under them.

  Both types are addable in one place only: the container the registry names for them. Each has its own add permission, `rolemap.xml` grants both to no role at all, and the grant that makes either type addable is written on the container itself — when this package creates it, when it installs into a site that already has it, and when a folder appears at the configured path, which is the case a policy profile or a content import reaches. So a `UserProfile` cannot be created or pasted into an ordinary folder by anybody, including a `Manager`, and neither type shows up in the add menu anywhere else. Filing principals somewhere else as well is a grant an operator makes on a folder they chose. The permissions are separate per type so that a site keeping groups apart from users can open each container to one kind only.

  Content-backed groups come with it: an `UserGroup` type, three PAS plugins (`IGroupsPlugin`, `IGroupEnumerationPlugin`, `IGroupIntrospection`) and a `group_ids` field on each Profile, so group membership is content a site can edit and review like any other.

  A Profile's `userid` is genuinely permanent — an identity record, every local role granted on it and the catalog entry the enumeration plugin queries all point at it, and the REST API refuses a change rather than detaching all three — and `email` is required, because the audit log, `@users` and magic-link join all read it. @ericof 
- Added the `[server]` extra: this site as an OAuth 2.1 authorization server, installed by its own `pas.plugins.identity.server:default` GenericSetup profile, which also registers the browser layer everything in the layer binds to — a site that never applied it does not publish the endpoints at all.

  Clients are registry-backed records, exportable through GenericSetup like providers are, but their secrets are stored hashed with scrypt rather than masked: this package is the server here, so nothing ever needs the plaintext again. A secret is returned once when minted or rotated and cannot be read back. Redirect URIs match exactly, public clients are flagged as requiring PKCE, and an unknown client id costs the same work as a wrong secret so the two cannot be told apart.

  Signing keys are asymmetric and generated when the profile is applied, never shipped — a key inside the package would be the same key in every site running it. Only the public halves are published, as a JWKS. The ring keeps previous keys so a rotation does not invalidate tokens still inside their lifetime, and it is bounded so the record cannot grow forever. Access tokens are self-encoded JWTs, so issuing one writes nothing to the database; the issuer is configured rather than derived from the portal URL, because relying parties compare it byte for byte.

  `@@oauth-authorize` issues a code to a registered client and `@@oauth-token` exchanges it, both as browser views rather than REST services because a relying party sends a browser and posts a form, not JSON. PKCE is mandatory for public clients and only S256 is accepted — `plain` puts the verifier in the authorization request, which is the exact thing PKCE protects. Codes are single-use, short-lived, bound to the client and redirect URI they were issued for, and burned even when the redemption fails, so one intercepted code does not become unlimited guesses at the verifier. The token endpoint accepts HTTP Basic as well as the form, which RFC 6749 §2.3.1 requires and most clients use.

  Refresh tokens are rotated on every use and revoked on replay, issued when a client is **registered** for the grant rather than when it asks. The client-credentials grant and a Bearer plugin complete the picture — an issued token authenticates a request against Plone, with the audience checked against the client registry on every one, which is what makes deleting or disabling a client this server's revocation.

  An unauthenticated end user at the authorization endpoint is sent to log in rather than refused: answering the client `login_required` broke the flow outright for the ordinary case of somebody not signed in yet. A visitor already signed in to Volto is not asked again — the endpoint reads the `jwt_auth` token Volto keeps in a cookie, so a Volto-first identity provider is a coherent thing to build. @ericof 
- Added the ability to keep a site's users and groups as content, without core knowing what content.

  `IUserContent` and `IGroupContent` are markers a Dexterity type provides, declared in core and implemented by whichever layer owns users — the direction every extension point in this package runs in. A user type promises `userid`, `login` and `group_ids`; a group type promises `group_id`; and for both the object's id within its container *is* that identifier, which is what lets core find one in a single traversal rather than a search. Four registry records say which portal type and which container, so `UserProfile` and `/identity-profiles` are values rather than code.

  The identity PAS plugin then implements `IUserAdderPlugin` and PlonePAS's `IGroupManagement`. There is no `IGroupAdderPlugin` — groups go through a different interface in a different package — but both loop over their plugins and stop at the first that returns true, so both halves work by *declining*. With no type configured, which is every site until somebody sets the records, the plugin returns false and `source_users` or `source_groups` does the job exactly as before.

  That makes being asked first load-bearing rather than cosmetic: registered below the stock plugins this one is never reached, because they never decline. The plugin is moved to the top of both interfaces on install, for the same reason the `[content]` layer sits at the top of `IPropertiesPlugin`.

  Membership is written to the **user**, not to the group, because that is the direction Plone asks the question in: `getGroupsForPrincipal` runs on every permission check that touches a local role, while listing a group's members does not. Nesting a group inside a group is refused rather than stored — a recursive membership answer computed from catalog metadata stops being a single lookup, which is the property this design rests on.

  On a site running the `[content]` extra none of that has to be configured: `UserProfile` and `UserGroup` declare the two markers, and the layer points the four records at itself. It does so with a subscriber rather than a value in `registry.xml`, because where Profiles live is itself configurable and a profile layered on top of this one sets the container's parent and id *after* this package's install handler has run — a path written once at install names the container the layered profile is about to move. Derived and re-derived, an operator who moves the container in the control panel gets core following them with no reinstall.

  The password is not stored on the content object. A Dexterity field holding a credential is serialized by `plone.restapi`, exported by GenericSetup, indexable and snapshotted by versioning: four separate paths that each fail by disclosing it. So the content object is the record a user *is* and `source_users` stays the credential store, which is what already happened for externally authenticated users. Adding a user through the ordinary API therefore produces somebody who can actually sign in.

  Core creates; it does not enumerate. Answering "which users match this?" without waking every object needs a catalog, and that is what the `[content]` extra is for. The two are not independent: PAS looks a principal straight back up after adding it, so a site that configures the records without a layer that enumerates gets a user that cannot be found. The record descriptions say so. @ericof 
- Added the audit log: a bounded per-user record of authentication events, stored inside the PAS plugin and purged on write against registry-configured limits for entry count and age. Successes are recorded from the event contract, so anything that fires an event is audited whoever fired it; refused callbacks are recorded by the callback service in an unattributed bucket, because being refused is precisely what leaves them with no userid.

  The IP address and user agent are personal data and are stored only when `pas.plugins.identity.audit_record_pii` is switched on, which it is not by default. Credentials, tokens and authorization codes are never recorded at all. The sink is a utility, so a deployment can send entries somewhere else.

  `GET @audit-log` reads it. The default scope is the caller's own authentication events; reading another user's, or the site-wide log including the refusals that could not be attributed to anybody, needs `Manage portal`. @ericof 
- Added the authorization server's admin API. `@identity-providers` manages who this site lets people log in *with*; `@identity-clients` and `@identity-keys` are the other direction — who may log in *to* it, and what this server signs with. The **OAuth clients** entry is registered in `portal_controlpanel`, so Plone's own listing links to it.

  The secret handling is what differs from the provider API, and the difference is deliberate. A provider's secret is masked: this package is the client there, has to keep sending it, and a round trip that echoes the mask back leaves the stored value alone. Here this package is the server and stores a hash, so there is nothing to mask and nothing to echo — a secret exists exactly once, in the response that mints it, and an operator who loses it rotates.

  A `PATCH` refuses what it will not change rather than dropping it silently: renaming a client would orphan every token already minted for it, and turning a confidential client public would leave a stored secret hash that nothing checks. Both are a delete and a re-register. Deleting or disabling a client is this server's only revocation, since access tokens are self-encoded; rotating a key leaves the previous ones in the ring so tokens already issued keep verifying, up to the ring's bound. @ericof 
- Added the claims contract and OpenID Connect discovery: the point at which an off-the-shelf OIDC client can be pointed at this site's issuer URL and need nothing else. `<issuer>/.well-known/openid-configuration`, the JWKS endpoint, `id_token` minting and the userinfo endpoint, with every advertised endpoint built from the configured issuer rather than the portal URL — which is whatever the request came in on, while this is a URL handed to another site.

  Claims are read from **Plone user properties**, never from a `UserProfile`. That keeps the `[server]` layer independent of the `[content]` layer as the import-linter contract requires, and is also simply correct, because the content layer serves its fields *as* a property sheet. A federation therefore looks like two mappings and is one: configure the first hop and the second follows, on a site with the content layer or without it.

  `profile` releases `name`, `preferred_username`, `website`, `picture` and `description`; `email` releases `email` and `email_verified`; `address` maps Plone's single-line `location` to the `formatted` member; `sub` is never scope-gated. `preferred_username` is the login name rather than the userid, since a userid may be 32 hex characters and mean nothing to a person. `picture` is a URL the other end can fetch, published only when a picture is actually stored — Plone's `getPersonalPortrait` falls back to a default image, and publishing a claim every user shares would tell a relying party that everybody uploaded the same photograph. Which store holds it is not this layer's business: it asks whether the user has one at all and always publishes `@portrait`, so the claim does not depend on whether the site installed the `[content]` extra. Asking `portal_memberdata` directly would be correct only while every picture landed there, and would silently drop the claim for every user whose picture is on their Profile — a federation that loses everybody's photograph, indistinguishable downstream from a site where nobody uploaded one. `description` is the one claim with no registered name: OIDC has none for a free-text biography, and it is released under `profile` anyway rather than under a private scope, since a relying party that does not know the name ignores it and a scope only this server's own peers would ask for buys nothing but a second thing to configure.

  A claim with no value is omitted rather than sent blank, so a relying party can tell "we do not know" from "it is blank". `email_verified` is the one to read twice: it is true only when *this site* verified the address with a magic link, never because an upstream provider asserted it. The core layer already refuses a provider's word when consuming identities, and a server that passed that word along as its own would export the problem to every relying party downstream. @ericof 
- Added the consent screen. `@@oauth-authorize` asks the user before issuing a code and remembers the answer per user and client: the prompt appears the first time and again whenever a client comes back for a scope not already agreed to, so an existing session at the authorization server keeps meaning something. Consent is recorded as the whole scope list the user was shown rather than merged into what they agreed to before — merging is how a consent screen ends up recording more than anybody said yes to.

  It sits at the *end* of validation, never the start. A user is never shown a form approving a request that was going to be refused anyway, and a form rendered before the redirect URI is verified would be a phishing page this server hosts on the client's behalf. The request travels back through the screen rather than into a session, so there is no server-side state to expire between the question and the answer, and the answer re-runs every check the first request did — a client disabled while the user was reading is refused on the way out. An answer without a valid `plone.protect` token raises `Forbidden` rather than counting as a denial: forging one is an attempt to authorize an application in somebody else's name, and it should look like the attack it is. A denial reports `access_denied` to the client with the `state` echoed.

  Where the question is asked is configurable. `Consent screen URL` names a frontend route to send the browser to, so the question is rendered in the site's own look; leave it empty and the server renders a standalone page of its own, which is what a site without a frontend gets and what an authorization server needs before anybody has built one. `GET @oauth-consent` is what such a screen reads — the client, the signed-in user, the scopes and the claims each releases. It decides nothing, and it refuses to describe what the server would not honour: an unknown client, a disabled one, or a redirect URI matching nothing registered is an error rather than a page reading "Allow *evil-app* to use your account?" served from the site's own domain.

  There is no way to withdraw consent yet. That belongs with an account screen listing what somebody has agreed to, and neither exists in v1. @ericof 
- Added the control-panel API and the registry layout behind it. `GET @identity-drivers` describes every registered driver and its configuration schema, which is what the frontend renders a form from; `@identity-providers` supports full CRUD plus a per-provider connection check. The **Identity providers** entry is registered in `portal_controlpanel`, so Plone's own listing links to it.

  Every provider setting is its own registry record — `pas.plugins.identity.providers.<id>.<field>` — rather than one text record holding a JSON list. A GenericSetup export therefore describes a site's providers field by field, a single setting can be changed without rewriting the rest, and `get_provider_record` reads one the way `plone.api.portal.get_registry_record` reads any other.

  Each driver's schema is what makes a provider configurable without frontend work: every field declares its type, whether it is secret, its default and an explicit `order`, because a schema travels as a JSON object and plone.restapi serialises those sorted — so the order a driver declares is gone by the time a form is built from it unless each field carries its position. A driver's defaults are applied when a provider is created, which is what keeps a GitHub provider from being configured with OIDC scopes it does not grant, and a driver may seed the new provider's attribute mapping so a provider created without touching it still syncs something.

  A provider's scope is a list of permissions rather than the space-delimited string OAuth 2 puts on the wire: with the encoding and the value in one field, a trailing space or a stray comma becomes a scope of its own that the provider rejects as unknown. The attribute mapping is a per-provider record of provider claim to Plone user field, so a claim this package has never heard of can be mapped without code; the `pas.plugins.identity.UserFields` vocabulary lists what can be mapped onto, built from `getFromBaseSchema(IUserDataSchema)` so it includes fields a site added. Stored secrets are masked on the way out and restored on the way back unless edited — symmetrically, including for a provider whose driver has been uninstalled, so a round trip that changes a title cannot silently blank a secret.

  The login callback URL is a site-wide setting rather than a per-provider one, since it is one frontend route registered identically with every provider; it accepts a path, resolved against the portal URL, and defaults to `/login-identity`. Reinstalling a layer creates the records its settings interface has gained since the site was set up, so a site that upgrades and reapplies a profile is not left with a control panel that cannot be read. @ericof 
- Added the core identity layer. An identity store maps `(provider, subject)` pairs to a permanent canonical userid; a driver framework carries GitHub, Google, generic OIDC, email and `plone-identity` drivers; a PAS plugin provides extraction, authentication, credentials reset and opt-in challenge; and authlib-backed authorization-code flows carry state, PKCE and nonce. Five documented events are the package's public API, and everything built on top of it — the audit log, the `[content]` extra's first-login handling — is driven by those events rather than by reaching inside the flow.

  The pending authorization attempts live in a signed cookie keyed from `plone.keyring`, the way `plone.session` keys its auth tickets: Plone 6.2 ships no `session_data_manager`, and an unsigned cookie would let a browser choose which flow it is completing.

  A userid is minted once and stored. It is a random uuid4 by default — it leaks nothing and never has to change — but a provider can be configured to mint a readable one instead, from the provider's username, the email address or the provider's subject, so a GitHub account arrives as `ericof` rather than 32 hex characters. All three are claims, so all three are handled: the value is normalized into something usable as an id, an empty one falls back to a uuid rather than minting something unusable, and one already taken gets a numeric suffix. Availability is checked against **every** PAS source, not just this package's records: otherwise a provider account called `admin` would be handed the site's `admin` userid and inherit its roles. The GitHub and `plone-identity` drivers default to the provider's username, since both publish one that is already the name the person is known by.

  Auto-linking by verified email is opt-in per provider, and matches only addresses this site verified itself with a magic link. A provider asserting `email_verified` is not enough — trusting it would make an account takeover as cheap as an unverified address at any provider a site happens to have configured.

  Provider metadata is resolved once and cached per issuer: published endpoint constants for providers that do not move, OIDC discovery for the rest, so a login costs one round trip rather than three. Which of the two a provider gets is asked of its driver — does it declare an `issuer` field for the operator to fill in — rather than looked up in a list of driver ids, so a driver this package has never heard of is discovered correctly and a subclass is not refused for being one. The token-endpoint authentication method comes from that discovery document rather than authlib's default, and the `id_token` audience is validated against the client id configured for the provider rather than the one the provider advertises. @ericof 
- Added the login-flow REST services. `GET @login-providers` lists the providers a user may log in with, `GET @login-providers/<id>` starts an authorization-code flow and returns the URL to send the browser to, and `POST @identity-callback` completes one and answers with a `jwt_auth` token — the same token `@login` issues, so everything downstream of signing in is unchanged.

  The callback identifies the flow from the `state` a provider redirects back with, which is what a provider actually sends; requiring the caller to name the provider as well made every browser login fail at the last step.

  `@login-providers` is also a plone.restapi expandable component, because the sign-in buttons are wanted alongside something else more often than on their own: the identities page lists what a user has linked *and* what they could link, which is one screen and now one request.

  Magic-link login is its own driver. `POST @magic-link` mails a signed, single-use, short-lived link and `POST @magic-link-confirm` redeems it for a `jwt_auth` token. Tokens are authlib-signed from the same keyring the flow session uses, rate-limited per address, and the endpoint says the same thing whether or not the address is known — an endpoint that answers differently is an account-enumeration oracle with a friendly message. @ericof 
- Added the required-information gate. While a profile is `incomplete`, every page its owner asks for is answered with a redirect to the profile's edit form, so a provider that withheld an email address cannot leave a site with an account it knows nothing about.

  Switched on by `pas.plugins.identity.enforce_required_profile_fields`, which ships on. Turning it off makes an incomplete profile a suggestion rather than a gate.

  A gate like this can lock a site out — a required field nobody can supply would leave every user in a loop, with the settings that would undo it on the far side. Two things stop that, and both are in the code rather than in the documentation. Managers and site administrators are never held, because somebody has to be able to reach the control panel. The profile itself is never held, because redirecting the target of the redirect is a loop no configuration escapes.

  The OAuth authorization endpoints are exempt too, by prefix. `@@oauth-authorize` is a browser view answering `text/html` for a `GET`, which is every signal the gate uses to recognise a navigation — gating it strands a visitor who was sent to authorize an application while the relying party that sent them receives neither a code nor an error. A site can name further views in `pas.plugins.identity.gate_exempt_paths`, for a browser-based flow another add-on publishes.

  Three other things pass through, for reasons about the request rather than the user: anything `plone.restapi` answers, because Volto fetches the edit form over the API and gating those would break the page the user is being sent to; anything that is not a browser asking for a page, because a gate on every request is a gate on every stylesheet; and signing out, because a user who would rather leave than fill the form in may. @ericof 
- Driver settings schemas now declare fieldsets, so the provider control panel can group them: what a site needs in order to reach the provider stays on the first tab, the settings deciding who a returning stranger becomes move to Accounts, and group mapping and the profile picture get tabs of their own. @ericof 
- Every address a provider reports goes onto the Profile, and a provider the operator trusts can verify one.

  GitHub returns every address on an account. This used to be treated as a question nobody could answer for the user: none of them was chosen, `email` was left empty, the Profile was minted `incomplete`, and the required-information gate held its owner on the edit form until they picked. That design belonged to a Profile with a single address slot, where filling it was a guess about which identity the person was here as. `emails` is a list, so there is nothing to withhold — all of them go on, in the order the provider offers them, and `email` derives from the list as it already did.

  Choosing is arranging. Which address stands for somebody is the order of their list, so a preferred address is moved to the front rather than set in a field of its own — on the edit form, or with **Make preferred** on the sign-in methods page. Nobody is held anywhere to do it.

  A later login **appends**, once. An address a provider has already put on is never put on again, so an address somebody deletes stays deleted; the order they arranged is never rearranged; and a provider that changes their address adds the new one beside the old rather than replacing it. Claims carry `emails`, one entry per address with `address`, `verified` and `primary`, and every driver fills it — with the single entry most providers send, so nothing downstream branches on how many there are. `email_choices`, `@my-profile`'s `email_choices` key, and the `@types` decoration that rendered the addresses as a choice are all gone with the question they answered.

  **A provider's email verification can now count, where an operator says it does.** `trust_email_verification` is a new per-provider setting: switched on, an address the provider says it verified is recorded here exactly as a magic link records one — an `email` identity in the store, one notion of verified and no second flag to drift. `google` and `github` ship with it on, because neither will call an address verified until the account has answered mail at it; every other driver ships with it off. Telling somebody who just signed in with Google to go and prove the address Google proved was a worse flow for no security.

  `auto_link_by_email` now requires it too, which closes a hole rather than opening one: the address auto-linking matches on is the one the incoming provider just sent, so a provider whose word this site does not take could previously reach an account by asserting an address some other, trusted route had verified. Both switches are off by default and both are the operator's.

  `email` is no longer a field the claims sync writes, since the addresses have their own path; a property map naming it is ignored for the Profile and still honoured against the Plone user. @ericof 
- Gave groups a way across the federation.

  A Plone site acting as an authorization server now releases a `groups` claim under the `profile` scope, carrying the groups PAS resolved for the principal, sorted, and never `AuthenticatedUsers`. `groups` is not a registered OIDC claim, but it is the name Keycloak, Okta and Entra all use, so a relying party that is not a Plone site can read it. Riding on `profile` is a deliberate trade, and the claims reference states it: a display scope now carries authorization data.

  A relying party maps that claim to local groups per provider, not per driver — two realms behind the same driver are two different directories. Nothing is granted until an operator fills the map in, an unmapped name grants nothing and never creates a group, and a group missing from the site is skipped and logged.

  Every login reconciles, so a membership revoked at the provider stops granting here without anyone editing the site. The reconciliation is fenced: each identity records what its own provider granted, so a login only ever takes back what that provider gave. A group granted by hand survives, and two providers cannot revoke each other's grants. @ericof 
- Gave the federation demo a group that crosses. The provider puts Dana in `site-editors`; the relying party maps that onto its own `Reviewers`, and the two names differ on purpose, because two sites in a federation do not agree on what their groups are called. The provider's other two groups are deliberately unmapped, so the demo also shows that an unmapped group grants nothing. @ericof 
- Gave the identity provider demo its groups as exported content, filed under `/groups`, and stopped creating one in code.

  The demo showed content-backed users and no groups at all, so the group half of the content layer had nothing on screen. A group created by the setup handler *and* present in the content payload is created twice on a fresh site, which is the shape the export round trip makes easy to reach; the payload is the single source now, and `group_container_id` tells the site where those groups live. @ericof 
- Groups can contain groups, and membership is a behavior rather than a field on one type.

  `group_ids` has moved off the Profile schema into `pas.plugins.identity.group_membership`, a schema-only behavior in a **Groups** fieldset. The storage is unchanged -- the field still lives on the content object, the catalog still indexes it, and `profile.group_ids` still answers -- but it is now something a type opts into. A site running its own user type gets membership without redeclaring the field, its vocabulary and its two permissions and then keeping all three in step by hand.

  The Group type enables the same behavior, and there `group_ids` means the groups that *group* belongs to. Everybody in an inner group is therefore in every group it names, the way a GitHub child team inherits its parent team's access. Membership stays a fact stored on the member whether the member is a person or a group, so nesting is a walk over one field rather than a second kind of edge.

  This was refused once, on the grounds that a group whose members are groups makes `getGroupsForPrincipal` recursive and that a recursive answer computed from catalog metadata stops being a single lookup. The first half is true and the second turned out not to matter: the recursion is over the group graph, which grows with the number of teams rather than with the number of people, and one catalog query returns all of it. A cycle is an ordinary input rather than an error -- two edit forms that each looked reasonable can produce one -- and the walk terminates on it instead of refusing the second edit for a reason about the first. A deactivated group neither grants nor conducts: cutting it removes the access of everybody who reached something through it.

  `GET @group-members/<id>` is the contextual version of a listing plone.restapi already half-answers. `@groups/<id>` carries member userids and, going through PlonePAS, already sees the nesting; what it cannot do is name each person, search within the group, or say what feeds into it. This does all three from the Profile catalog in one query, and reports `nested_groups` and `parent_groups` so a group page needs no request per level. A manager may read any group; anybody else may read a group they are in. 
- Made `fullname` a required field on `UserProfile`. It is how a user is named everywhere the site shows them, and a provider is not obliged to send one — GitHub falls back to the login, and plenty of providers send nothing at all. Because the required-information flow reads what the type requires, a profile without a full name is now `incomplete` and its owner is asked for one. @ericof 
- Made the profile workflow describe the profile rather than its age. `incomplete` now means "missing information the site requires" and `complete` means it is not, and the add-on moves a profile between the two itself — when it is created, when it is written to, and when its owner signs in.

  Nothing used to fire `complete`. Every profile stayed `incomplete` for ever, so the frontend's first-login routing diverted every user on every login, and a user who filled their profile in was sent straight back to the form they had just completed.

  Which fields count is `pas.plugins.identity.required_profile_fields`. Empty, which is how it ships, means the fields the profile type itself marks required — `login` and `email` here, and the right answer for a site running its own user type or a behavior that adds a field. Set, it names them. A field counts as filled when it holds something other than `None`, an empty string, whitespace or an empty collection; `0` and `False` are answers somebody gave.

  `@types` for the user type reports the site's required fields alongside the type's, so the edit form asks for everything the flow insists on. `plone.restapi` builds that list from the schema and nothing else, and without the correction a field required by the record but optional on the type would hold a profile incomplete while the form accepted a save without it — a loop produced by one registry record. The record only ever adds: a field the type requires stays required, because the type is the one that cannot store an empty value.

  This matters because a provider is not obliged to send anything: GitHub withholds an email address the user marked private, a bare OIDC provider may release nothing beyond `sub`, and a magic link knows only the address it was sent to. A profile minted from one of those is missing something, and the site has to be able to insist.

  `deactivated` is never entered or left by any of it. That state is a decision about an account, and "nothing is missing" is not an argument against it. @ericof 
- Read a GitHub account's address from `GET /user/emails` instead of hoping it is on `/user`.

  `/user` omits the address entirely for anybody who marked it private, and it carries no `email_verified` key at all. So on that call alone a GitHub sign-in arrived with no email claim — the profile was minted `incomplete` and the required-information flow asked the user to type in an address GitHub already knew — and a GitHub identity could never be auto-linked by a verified address, whatever the account's own verification state. `GET /user/emails` answers both, and the `user:email` scope needed to call it has always been requested, so no operator has to change a registration and no existing user has to re-authorize. The primary verified address is preferred, then any verified one, then an unverified primary: an address is worth having even when nobody will auto-link on it. Drivers still perform no I/O — the GitHub driver names the endpoint and merges the answer, and the flow layer makes the call — so the whole driver layer stays testable against recorded payloads with no provider in the loop. The call is best-effort: a token whose scope was narrowed answers 403 and a provider having a bad afternoon answers 5xx, and neither may turn a missing address into a failed login. @ericof 
- Split a provider's availability from its visibility, and gave it a look.

  `enabled` used to answer two questions at once — whether a provider works, and whether the login screen offers it — so taking a provider off the login page also took it away from every account already signed in through it. It now answers only the first. The new `show_in_login` answers the second: a provider that is enabled but not shown stays linkable from a user's own identities page and still signs in an account already linked to it, which is what a staff-only or invitation-only provider looks like. Providers stored before this setting existed read back as shown, so nobody's login buttons disappear.

  `GET @identities` grew an `available` list for exactly that reason. It is the *enabled* providers minus the ones this caller has already linked, so the identities page no longer has to render the login screen's listing and hope the two questions have the same answer.

  A provider also carries an icon and two colours now — `icon`, `background_color` and `foreground_color`, served on the public login listing so a client can draw a button that looks like the provider it opens. The icon is an SVG document stored as its source, and it is sanitized as it is stored rather than as it is rendered: an icon copied from a brand page carries whatever that page put in it, and what a control panel accepts ends up in the registry, in a GenericSetup export, and in everything else that reads a record. Only an allowlist of elements and attributes survives, no attribute may reference a URL, and anything that is not an SVG document is refused outright rather than quietly emptied. Colours are hex values and nothing else, because the value reaches a style attribute. @ericof 
- The importer now refuses a document naming a provider this site does not have.

  The identity key is `(provider, subject)`. The subject survives a migration untouched, because it belongs to the provider. The name does not: it is `pas.plugins.authomatic`'s `json_config` key on one side and a string an operator types into a control panel on the other, in a different site, after the import has finished.

  A mismatch used to raise nothing at all. The import reported success, and then every migrated person signed in, matched no identity, and was handed a second account beside the one waiting for them — while the migrated Profile kept their name and their groups and belonged to nobody who could sign in. On a real 17-person dump that turned 17 migrated accounts into 17 new ones.

  The check runs before anything is written, including on a dry run, and the message names what is missing, what is configured, and any name that differs only in case — which is the likeliest mistake and the hardest to see, because the two strings look identical in a control panel listing.

  `allow_unknown_providers`, or `--allow-unknown-providers`, is for the deliberate order: import first, configure the providers afterwards. The identities are written either way, so the join starts working the moment a provider exists under the right name. @ericof 
- `GET @my-profile` now reports `missing`: the required fields the profile has no value for, and the reason `review_state` is `incomplete`. Read off the same catalog brain as the rest of the answer, so saying *what* is missing costs nothing more than saying *that* something is, and the endpoint still wakes no object. The frontend needs it to explain itself — a user redirected to a form with no reason given cannot tell a requirement from a broken site. @ericof 
- `GET @user-account/<userid>` answers two questions an administrator could not ask before.

  *Which providers has this person configured?* `@users/<id>` does carry `identities`, but as bare provider ids and subjects. This names each provider, carries its icon and colours so a panel can show the same button the person signs in with, and reports whether the provider is still configured and still enabled -- three states rather than two, because an identity against a provider somebody has since turned off looks like a broken login and reads like nothing.

  *When did this person last authenticate?* Nothing in Plone records it. This package's audit log does, for every route in -- a federated sign-in, a magic link and an ordinary password login all record `authenticated` -- so the answer existed and had never been reachable per user. The endpoint reports it alongside the most recent events, so a panel can show how somebody got in and not only when.

  It also carries the profile's addresses and which of them this site has verified, because a verified address is what `auto_link_by_email` attaches a new provider account to: an administrator looking at one is looking at the other.

  One user at a time, deliberately. The audit log is bounded per user rather than globally, so folding either answer into the `@users` listing would read one bounded log per row on every page of it. `Manage users` throughout, with one exception: a caller asking about themselves, since the same facts are already theirs through `@identities` and `@audit-log` and refusing here would only mean the frontend needing two code paths to draw one panel. 
- `UserProfile` and `UserGroup` keep a version history.

  A Profile is the record of a person, and "who changed this, to what, and when" is a question sites ask about people more often than about pages. Both types now carry the `plone.versioning` behavior and a `repositorytool.xml` policy — two independent pieces of configuration, only one of which is visible on the FTI. A type with the behavior and no policy entry looks versioned everywhere a person can see and keeps no history at all, so the tests assert `getVersionableContentTypes()` rather than the behavior list.

  **This reopened a question the package had already answered, and the answer had to change.** The optional password behavior keeps its hash in an annotation rather than in a Dexterity field, and three places in the source explained why in the same terms: a field is serialized by `plone.restapi`, exported by GenericSetup, indexable, and snapshotted by versioning, so an annotation is invisible to all four.

  Three of those four are true. CMFEditions deep-copies `__annotations__` into a snapshot, so a versionable Profile would have carried every superseded hash in `portal_repository` — a password change that no longer retired the old credential, accumulating somewhere nobody looks, with nothing to say so. That is worse than the field would have been, because a field at least announces itself.

  So the install handler registers a CMFEditions modifier that keeps the credential out of the snapshot on the way in and restores the working copy's on the way out. Skipping alone would have meant reverting a Profile silently cleared its password, which is an account lockout decided in version history. The uninstall handler removes the modifier again.

  The tests include the mutation: switching the modifier off and proving the old hash comes back, because a regression test that passes with the fix removed is not evidence of anything. @ericof 


#### Bugfix

- Fixed a 500 when editing a provider whose configuration carries a list. JSON has one sequence type, so every array in a request body arrives as a list, while the record it is stored in is always a tuple. The coercion asked the driver's schema, which left a key the schema does not declare, and a provider whose driver is gone, going through uncoerced. @ericof [#21](https://github.com/collective/pas-plugins-identity/issues/21)
- A federated first login stopped failing once Profiles became versionable.

  `sync_claims` and `sync_addresses` end in a modification event when they change something, `at_edit_autoversion` answers it by calling `portal_repository.save`, and that is a permission the person being logged in does not have. The callback answered `401` with `"You are not allowed to access 'save' in this context"`, which reads as an authentication failure rather than as a versioning one.

  The Profile *creation* beside it already ran unrestricted, for the reason the docstring gives: the person is mid-login and holds no roles yet. The claim sync now runs the same way — these writes are the package acting, not the user editing. @ericof 
- A login that resolves to an account nothing created now says so instead of raising `AttributeError`.

  PAS answers with a principal whether or not anything became the record behind it. On an ordinary site core writes a `source_users` row; on a site that keeps its users as content the object *is* the account and creating it is the site's own job. A site with those records set and nothing claiming its users therefore authenticates people into accounts that do not exist, and every later lookup of the userid returns `None`.

  The first line to dereference one was the token minting: `AttributeError: 'NoneType' object has no attribute 'getId'`, from a traceback naming neither the user nor the reason. The warning that says exactly what happened was already being logged two lines above it and read as unrelated.

  `mint_token` now raises `PrincipalUnavailable`, naming the userid and what to look for. The callback and the magic-link confirmation both answer 500 with a message saying the site has no account for the user, and log the detail. Deliberately not the 501 they answer when the JWT plugin is missing: that one means the site cannot mint tokens at all, and reporting one as the other sends whoever reads it to the wrong control panel. @ericof 
- A login through an identity whose account was deleted now restores the account instead of signing nobody in.

  An identity outlives the account it was minted for — a user deleted while the identity stayed in the store, an export restored without one half. From then on every login through that identity resolved to a userid nothing could serve: no properties, no roles, invisible to every search, and a traceback from the first line that touched the user.

  It never recovered on its own, and that is the part that matters. The identity is *found*, so the branch that creates a user record is not taken; the login is not a first one, not a link, and nothing else looks. The account stayed missing for every sign-in from then on.

  The same userid is restored rather than a fresh one: it is what the identity points at, what anything the person owns is owned by, and what the store would go on resolving to anyway — minting a new one would strand all of it and leave the same dead record behind. It is logged at warning level, because an account reappearing is not what an operator who deleted one expects, and removing the identity as well is what makes the deletion stick.

  Nothing happens on a site that keeps its users as content: there the object is the account and creating it is the site's own business, which is already reported separately when nothing does. @ericof 
- A provider is no longer seeded a `scope` its driver's schema does not declare. The magic-link provider carried an empty one it could neither show nor clear, which is the value that surfaced the crash above. @ericof 
- An exported document is no longer refused because it carries verified addresses.

  A verified address is stored as an identity under the `email` provider, keyed by the address, so an export has always carried verification among the other identities. The provider-name check added in the same release required every provider a document names to be configured in the target site, and `email` is not a provider anybody configures — so every document from a site that had ever verified an address was refused, which is most of them.

  `email` is exempt from the check now, because it is the store's own marker rather than a provider. Caught by asking what the export already carried before adding a field for it. @ericof 
- An offered address list no longer leaves a site without profiles holding no address at all.

  A driver offered several addresses picks none of them and carries the list, so the user can say which is theirs on their profile. That only works on a site that has profiles: without the `[content]` extra there is no profile, no form and no gate, so nobody is ever asked — and a GitHub sign-in produced an account with no email and nothing anywhere requesting one, which is worse than the guess the choice replaced.

  The question is now asked only where it can be answered. A site that keeps its users as content leaves the list alone and the required-information flow holds the user on the form. Anywhere else the first offer is taken, which is the address the driver ordered first: the account's primary verified one where there is one.

  The test for "can this site ask" is deliberately not the one used before creating a user, which also insists the container resolves. The container is created while the first profile is minted — in a subscriber to the event fired later in the same login — so on the very first sign-in to a fresh site it does not exist yet, and the stricter question would have answered "no profiles" for the one user most likely to be handed a list. @ericof 
- Auto-link-by-verified-email no longer attaches a login to an account that no longer exists.

  The feature attaches a new provider identity to whichever account proved that address to this site with a magic link. It looked the owner up and adopted it, and nothing asked whether that account was still there.

  When it is not — deleted after its address was verified, or a store restored beside a different one — the login *succeeded* and returned a userid nothing resolves: no properties, no roles, invisible to every search, and a traceback from whichever line touched the user first. Signing in with Google after verifying an address produced exactly that, and the callback died in `mint_token`.

  The adoption now checks the account resolves and declines when it does not, saying so at warning level and naming the address so the stale identity can be found. The sign-in then mints a fresh account as it would for any unrecognised identity — not what the operator configured, but a working login, and recoverable: removing the stale identity lets the next attempt link properly. @ericof 
- Both migrations produce users, not only identities.

  `migrate()` wrote each `(provider, subject) → userid` straight into the identity store. That is half of what `link()` does: the other half is firing `IdentityLinked`, and on a site where principals are content that event is what mints the Profile which *is* the user.

  The distinction is easy to lose, because the migration reads as correct either way — the identity resolves, and the person turns up at their first login. What they could not do is exist before it: they were absent from `@users`, could not be granted a role or added to a group, and vanished entirely once the old plugin was removed, which is what the hard cutover the migrations document tells you to do.

  Both link through the plugin now. The claims the authomatic migration had been building all along reach the Profile too, having previously had no listener: the full name and the address arrive with the person. The address is still never inherited as verified, because authomatic did not record whether the provider asserted it.

  The report gained a `users` field — the userids that have a Profile after a live run, or that would gain one on a dry run — and `counts` gained the matching entry. @ericof 
- Brought users who did not arrive through a provider into the required-information flow.

  Everything that minted a Profile or reconciled one hung off `ExternalIdentityAuthenticated`, and only a federated sign-in fires that. So a `source_users` account — the administrator's own login, anybody created through `@users` before the layer was installed, anybody added in the ZMI — was never minted a Profile, was never reconciled, and gave the gate nothing to hold them for. `enforce_required_profile_fields` was therefore a rule about where a user came from rather than about what the site requires of them, which is neither what it says nor what it is for. Logging in by any means now mints the Profile when the user has none and reconciles it either way. A Profile minted this way is seeded from what the site already knows about the person — their fullname, address and the rest, read through the ordered property sheets rather than out of `portal_memberdata` by name — so somebody the site has held for years is not asked to type it all in again the first time they sign in after the layer is installed. Nothing happens on a site without the `[content]` layer, and the Zope root user is skipped: it is not a member of this site, and minting a Profile would file the emergency account among the site's users. @ericof 
- Capped the pending authorization attempts a session keeps, so a browser can still store the flow cookie.

  The attempts live in one signed cookie and nothing bounded how many. Each encodes to roughly 450 bytes, so the ninth pending attempt pushed the `Set-Cookie` past 4096 bytes — the largest a browser is required to store, and over it the cookie is discarded rather than truncated, with nothing said to either side. The browser went on sending the eight-attempt version, the `state` of every login started after that was never stored, and each one came back refused as unknown: {guilabel}`That sign-in link is no longer valid. Please start again.`, with a valid `state` in the URL and a correct one in the log. It cleared up on its own after ten minutes, when the pending attempts aged out, which is what made it look intermittent. Nine abandoned sign-ins in ten minutes is what a person testing a login does. Five are kept now, oldest dropped first: the newest attempt is the flow the person is in, and the cookie stays at about 2.4 KB. @ericof 
- Corrected the `Groups` field description on the `UserProfile` edit form, which told users something that had stopped being true.

  It said that editing the field was the only way membership changed and that there was no write API. `IGroupManagement` made that false: `api.group.add_user` and the {guilabel}`Users and Groups` control panel reach the identity plugin and write the same field. The description was wrong in the place most likely to be read, and the reference documentation carried the same sentence. Both now say the two paths reach the same place. @ericof 
- Created the Profile container before importing principals in the demo identity provider, so the demo user gets a Profile.

  `plone.exportimport` runs `plone.importer.principals` before `plone.importer.content`, and the container is created lazily, so `addMember` ran at a moment when nothing resolved at the configured path. The user adder declined exactly as it is designed to, the demo user landed in `source_users` with no Profile, and the container then arrived with the content import — so everybody created afterwards got one. That is what made it easy to miss: the mechanism looks correct the moment you test it by hand, and only the imported user is wrong. The install log had been saying `'profiles' does not resolve to a container` the whole time. @ericof 
- Declared `defusedxml`, which `core/svg` imports to parse a provider icon.

  It arrives today through another package's dependency graph, which is why every test passed and why nothing said otherwise until a demo image was built from scratch and refused to start on `ModuleNotFoundError: No module named 'defusedxml'`. A package should not depend on what it imports directly arriving through somebody else's requirements. @ericof 
- Fixed UserGroups being invisible to every group lookup except the plugin's own.

  The `[content]` plugin implements `IGroupIntrospection` and the install handler never activated it. `PlonePAS.pas.getGroup` walks exactly that interface, so it found only `source_groups` and answered `None` for every UserGroup — and with it `api.group.get`, `portal_groups.getGroupById` and anything reaching a group the way Plone reaches one, including the sharing tab.

  The group tests all passed throughout, because every one of them called the plugin's methods directly. The ones added here go through the tool instead. @ericof 
- Fixed a 500 on every URL outside a Plone site, including the ZMI.

  `IPubAfterTraversal` fires for every published request, and a Zope instance serves more than one site's worth of them: `/manage`, the root `acl_users`, anything mounted beside the site. The gate asked `api.user.is_anonymous()` before establishing that the request had reached a Plone site at all, and with no portal in the acquisition chain that raises `CannotGetPortalError` — so the traceback named a question about the *user* on a request that never got near one.

  The effect was worse than a broken page. `/manage` and the root user folder are where an operator goes to fix a site they cannot otherwise reach, and installing the `[content]` extra closed both. The gate now answers "nothing to say" for any request without a portal, and still gates every request that has one. @ericof 
- Fixed deleting a group returning a 503 and leaving the group in place.

  `GroupsTool.removeGroup` loops every `IGroupManagement` plugin without guarding the call, and `source_groups` raises `KeyError` for a group it never had. This plugin deleted its content object, the stock one raised on the same id, and the successful delete rolled back with the transaction. The tool now tolerates a plugin that declines by raising, which is the idiom `addGroup` fifteen lines above already used. @ericof 
- Fixed the OIDC `picture` claim, which no relying party could actually fetch.

  Two defects, both on the read path and both silent. `GET @portrait/<id>` returned `stream_data` without a `Content-Length`; that helper answers with plain bytes while the blob is uncommitted and with a `filestream_range_iterator` once it is on disk, and the publisher calls `len()` on what it is handed — so every picture that had really been stored answered 500, while the tests, which set the field and read it back in the same transaction, saw bytes and passed. And the claim published the URL bare, but `@portrait` is a `plone.restapi` service and `plone.rest` only takes over traversal for a request asking for JSON: the URL 404ed for this package's own fetcher, for any relying party that is not a Plone site, and for a browser rendering the claim in an `<img>`. The claim is now published under `++api++`, which resolves for all of them. @ericof 
- Fixed the demo answering magic-link requests with a 500. `Products.PrintingMailHost` was missing from the image, and the demo package now installs *and* loads it rather than relying on an environment variable set in the compose file. @ericof 
- Installing the add-on no longer fails while it is importing its own settings.

  The four registry records naming the user and group content types are derived from the container settings rather than written once, so a subscriber re-derives them whenever a container setting changes. Every registry write in the site reaches that subscriber, and one of the writes that reaches it is this profile's own `registry.xml` — during the very import step that creates the records being written.

  That was safe while the two settings files belonged to two profiles: the core half was always already in place by the time the other one was imported. Merging them inverted the order, and site creation died with `Cannot find a record with name 'pas.plugins.identity.user_content_type'` from a line about syncing.

  Syncing now declines while any record it needs is missing, in either direction — the settings it reads, in a site that has uninstalled, and the records it writes, in a site that is mid-install. `post_install` runs it again once everything exists, so the site ends up with the same values either way.

  Found by the federation demo refusing to start, which is the only thing in this repository that creates a site from scratch in a container. @ericof 
- Made a Profile's `userid` and a Group's `group_id` the object's own id rather than a field stored beside it.

  They were two values that had to be equal with nothing making them so, and they were read by different code: the PAS plugin traverses `container.get(userid)` while the catalog indexes the field. A rename changed one and not the other, after which enumeration still found the principal and every write was addressed to an object that no longer answered to that name — no error anywhere. Deriving one from the other makes that state unreachable.

  No form offers the value and no deserializer can write it; the property accepts a write and discards it, because Dexterity's factory sets every keyword it is handed and payloads exported earlier still carry the key, but a write that *disagrees* with the id is logged. `UseridIsPermanent` is gone with the field it guarded. Renaming is still allowed and the principal id follows the new name — what the old id was written into, from identity records to sharing entries, does not follow it. @ericof 
- Made the authorization endpoint insist on a complete profile, so that the required-information flow actually reaches a federated sign-in.

  It did not. Every route such a sign-in touches — `@@oauth-authorize`, the login page, the callback, the consent screen — is exempt from the gate, each for a good reason, and together they added up to no enforcement at all. A user could sign in to a relying party through this provider with a profile the provider had declared incomplete, and the relying party received an account missing the same field. Found by Érico signing in with a GitHub account that keeps its address private: he was never shown the profile form at all.

  `@@oauth-authorize` now pauses the request at the profile's edit form and carries the authorization request along as `return_url`, resuming it once the profile is complete. The client is told nothing in the meantime — the request is paused, exactly as it is while the user signs in — except under `prompt=none`, where interacting with the user is forbidden and the client is told `interaction_required` instead.

  The request to resume travels as `identity_resume`, not `return_url`. That name belongs to Volto: its edit form reads it and pushes it through the router after a save, and an absolute URL pushed that way is resolved against the current path — so the first version navigated the user to `/profiles/<id>/http:/host/@@oauth-authorize` and showed them two 404s before the real redirect caught up.

  Asked through the `IProfileSupport` utility rather than by importing the `[content]` layer, which the import-linter contract forbids: completeness is that layer's idea, and a site without it has no utility and enforces nothing. `enforce_required_profile_fields` turns this off with the rest of the gate. @ericof 
- Stopped a user from putting themselves in a group by editing their own profile.

  `group_ids` was declared with the same write permission as `fullname`, and the owner of a profile holds that permission on their own profile by design — that is what self-service means. It also meant filling in your name and granting yourself roles were the same action, on the same form, and the form is the one every user is now sent to.

  Group membership has a permission of its own, `pas.plugins.identity: Edit Profile Group Membership`, granted to `Manager` and `Site Administrator` in every workflow state and never to the profile's owner. Every other field is unchanged. Found by Érico editing his own profile in the demo. @ericof 
- Stopped an empty Profile field erasing the value `portal_memberdata` still holds for it.

  PAS resolves a member property by taking the first ordered sheet that *has* the property, not the first that has a value for it. This layer's plugin sits at the top of that order and declared all five properties on every Profile — deliberately, because a sheet that omits a field also stops routing *writes* to it, quietly leaving the Profile not the store for anything it did not already carry. But declaring a field the Profile had no value for meant answering an empty string and stopping the search there, so a user whose Profile was minted without a fullname read back as having none at all: in the user listing, on the author page, and in the `id_token` the `[server]` layer mints, which omits an empty claim and therefore released neither `name` nor `email` for an account that plainly had both. That is every user who already existed when the layer was installed, and every federated user whose provider withheld a claim — GitHub does exactly that for an address the user has marked private. The sheet still declares every field, so writes are unaffected, and a field the Profile has no value for is now filled from the property plugins below it. A Profile that does carry the field still wins, and a field neither store knows stays absent rather than going out empty. @ericof 
- Stopped reporting a provider that cannot start a flow as a provider that is down. Asking to link the email provider answered `502 Provider unavailable`, and clicking {guilabel}`Email` on a login page would have answered the same.

  The email driver has no authorization endpoint and never will — its provider is a mailbox — so the refusal was permanent, while `502` told the caller the provider was temporarily unreachable and to try again. Three other conditions read the same way and were equally permanent: an unconfigured issuer, a provider with no `client_id`, and a `callback_url` that is neither a path nor an absolute URL. All four now answer `400 Provider cannot start this flow`, at every endpoint that starts one. A genuine discovery failure or an unreachable provider is still a `502`. @ericof 
- Stopped serving this package's vocabularies to anonymous callers. `plone.restapi` serves a vocabulary under `zope2.View` unless it is named in `plone.app.content.browser.vocabulary.PERMISSIONS`, so `pas.plugins.identity.UserFields` and `pas.plugins.identity.Groups` were both readable by any visitor — the second listing every group on the site by id and title. Both now require `Modify portal content`, which is what stock Plone puts on `plone.app.vocabularies.Users`. @ericof 
- Stopped writing a `source_users` account beside the content object on a site that keeps its users as content.

  Every federated first login created one: a placeholder row so that "the stock plugins have a complete record". On a site keeping its users as content there is already a complete record — the plugin enumerates the object, and a site that opted into `ICredentialStorage` authenticates against it — so the row was a second record of the same person, kept in step by nothing and outliving what it shadowed. The demo identity provider showed both of its users twice over in {menuselection}`acl_users --> source_users --> Users`. A site that has *not* configured user content is unchanged, because there the `source_users` account is the only record such a user has. Where nothing at all claims a new user, the login still succeeds and core now says so at warning level, naming the type that was not created. @ericof 
- The authomatic converter now understands the provider's own property names, not only Plone's.

  A dump read from authomatic's stored `UserIdentity` carries the keys the provider sent — `name`, `link`, `picture`, `first_name` — rather than the Plone field names its derived property sheet would have produced. `link` is the one that mattered: it is what an OAuth2 provider calls a homepage, authomatic's own shipped property maps translate it to `home_page`, and the converter was silently dropping it.

  Found by running the documented extraction against a real `pas.plugins.authomatic` 2.0.0 store on PostgreSQL/RelStorage rather than against a fixture. `fullname` and `name` now both answer for the full name and `home_page` and `link` both for the homepage, with the Plone name winning when a dump carries both. A key with no Profile field is still dropped, because an attribute nothing declares is invisible to every form and permission in the site. @ericof 
- The federation test stack asks for consent on a page it actually serves.

  The demo points the identity provider's consent screen at a frontend route, which is the interesting configuration and the one the manual stack runs: the question is then rendered in the site's own look rather than by the standalone page the server falls back to.

  The federation test stack runs the two backends and no frontend. It got the same setting, so the first authorization in a fresh stack was redirected to a route nothing serves, the flow test found a 404 where it expected either a consent form or a code, and four tests failed on an assertion about the *URL* for a mistake about the *stack*.

  `DEMO_IDP_CONSENT_URL` now overrides it, and the compose file sets it empty. Empty is a meaningful value rather than "unset", so it is read with `os.environ.get` instead of through the helper that falls back to a default — a helper that could not have expressed it.

  Red since 2026-08-25 and never seen: those tests are docker-marked, and this repository has no remote, so the suite has never run in CI. @ericof 
- The principal container is only ever created as a type that can actually contain something.

  `Document` is the first fallback when the configured container type may not be added where the container goes, because `plone.volto` makes `Document` folderish and a Volto site refuses `Folder` at the portal root. The same id names an ordinary *item* on a site without that add-on, and nothing checked.

  The result was a container that could hold no Profile and could not even be granted the add permission, reported as `The permission pas.plugins.identity: Add User Profile is invalid` — a message about permissions, from a line about permissions, for a mistake about types. Candidates are now filtered on whether their class is folderish, and when nothing addable in the parent is, the refusal names the record to change and lists the folderish types that were available. @ericof 
- `api.user.delete` now deletes a user whose account is a Profile.

  It did not, and the failure was silent in the way that matters: PlonePAS hands a deletion to whichever plugins implement `IUserManagement`, this package implemented none, and `source_users` removed whatever it held — nothing at all, for anybody who signed in through a provider. The Profile stayed where it was, kept answering enumeration and kept serving the property sheet, so the user was still there and the site had reported success.

  The profile plugin implements `IUserManagement` and `IDeleteCapability` now: deleting a user deletes their Profile, and the users listing offers the button because the plugin says it can. It declines for a userid it holds no Profile for, which is how PAS is told to try the next plugin.

  The identity records are deliberately left alone. An identity outliving an account is by design here — it is what lets the same person sign back in under the same userid — and removing one is a separate decision. A login through an identity whose account is gone recreates the Profile and says so at warning level first, so the case is reported rather than silent.

  The plugin is not a credential store, so `doChangeUser` refuses with the `RuntimeError` PlonePAS expects from a plugin that cannot set a password, and password changes go on reaching `source_users` exactly as before. @ericof 


#### Internal

- Raised the coverage floor from 95 to 97. Measured, not estimated: the full suite covers 99.16% with 125 statements outstanding, and the container-free run CI gates on covers 97.57%. 100 remains the target. @ericof [#8](https://github.com/collective/pas-plugins-identity/issues/8)
- Code says why, instead of citing a document its readers do not have.

  Forty-six docstrings, comments, ZCML notes and one registry XML comment justified themselves with an identifier from a planning file that ships with nobody — `S1`, `S2`, `S8` for gates, and `C7`, `D3`, `D10`, `S1b`, `S1d` for decisions. `Exact string comparison, per S8` looks authoritative and carries nothing: a contributor, a reviewer, or the author in a year has no way to follow it. Each now states the reason, or cites something a reader can actually reach. Test docstrings whose entire body was `"""S8."""` or `"""D3."""` say what they assert.

  One had leaked into the product: a registry field description shown to operators began `D3: access tokens are self-encoded…`. One was undefined even in the planning file — `S1d` names nothing anywhere, which is the clearest argument against the habit.

  Section references now name their specification inline, so `§2.4` reads as `Back-Channel Logout 1.0 §2.4` rather than depending on a module docstring several screens away. Where a `§` already sat beside `RFC 6749` or an OpenID specification it was left alone: those a reader can follow.

  Two were stale as well as opaque, which is the other cost of a reference nobody can check. The server's `configure.zcml` said nothing was registered there yet and that the endpoints would arrive "with the rest of Gate S1", while including five of them, every one bound to the server layer. `test_oauth_server.py` said there was no container to point at Plone as a server "until the discovery document lands in Gate S2" — discovery is tested by a class in that same file. @ericof 
- Core reaches the optional `[content]` layer through a utility it declares, instead of importing it inside a function. `IProfileSupport` answers the three questions whose answer changes when that layer is installed — where a user's Profile is, which picture represents them, and where a picture should be stored — and the layer registers something that provides it.

  The import it replaces was a contract violation that looked like a way of avoiding one. `core.serializer` imported `profile.subscribers` inside a function body with a `try: … except ImportError`, and import-linter reads function bodies: the "core never imports the optional layers" contract was **broken**, and `make check-imports` said so. It is green again, and the dependency now points the way the contract wants — the layer imports core, core imports nothing of the layer. It is the same shape back-channel logout already uses to reach the `[server]` layer.

  Nothing about a site without the extra changes: `queryUtility` answering `None` means what the `ImportError` meant. @ericof 
- Gave the vendored container entrypoint a header naming the Plone version it was taken from and what differs from it, and stopped its `import` and `export` verbs passing their last argument twice. The duplicate was harmless only because `plone.exportimport` parses with `parse_known_args`. @ericof 
- Import order across thirteen modules and ten test modules, as the project's own formatter wants it.

  `make format` had not been run over them, so `ruff check --select I` moved twenty-three files the moment it was. Mechanical, and kept as a commit of its own so that it does not sit inside a change anybody has to read. @ericof 
- Made the demo identity provider's user a Profile, password and all.

  They were `alice`, imported from a `principals.json` payload, and the principals importer creates users the way Plone always has: a `source_users` row holding the password, in the site whose entire point is that a site does not need that store. They are now `dana`, created through `api.user.create` — the seat every user goes through — so the shipped adder mints the Profile and the demo profile's `types/UserProfile.xml` enables the password behavior that puts the credential on it. A payload could not have carried that password anyway: it lives in an annotation, which is exactly what an export does not serialize, and that is the reason a credential is kept there rather than in a field. Sign in at `plone.localhost` as `dana` / `dana-demo-password`. @ericof 
- Organised the backend around one concern per module. Each provider driver lives in its own module under `core/drivers/` with the shared normalisation in `core/drivers/base.py`; each REST endpoint family is a package with one module per verb; and the three layers — `core`, `profile`, `server` — are separated well enough that an import-linter contract can hold them apart.

  `requests` is declared as a direct dependency rather than arriving through `Products.CMFPlone`: `core/flows` imports authlib's requests integration at module scope, authlib does not pull it in itself, and a dependency that happens to be there is not a dependency that is there.

  The demo lives in `identitydemo`, a sibling package that is never published — the wheel ships `src/pas` and nothing else. Each demo site is built from data rather than Python: its settings are its profile's `registry` XML, its principals and content are a `plone.exportimport` payload, and what is left in each handler is only what genuinely cannot be static, such as a URL read from the environment. @ericof 
- Pinned `grimp` below 3.16 so `make check-imports` installs again.

  That release ships no wheel for the Python the throwaway venv is built with, so `uv` falls back to building it from source and `maturin` fails for want of a Rust toolchain. The failed install leaves an empty venv behind, so the symptom is `no such file or directory: .venv-imports/bin/lint-imports` — which reads like a broken target rather than like a missing wheel. @ericof 
- Pointed the package metadata at the documentation, and stopped shipping the working copy in the sdist.

  `[project.urls]` gained `Documentation` and `Changelog`. PyPI renders both of those in its sidebar, and the published documentation is where every question this README raises is answered.

  The sdist no longer carries `demo/`, the three Dockerfiles and their `.dockerignore`, `mx.ini`, or `bobtemplate.cfg`. All of them build or run *this checkout* and mean nothing once unpacked somewhere else — `demo/` in particular is the federation demo's own package, which is never published to anything. `tests/demo/` goes with them, since it imports `identitydemo` and would otherwise be a test module that cannot import. @ericof 
- Regrouped `core` by what a module is, rather than leaving twenty-five files at one level.

  `behaviors/` takes one module per behavior, `contents/` the two Dexterity classes, `serializers/`, `indexers/` and `subscribers/` each take their own registrations, and `utils/` takes the helpers that have no policy in them and nothing wired into ZCML — normalising an address, sanitizing an SVG, resolving a claim path, closing a group graph. The line drawn at `utils/` is that line and no other: `catalog`, `completeness`, `container`, `doctor`, `interfaces`, `localroles`, `logout`, `patches`, `portraits` and `verification` all decide something, so they stay one level up beside the things that call them. Eleven files remain where there were twenty-five.

  `core/configure.zcml` is now the four things that cannot move: the sub-package includes, the two class markers, and one adapter. Every other registration lives in the package it registers, next to the code it names.

  `core.subscribers` kept its dotted path by becoming a package whose `__init__` carries what the module carried, which is the shape `core.store` and `core.events` already had. The tests mirror the same folders.

  **This moves two persistent classes.** `UserProfile` and `UserGroup` are stored in the ZODB under their dotted path, so an existing site's profiles and groups are unreadable until it is migrated or rebuilt. The FTI declares the new path, and nothing in Plone can repair an object it cannot unpickle. @ericof 
- Regrouped the `server` layer by what a module is: sixteen files at the top level, now six.

  `controlpanel/` takes the panel, the client registry and the client schema; `grants/` takes authorization codes, access tokens and refresh tokens, which are one sequence rather than three subjects; `consent/` takes the record and the screen that asks for it; `subscribers/` and `utils/` take the rest. Each carries its own `configure.zcml`, so `server/configure.zcml` is four includes. What stays at the top level is what does not belong to any of them: the claims contract, discovery, the PAS plugin, the interfaces and the setup handlers. @ericof 
- The coverage floor is 95 while the gap to 100 is closed.

  100% branch coverage is still what this package holds itself to, and still the target: an authentication plugin has no line that is fine to leave unexercised. The floor is lowered so continuous integration has a gate it can pass in the meantime, with the measured numbers recorded beside the setting.

  The full suite covers 99.15%, leaving 124 statements. `make test` covers 97.52%, leaving 498 — and the difference is not untested code but the 374 statements reached only by the tests that drive containers, which the coverage run does not execute. Raising the floor back is a ratchet, and the work it waits on is those 124 statements. @ericof 
- The federation demo maps `content-site-editors`, and dana is now in it.

  The relying party's group map is keyed on the *provider's* group ids, and the provider releases whatever its users are members of. Moving the map to `content-site-editors` while the only demo user was still in `site-editors` alone would have granted nothing: the claim arrives without that group, the map finds no row, and the federated sign-in produces a user with no `Reviewers` and no error anywhere. dana is a member of both groups now, so the row matches.

  A test keeps it that way. Every key in the demo relying party's map has to be a group at least one exported IdP profile belongs to — the whole failure is silent, so it is checked rather than remembered. @ericof 
- The property-map fallback is gone, because nothing could reach it.

  `IdentityPlugin._apply_property_map` wrote a provider's mapped claims into `portal_memberdata` for a user whose data nobody else claimed, and `_properties_owned_elsewhere` is what told it to stand aside for a user with a Profile. Every authenticated user has a Profile: `ensure_profile` runs from the login event and declines only where the Profile catalog is absent, which is a site this plugin is not installed in. So the guard always answered yes and the body never ran — across the whole suite, which is how it was found.

  Both methods are removed. Nothing changes for a running site: the subscriber applies the same map to the Profile, and the property sheet a Profile serves is what every reader consults first. `tests/core/test_login_ordering.py` still asserts that nothing lands in `portal_memberdata`, which is now a statement about there being no such writer rather than about one declining — and is what would notice the fallback coming back.

  `IOwnsUserProperties` stays. It is the layer's declaration about its own sheet and it is still true; what it no longer does is switch off a second writer, because there is no second writer. Its docstring says so rather than describing a method that is not there. @ericof 
- Wired the quality gates. An enforced 100% branch coverage floor; an import-linter contract keeping `core` free of any dependency on the optional `profile` and `server` layers and those two independent of each other; and a coverage pragma policy requiring a same-line justification on every `# pragma: no cover`, since an unjustified pragma is how a coverage gate quietly stops meaning anything.

  The Plone constraints' `pytest-plone==1.0.0` pin is overridden with `>=1.0.0` in `mx.ini`, which takes the full backend run from roughly 45 seconds to 3. @ericof 
- `make install` provides the demo package, and the container tests get a job of their own.

  Two test modules import `identitydemo` at module scope, and one of them is a `conftest.py` — so an environment without it does not skip a directory, it aborts the whole pytest session with `Interrupted: 2 errors during collection`. `make install` now installs it, because an environment built by that target has to be one the suite can collect in. It reaches neither the published package nor the production image: neither runs `make install`, and the demo deliberately stays out of `mx.ini`.

  `make test` leaves out the `docker` marker — 2568 tests, no containers, and faster for it. The 38 that drive Dex, Keycloak and two Plone sites are `make test-docker`, and `make test-all` is still the whole thing. Use `test-all` before pushing anything touching the flow, the server layer or the demo, because `test` cannot see those.

  The split is what the container tests needed: they run from two Plone sites built by `make demo-image-build`, an image that is built rather than pulled, so every caller of the default target would have needed it. They have their own job now, which builds the image first and fails rather than skips when Docker is missing — a job that exists only for these tests would otherwise go green having proved nothing. @ericof 


#### Documentation

- Corrected the README's account of the layers, and dropped the scaffolding section.

  "The two layers" introduced a core and *two* optional extras, then tabulated three things. The heading is now "Layers and extras", and the text says what the documentation says: one optional layer beside the core, `[server]`, plus `[sql]`, which is an extra rather than a layer because it installs no profile.

  The `plonecli` and `bobtemplates.plone` section is gone. `pyproject.toml` names this file as the long description, so it was telling everyone reading the package on PyPI how to scaffold subtemplates into it — advice for somebody working on this package, on the page for somebody deciding whether to install it. @ericof 
- Corrected two claims in the README that the source does not support.

  ORCID was listed among the identities a user id maps to, as though a driver shipped for it. None does: the five drivers are `email`, `github`, `google`, `oidc-generic` and `plone-identity`. The line now names what is actually there, including another Plone site.

  The package was described as a core plus one optional extra. There are two. `[server]` adds the authorization server layer and a GenericSetup profile of its own; `[sql]` adds an audit sink writing a row per event to a relational database, needs `IDENTITY_AUDIT_DSN`, and installs no profile. Both are tabulated now, because "one extra" left the second one undiscoverable from the README. @ericof 
- Replaced the backend README's "TODO: List our awesome features" with what the package actually does. `pyproject.toml` names this file as the long description, so it is what PyPI will show on the first release: it now carries the feature list, the two layers and their profiles, what is deliberately not in scope, links into the published documentation, and how to run the suite without Docker. @ericof 


#### Tests

- Added `tests/content_types/`, covering the FTI and versioning of both types.

  There were no FTI tests at all. Nothing asserted the class, the schema, the add permission, or which behaviors either type declares in which order — so a behavior added, removed or reordered was a change no test could see, on the two types the whole add-on is built around.

  The layout follows the house pattern: a package `conftest.py` holding everything type-agnostic, and a module per type supplying only `portal_type` and `payload`. Adding a third content type should mean writing a module, not new fixtures.

  Two things differ from that pattern, and both come from what these types are. Principals may only be created where the add permission is granted — which is the container the registry names and nowhere else — so `container` resolves that instead of defaulting to the portal. And this package is not under `tests/core`, so the autouse fixtures that elect those tests as a manager do not reach it and the factory elevates for itself. @ericof 
- Added the end-to-end flow tests. Dex runs in Docker through pytest-docker and the suite drives a browser-less authorization-code flow against it — fetch the providers, follow the authorize redirect, log in at Dex's own form, come back through the callback, and get a `jwt_auth` token — plus the token exchange against a genuine RS256 `id_token`, so signature, issuer, audience, expiry and nonce validation are exercised rather than assumed. Keycloak is there too, for the back-channel logout evidence Dex cannot give: Dex does not implement it.

  The other side is tested against `authlib`'s own `OAuth2Session` — the same library this package uses as a *client*, pointed the other way and knowing nothing about this package — through authorization, PKCE, consent, code redemption and a Bearer-authenticated request to Plone, plus the refusal of a replayed code.

  Three properties are pinned by measurement rather than by argument. Every action fires exactly one event and a refused one fires none, because a double-fire duplicates audit entries and runs subscribers twice while a missing fire makes a subscriber look broken. A client-credentials token request registers **zero** objects with the ZODB transaction, which is the claim the self-encoded access-token design was chosen for. And a GenericSetup registry export describes a provider well enough to read back, which nothing otherwise guaranteed for records created at runtime.

  The `[content]` extra's profile is applied per test module with `@pytest.mark.portal(profiles=[...])` rather than a fixture shadowing pytest-plone's, so every test outside that package still runs against a site where the extra was never installed — which is what makes "core installs alone" something the suite proves rather than assumes.

  The demo handlers import their payload through `plone.exportimport`, whose importers commit for real, and a commit escapes the rollback `plone.app.testing` does between tests. Everything the identity-provider handler wrote therefore stayed in the site for the rest of the session — most visibly its demo user, which a later and entirely unrelated module then failed to create with `Duplicate user ID`, hundreds of tests after the one responsible and invisible to anyone running either module alone. Commits are switched off for the duration of those tests, on the importer class rather than through the environment variable, which `plone.exportimport` reads at import time. @ericof 
- An authorization paused to complete a profile, and resumed, releases the completed claims.

  The scenario a live demo produced on 2026-08-27 and no test covered: somebody is sent here to authorize an application, their profile says nothing about them yet, they fill it in, and the relying party exchanges its code four seconds later — and creates an account with neither an address nor a name. The suspicion was that the server had captured claims when the code was issued, so anything typed afterwards arrived too late.

  It had not. `mint_id_token` calls `claims_for` at token issue, and an authorization code carries a subject and a scope rather than a snapshot of a user. `tests/server/test_paused_authorization.py` holds that from the relying party's side, where it can be seen: the same code redeemed before the form is filled in carries the account as it stands, and redeemed after it carries what was typed. Removing the edit between the two halves is what makes the assertion fail, so it is sensitive to exactly the reported failure rather than to the endpoint working at all.

  Two facts about Plone turned up in the writing and are recorded in the fixture: `api.user.create` refuses a user with no address, and `setMemberProperties` silently drops a write that would blank one. So the fixture starts from a placeholder address and an empty `fullname`, and asserts on both claims changing rather than on either being absent. @ericof 
- Asserted the login transaction note against the *committed* storage record rather than only against the `Transaction` object.

  Every other test in the module reads the description and user off the object in memory, which is one step short of the claim being made: what an operator reads is the undo log, and a description that never survived the commit would pass all of them. The two new tests run on the functional layer, because the integration one forbids the commit that is the thing under test, and they read the record back through `storage.iterator()` — the same record `undoLog` and every ZODB browser show. Both fields are stored as UTF-8 bytes rather than text, which the tests go through rather than around. @ericof 
- Asserted the thing a migration is actually asked: that signing in afterwards lands on the account that was imported.

  Everything else in the export/import tests puts a document in and takes one out. None of it covered what happens next, which involves neither the exporter nor the importer — a real person authenticating at the provider, and either arriving in the account migrated for them or being handed a brand-new one beside it.

  The join is `(provider, subject)` and both halves have to survive. The subject does so without translation: `pas.plugins.authomatic` stores the provider's own user id, and for Google that is the `sub` claim, which is exactly what this package's Google driver reads. Confirmed against a real authomatic 2.0.0 store, where the stored subject equalled the `sub` claim in all 17 identities and all 17 people landed in their migrated account.

  The provider id does not, and cannot be made to: authomatic's provider *name* becomes this package's provider *id*, and that is typed by hand in a control panel, in the target site, after the import. Rename it and the import still reports success while every migrated person signs in and gets a second account — with the first left intact, keeping their name and their groups, belonging to nobody who can sign in. Reproduced on the real dump: 17 migrated accounts became 17 new ones and 34 userids. A test class now holds that failure in place. @ericof 
- Covered group membership through `api.group.add_user` and `api.group.remove_user` rather than through the plugin.

  `addPrincipalToGroup` was exercised only by calling it directly, which cannot tell whether PlonePAS's group tool ever reaches this plugin — the half that has already been wrong twice. The new tests go the way Plone goes, and one of them asserts the membership is visible to `api.group.get_groups` rather than merely written to the Profile, because recording it where nothing reads it would satisfy the other. @ericof 
- Five REST services were reached through the publisher for the first time.

  `@group-members`, `@portrait`, `@user-account`, `@oauth-consent` and `@oauth-grants` were each well covered by constructing the service directly and had never once been fetched over HTTP. That is the gap the direct-construction convention deliberately leaves, and `test_wiring.py` exists to close it: a wrong `name`, a missing browser layer, a permission that refuses anonymous with a login form instead of a body, or a traversal that drops the path segment carrying the principal's id — none of which a direct call can see.

  `@portrait` was the one that most needed it. The `[server]` layer publishes its URL as the OIDC `picture` claim, and the caller is a relying party with no Plone session; the new test fetches a real PNG anonymously and asserts the bytes and the content type.

  Writing them found nothing broken, and two of the assertions had to be corrected rather than the code: a Profile with no picture correctly answers 404, and withdrawing an agreement that was never made correctly answers 404 too. The consent and grants tests now record an agreement first, so the withdrawal withdraws something — a DELETE against a client the caller never authorized answers 404 whether traversal worked or not, which is the one status that cannot distinguish a reached service from an unreached one.

  Separately, `test_the_whole_oauth_namespace_is_exempt` was passing vacuously for two of its four cases. It asserted only that no `/edit` redirect was issued, and a 404 carries no `Location` either — so `@@oauth-jwks` and `@@oauth-userinfo` would have passed had the views not existed. Only `@@oauth-authorize` had a companion existence test. All four now assert they were reached. @ericof 
- Four test modules moved to where their subject already lives.

  `tests/core/` held 21 modules directly beside fifteen subdirectories that already had names for most of what they test. Mapping each flat module to the source modules it imports separated the misfiled from the genuinely cross-cutting:

  - `test_export.py` imports only `core.controlpanel`, and is now in `tests/core/controlpanel/`.
  - `test_property_writes.py` and `test_groups.py` are both about `core.pas.profile`, and are now in `tests/core/pas/`.

  What stays flat stays for a reason. `test_uninstalled_site.py` reaches eleven source modules and `test_login_ordering.py` five; those are claims about the package as a whole, and a flat module is the honest place for them.

  The fourth move is a rename. Two modules were called `test_external_user_record.py`, one in `tests/core/` and one in `tests/core/pas/`, testing the same feature at two levels and cross-referencing each other to explain the split. The split is right; the shared basename put each of them one mistyped path away from silently replacing the other. The integration half is now `test_shipped_user_record.py`, which is also what it is. @ericof 
- Moved the Dex configuration and the Keycloak realm into `tests/_resources/`. They are fixture data for the container stack rather than test packages, and sitting at the top level of `tests/` they read as two more suites. @ericof 
- Pinned the *position* of the identity plugin among PAS's user adders and PlonePAS's group managers, not merely its presence.

  Both interfaces work by refusal, and `source_users` and `source_groups` never decline — so registered below either of them the plugin is never reached, and nothing reports it. Every unit test calling the plugin directly still passes while the feature does nothing through `api.user.create`, which is how the missing ordering was found in the first place. Asserting the plugin is in `listPluginIds` cannot see that difference, so the new test asserts it is *first*, and that more than one plugin is registered — being first means nothing when you are alone in the list. @ericof 
- Removed 48 `api.env.adopt_roles(["Manager"])` blocks that granted a role the harness had already granted.

  The autouse `_manager` fixture in `tests/core/conftest.py` elects every test under `tests/core` as a site manager, and 48 blocks across 16 modules were re-granting it. This was measured rather than reasoned about: all 48 were deleted and the core suite ran 1582 passing, unchanged.

  Two elevations under `tests/core` stay, and the difference is worth naming. `test_completeness.py` adopts `Anonymous`, which is the opposite of a grant. `test_email_linking.py` runs as the `member` fixture rather than as `TEST_USER_ID`, so the role `_manager` grants is not the role that request carries — dropping it there would have been a real regression rather than a cleanup.

  The fixture's own warning is updated: 75 blocks now lean on it across two passes, which raises what is at stake when `plone/pytest-plone#63` finally allows it to go. @ericof 
- Seven groups of near-identical tests became tables.

  Normalising every test body to its structure — literals replaced by a placeholder — found 56 groups within a class whose members differed only in their constants. Most are pairs, and folding a pair trades a sentence of real explanation for a param id, so the pairs were left alone. The groups of three and more were not: there the shape never varied, only the case did, and the case is what a table carries better than a method name.

  `TestResolveClaim` had nine methods that were one call each; `TestDropsWhatRuns` had eight, one per way of getting script or network access past an element-name filter. Both now read as the thing they always were — a lookup table and a threat model. The reasoning that lived in the docstrings lives in comments beside the rows it explains, and every case keeps its name through `ids=`.

  Also folded: `TestKeepsWhatAnIconNeeds`, `TestTheDocument`, `TestCheckChallenge`, `TestSearching` and `TestTheStore`. No case was lost — the suite goes from 2401 tests to 2413, and the twelve added are the new publisher tests. @ericof 
- The opaque userid default is asserted where the demo's choice cannot interfere.

  `test_the_local_userid_is_not_the_providers_subject` was `xfail(strict=True)` in the federation suite and could never have passed there: the demo relying party asks for username-derived userids, and the demo user's username at the provider is also its userid, so a userid equal to the subject and a userid correctly derived from the username are the same string.

  The assertion was worth keeping and the place was not. It is now `test_the_default_userid_is_not_the_providers_subject` in `tests/core/pas/test_userid_source.py`, signing in with a subject that is nothing like a userid, so it says what it always meant: reusing the provider's subject would leak it into every URL that names a user and tie the account to the one provider that issued it. The demo keeps its legible userids. @ericof 
- The server tests stopped redeclaring the same fixtures and constants in every module.

  An `issuer` fixture was written out eight times with byte-identical bodies and eight different docstrings; `plugin` and `userid` twice each. `ISSUER` was declared in ten modules, `REDIRECT` in ten, `SERVICE_USER` in three and `USERID` in five — every copy identical. Meanwhile `tests/server/__init__.py` already existed holding two profile ids, and `tests/core/services/__init__.py` was already the worked example of exactly this: a package `__init__` carrying the values its modules share.

  The constants moved there and the fixtures into `tests/server/conftest.py`. `test_paused_authorization.py` keeps its own `USERID = "dana"`, which was the one deliberate variation in the set. The shared `plugin` fixture now reaches PAS through the `acl_users` fixture rather than `portal.acl_users`. @ericof 
- The suite stopped minting an RSA key per test site.

  Every test portal that applies the `server` profile runs `ensure_keys`, and each fresh portal generated its own RSA-2048 key. Instrumenting `generate_key` put a number on it: **520 keys and 42.9 seconds, a fifth of the entire run**, all of it thrown away microseconds later. The server suite alone spent 51% of its wall clock there.

  A session fixture now generates four keys once and recycles the RSA maths, handing out a fresh `kid` on every draw. Nothing asserts on key *material* — the ring tests assert on `kid`, and no two draws ever share one — so signing, verification and rotation behave exactly as before, including a `kid` absent from the ring failing to verify. `tests/server/test_keys.py` imports `generate_key` by name, so the three tests of generation itself still exercise the real thing.

  The backend suite went from 211.9s to 172.6s, and `tests/server` from 75.4s to 37.9s. @ericof 
- Two test classes stopped repeating their own setup, and one duplicated assertion went.

  `TestOutsideASite` opened both of its tests with the same five lines of `monkeypatch`, and `TestGuard` opened two of three with the same `delenv`. Both now use the `_setup` fixture the other 118 modules in the suite already use.

  While in `TestGuard`: `test_refuses_without_the_opt_in` asserted that `guard()` raises, and `test_says_why_it_stopped` asserted that it raises *and* names the variable in the message. The second cannot pass while the first fails, so the first was never able to fail alone. It is gone and the reason is recorded on the test that replaced it. @ericof 



### Frontend


#### Breaking

- A client's scopes are edited as the list they are, and `OAuthClient.scope` is `string[]`. The two conversions the client form used to do existed only because the backend record was one line of space-separated text; the record is a list now, so the form binds to it directly and the listing renders the scopes comma-separated, the way the grants beside them already read. @ericof [#9](https://github.com/collective/pas-plugins-identity/issues/9)
- The provider form is composed from the backend's schema rather than built here.

  `providerSchema.ts` was 529 lines that turned a descriptor dict into Volto properties, with its own notion of field types, its own ordering, its own secret flag and its own untranslated English. All of that is the backend's answer now, serialized by `plone.restapi` from two interfaces and already translated into the site's language, so what is left here is composition: merge the provider's schema with the chosen driver's, prefix the driver's half so one flat form can carry a nested object, and add the two fields that exist only while a provider is being created.

  Nothing in the frontend decides what a field looks like any more. The colour fields ask for Volto's own `color_picker` and the icon asks for `provider_icon`, both named by the backend through `frontendOptions`. `DriverField` is gone from the types: nothing here describes a field.

  `ProviderIconWidget` is the one widget this add-on supplies. It sends and reads the same `filenameb64:…;datab64:…` envelope Plone stores `site_logo` in, but previews by inlining the document rather than through `/@@site-logo/<filename>` — Volto's own registry image widget builds that URL, and it answers 404 for a provider icon. Inlining is also exactly what the login button does with the same bytes, so what an operator sees is what a visitor gets.

  `fromFormData` no longer trims or corrects anything. Every rule about what a value may be lives on the backend schema, and cleaning up here would only hide which value a refusal is about. @ericof 


#### Feature

- Waits and refusals are drawn over the login card instead of replacing what they are about.

  Both used to displace the page. A wait swapped the options for a line of unstyled text, so the card changed size and the reader lost their place; a refusal appeared as a paragraph that pushed everything below it down, moving the button somebody was about to press. Neither is a different page — they are something happening to the page already there.

  `LoginOverlay` draws both, and the difference between them is who ends them. A wait carries a spinner and no control, because it is not the reader's to end. A refusal carries no spinner — nothing is happening, which is the whole message — and a filled button that dismisses it, because leaving it up hides the form somebody needs to try again in. What is dismissed is the *refusal that was read*, not refusals in general, so a second wrong password says so again rather than being swallowed by the first one's dismissal.

  The picker keeps its buttons while a redirect is in flight and says where it is going, naming the provider that was pressed — which the single-provider page always did and the multi-provider one did not. Greying the buttons says they cannot be pressed; it does not say why.

  The card's body no longer changes height between states, and centres what it holds, so a short one is not left against the top of a box more than twice its height. `MagicLinkForm` was rewritten to wear the same markup and classes as the password form, which are Volto's own: a bare label and input beside a fully dressed form, on the same card, one click apart, was the "fields look strange" of it. @ericof [#12](https://github.com/collective/pas-plugins-identity/issues/12)
- Email sign-in is a button on the login page rather than a form standing open under it.

  The page offered three ways in and treated them inconsistently. A provider was a button; a password was a button that opened its form in place of the list; the magic link was a label and an input rendered inline below everything else. That made the email field the only always-visible input on a page whose question is "choose how you would like to sign in", and the one option that did not look like an option.

  Email is now a `ProviderButton` beside the others, wearing the provider's own title and colours, and pressing it opens the email field on the next step — the same second-step behaviour the password button already had, including the way back to the options. The two ways in that ask for something typed sit together at the end of the list, since neither leaves this origin.

  One disclosure state replaced the boolean, so opening either form closes the other; two open forms is not a state this page has. The email provider stays out of every branch that redirects, because it answers with a message rather than an authorize URL. A site whose only way in is the magic link still gets the form outright: one way in is not a choice. @ericof [#13](https://github.com/collective/pas-plugins-identity/issues/13)
- A user's account is a page in the control panel rather than an overlay on a row.

  The Account action opened `UserAccountPanel` inside a modal, which is the wrong container for it. What it shows is a page's worth of read-only facts about one person — which providers they have configured, which addresses are theirs, what they have done lately — it is not a form with an outcome, and as an overlay it could not be linked to, bookmarked, opened in a new tab or reached with the back button. An administrator comparing two accounts had to close one to open the other.

  It is now a route at `/controlpanel/users/<userid>/account`, and the row's action is a `Link` — the same argument already made in that row for why Edit is an anchor and not a click handler. Volto's own control-panel pattern already covers everything below `/controlpanel/`, so the route needs no entry of its own.

  The page is split into tabs: how they sign in, which addresses are theirs, and what they have done lately. Three separate questions about one person, and an administrator opening the page has one of them in mind rather than all three. When they last signed in stays outside the tabs, because it is the fact the page is about rather than one of its sections.

  Reading the userid back off the path needed care: react-router decodes a route parameter only halfway — a space comes back decoded, a slash does not — so handing it straight to an action that escapes what it is given asked the backend for a userid nobody has. @ericof [#14](https://github.com/collective/pas-plugins-identity/issues/14)
- The sign-in methods page is split into tabs.

  It stacked everything into one column: the providers linked to the account, the providers that could be linked next, and the email addresses on the profile. Those are two different questions, and the page read as a pile — with the addresses, which is where the work usually is, below whatever length the provider list happened to be.

  It now wears the same tabs the control panel's account page does, built on `@plone/components`' `Tabs`. The two pages ask the same question — how does this person get in — one of them as the account's owner and one as an administrator, so they are recognisably one design rather than two. @ericof [#15](https://github.com/collective/pas-plugins-identity/issues/15)
- Added `/applications`, where a signed-in user sees every application they have authorized and can withdraw one. The mirror image of `/identities`: that page is what somebody signs in *with*, this is what they have signed in *to*, and until now only the first half of that existed.

  It is shaped like the control panels: a table of what exists, then one application on its own. A row names it, says when it was authorized and how many fields it reads; opening it names those fields — the claims, not the scope names, because "profile" tells a person nothing while "name, preferred_username, picture" is what they agreed to hand over. Four rows of claim lists is a wall nobody reads, and the person deciding whether to withdraw one wants every field it can reach. An application the operator has since unregistered is still listed and still removable, since the agreement outlived the registration.

  Under the list, in as many words: withdrawing signs an application out everywhere and makes it ask again, and an access token it already holds keeps working for up to the token lifetime this site configured, because the site cannot recall one already issued. Withdrawing asks first, naming the application.

  The user-menu entry sits between "Sign-in methods" and "Site Setup" — the same question the other way round, so it belongs next to it — and appears only on a site whose backend publishes `@oauth-grants`. Nothing in the user payload says whether the `[server]` layer is installed, and `core` may not depend on `server` so its serializer cannot mention it; rather than reach across that boundary the entry asks the endpoint once per session and shows itself when it answered. A site without the layer answers 404 once, nobody sees an entry, and it is not retried. @ericof 
- Added `/fallback_login`, which renders Volto's own login form and nothing this add-on owns.

  This package takes over `/login` completely, so anything that stops its Login rendering — a provider list that fails to load, a misconfigured add-on, a JavaScript error in a component shipped here — is a site nobody can sign in to, including the administrator who would go and fix it. Every route out of that is a page this package draws, which is exactly what is not working. The escape has to be somewhere that shares none of it.

  The name is `volto-authomatic`'s, which ships the same escape at `/fallback_login` and `/failsafe_login`, so a site migrating from it keeps a URL its operators already know. It is registered as a non-content route in its own right: Volto's own `/login` entry does not cover it, because those entries are tested as unanchored regular expressions and `/login` does not occur in `/fallback_login` — without that, Volto asks the backend for a content object at the path and renders a 404 over a page that works. @ericof 
- Added `/identities` and the user-menu entries that lead to it. A signed-in user can see their sign-in methods, add another, and remove one — with the remove button disabled and explained when it is their last way in, rather than failing only once pressed. The page loads in one request rather than two: `@identities` carries the available providers as an expanded component.

  Who is signed in is now shown on the toolbar button that opens the personal-tools menu, as a portrait or as initials on a colour derived from the userid. Volto drew a generic user icon there and a 96px portrait inside the menu — or, for the many users who have never uploaded one, a camera icon: the same picture for everybody, saying "no image here" rather than "this is you". The colour comes from the userid rather than the name, so correcting the spelling of your own name does not change it, and nothing is stored to keep it stable.

  The menu itself is now an ordered list of plugs, Volto's own three entries included. It used to be three fixed entries with a pluggable after them, so an add-on could only append: wanting an entry *between* two of Volto's, or wanting one of them gone, meant shadowing the component. "Sign-in methods" sits straight after "Preferences", because choosing how you get in is one; Site Setup stays last, because it is about the site rather than the person. A user who has a Profile gets it under "Profile", in Volto's slot, since for them the content object is where their fields live; on a site without the layer, and for a user first login has not minted one for, Volto's entry keeps the slot and leads to the member form, which is where *those* users' fields really are.

  The condition is having a Profile, and it is worth saying why it is not the `source` field `@users` reports. Every account this package creates lives in `source_users`: the layer's PAS plugin serves properties and enumeration, it does not authenticate. So a user whose fields are entirely in a Profile still reports `"source": "source_users"`, and a rule keyed on that hides the entry for everybody. The plugin sits above `mutable_properties`, so wherever a Profile exists it is what answers for that user's fields — having one and being backed by one are the same condition.

  All of it reads one store the add-on fills. Volto fetches the current user only when the menu opens and clears it around itself, so nothing outside the menu could rely on knowing who is signed in; a component mounted on every route now reads `@users/<userid>` once per user, carrying the `identities`, `source` and `profile_url` this package's serializer adds.

  **This shadows two Volto components**, `Toolbar` and `PersonalTools`, because Volto has no extension point for the avatar: `toolbar-personal` is a DOM id on a button rather than a pluggable. `PersonalTools` is a TypeScript rewrite rather than a copy with a patch — it is this package's code once shadowed, and carrying a verbatim copy made every improvement look like drift — and both carry a header naming the Volto version they were taken from and what differs, so an upgrade is a diff against upstream rather than a re-reading. @ericof 
- Added an address field to {guilabel}`Sign-in methods`, so an email address can be confirmed and used to sign in. Clicking the emailed link returns to the page with the address added.

  Before this the email provider was rendered as an ordinary provider button, and pressing it started a redirect flow for a provider that has no URL to redirect to: the request was refused, and the page reported that something had gone wrong. Which providers are buttons and which need an address is now decided in one place that both the login page and this one read, rather than in a string each of them kept its own copy of. @ericof 
- Added first-login routing. `/first-login` asks the backend's `@my-profile` where the signed-in user's Profile is and how far along it is, and sends them to it while it is still `incomplete` — so somebody who has just signed up sees their profile once, and somebody who has already filled it in is not asked again.

  Only `incomplete` diverts. A complete or deactivated Profile, a user without one, a site that never installed the `[content]` extra, and a backend error all mean "carry on where you were going": being signed in is not conditional on this answer. The Profile URL the backend reports is turned into a site-relative path before navigating, which in a split deployment is the difference between the frontend's rendering of the Profile and the backend's. @ericof 
- Added the OAuth clients control panel at `/controlpanel/identity-clients`, for a site running the `[server]` layer: it registers, edits and unregisters clients, rotates their secrets, and rotates the signing key — the frontend half of `@identity-clients` and `@identity-keys`. It has the providers panel's shape, which is Volto's own: a table of what is registered, the add action in the toolbar, and the form rendered by `Form` from a schema.

  The form asks for everything the backend will change and nothing it will not: the grants, the scope, the redirect URIs and the service user are on it, while the client id and the confidential-or-public choice are registration-only, because changing either means new tokens rather than an edit. Redirect URIs and scope are edited as the lists they are rather than one text box each, and trimmed of the blanks an exact match would never hit.

  The secret is the part that differs from every other field. It exists in exactly one response — the one that mints it, at registration or rotation — and the server cannot read it back, so the panel does not treat it like a field: it is held in the container rather than read from the store on each render, so it survives the re-listing that follows a create; it is announced as an `alertdialog`, because dismissing it loses something irrecoverable; it is a read-only input rather than plain text so it can be selected and copied from the keyboard; and it is dismissed only when the operator says they have saved it, never by another request resolving. A browser that refuses clipboard access is not an error — the secret is on screen and selectable.

  Public clients are offered no secret rotation, having no secret. A disabled client says in as many words that its existing access tokens are refused too, because the audience is checked against the registry on every request and that is not obvious from the word "disabled". Unregistering one asks first. The key view shows key ids and which one is signing — never key material — and says what rotating past the ring bound costs: tokens still in flight stop verifying. @ericof 
- Added the consent screen at `/oauth-consent`, for a site running the `[server]` layer. A relying party sends somebody's browser here to be asked whether an application may use their account, and answering that on a standalone page that looks like nothing else on the site is the page a careful person should not trust.

  It names the application, and it says who would be agreeing: the browser may hold a session the user forgot about, and agreeing on behalf of the wrong account is the mistake this screen exists to make visible. It lists what would actually be released rather than the scope names, because "profile" means nothing to the person being asked while "name, preferred_username, picture" is the real question; a request that releases nothing says so instead of showing an empty list.

  The answer is a browser navigation rather than a fetch, and deliberately: the authorization endpoint answers a decision with a redirect to the relying party, and it is the browser that has to arrive there. Nothing is decided here — the request travels back exactly as it arrived, and the server decides again from scratch. A request the server would not describe gets no buttons at all. @ericof 
- Added the group mapping to the provider control panel. Each row maps one of the provider's groups onto a group on this site: the provider side is free text, because this site cannot enumerate the far end, and the local side is a picker over the site's groups, because a group that does not exist here grants nothing.

  The mapping is offered only for a driver whose providers have groups — the same switch the backend applies, so nobody is asked to map the groups of a magic link. @ericof 
- Added the identity providers control panel at `/controlpanel/identity-providers`, built on Volto's own machinery and shaped after `volto-light-theme`'s Themes panel: a table of what is configured, with Add in the toolbar rather than a form permanently open at the bottom of the page, and Save and Cancel there while editing. Delete asks first, and the per-provider connection check reports what it found.

  Nothing here enumerates a driver's fields. Each form is rendered from the schema the driver publishes over `@identity-drivers`, so adding a driver on the backend adds its form here with no frontend change — including its declared defaults, its field order, a select for a `choice` field over the options the driver names, and a token widget for a list. A driver's defaults matter more than they look: without them a GitHub provider gets configured with OIDC scopes it does not grant.

  The add form fills in what it can. The provider id is named after the driver and follows it until somebody types one of their own, which is never overwritten afterwards; the attribute mapping is seeded from what the driver declares, so a provider created without touching it still syncs the address and the name onto the Plone user. Both follow the driver rather than surviving it, since a mapping is written in the claim names of the driver it was chosen for.

  The attribute mapping is edited with Volto's `ObjectListWidget`, and its user-field column is a vocabulary rather than free text, so a mapping cannot name a field that does not exist. A stored secret is rendered as the mask the backend sent and saved straight back unless edited, which is what preserves it. The site-wide login callback URL is reachable here too — it lives in the settings rather than on a provider, being one frontend route registered identically with every provider — and a settings payload the backend cannot serve is reported rather than crashing the page. @ericof 
- Added the login page. `/login` replaces Volto's own and offers every way into the site as one list of buttons: a button per configured provider, Plone's own password form as one of them rather than a line of text underneath, and an "email me a link" form when magic-link login is enabled. `/login-identity` is the route providers redirect back to; it hands the code or the emailed token to the backend and receives a `jwt_auth` token.

  A site with exactly one way in does not ask anybody to pick it. The page starts the flow itself and says where it is taking them, rather than rendering one button whose only purpose is to be clicked — but never past a provider that just failed, since start, fail, render, start again is a loop with no way out of it.

  Whether the password form is offered at all comes from `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN`, read at build time and off unless it says otherwise: a site installing this add-on has external providers, and leaving the password form up beside them invites people to create a second way into the same account. An authorization server built on this package is the case that wants it on, since its users *are* local. Turning it off can never leave a site with no way in — with no providers configured the password form is the login page regardless, which is what a fresh install is.

  Post-login redirect targets are restricted to site-relative paths, so a target that never reaches the backend cannot become an open redirect either. The magic-link form says the same thing whether or not the address is known, matching the backend. @ericof 
- Added the required-information gate to the app. While the signed-in user's Profile is `incomplete`, every route redirects to its edit form, and first-login routing now lands on that form rather than on the profile's view — the profile is missing something, and the view asked for one more click to reach the only thing the user could do about it.

  The backend has a gate of its own and deliberately lets `plone.restapi` requests through, because Volto fetches the edit form over the API and gating those would break the page the user is being sent to. Every navigation in this app is such a request, so the backend gate never fires for a Volto site and this is the one that does.

  What is not held is the interesting half. Signing in has to be able to finish and signing out has to stay possible, so `/login`, `/login-identity`, `/logout`, `/first-login` and `/oauth-consent` pass. So does the whole profile, not merely its edit form: the form loads widgets against paths beneath it and saving bounces the user to the profile's view, and redirecting either would be a loop no configuration escapes. A backend that answers with an error is not allowed to make the site unreachable, and nothing is asked for at all while the visitor is anonymous. @ericof 
- Every string the add-on renders is translatable. The login page, the callback, the first-login wait, the identities list, the user-menu entries, both control panels and the secret reveal formatted their text as literal English; all of them now define their messages and format them through `react-intl`, and the extracted catalogues carry the full set.

  Nothing a reader sees changed in English: each message keeps as its `defaultMessage` the exact text the component used to hard-code. @ericof 
- Gave the add-on real styling rather than the structural minimum it started with. The stylesheet used to leave typography, buttons and form controls to the site's theme, on the reasoning that the add-on should look like part of the site; in practice that meant the identities page, both control panels and the login form each looked like whatever a theme happened to leave them.

  The login page now carries the markup and styles `volto-authomatic` uses, which are Volto's own login form's: a fixed-width centred card with a titled header, a description strip, labelled fields under a single underline, and submit and cancel as icon buttons on a divided row — so two add-ons that both replace `/login` do not give a site two different login pages. `/identities`, the callback, the first-login wait and both control panels get the page chrome Volto's own settings pages have: a centred container, a titled panel, and a toolbar whose back action is a route rather than a full page load.

  The root stylesheet holds the design tokens and the handful of base classes more than one component wears; everything that styles a single component lives in a `.scss` beside it and is imported by that component, the way `volto-authomatic` splits its own. Both control panels carry an icon in Plone's control-panel listing, keyed by configlet id — Volto draws a generic placeholder otherwise, and two unlabelled tiles read as two things that did not finish installing. @ericof 
- Groups and profiles have views of their own, and the users control panel can say how somebody signs in.

  Both types are content, so both rendered through Volto's default view: a title and a body that is empty, because neither has rich text. A **profile** now shows the person -- their name, what they wrote about themselves, and their picture. Deliberately not their address: the page's URL is guessable from a userid, and the account's own owner sees their addresses on their sign-in methods page.

  A **group** shows what is in it. The groups nested inside it, the groups it is nested inside, and its members -- including everybody who is in it through a nested group, with the group they arrived through named beside them. A visitor who can see the group without being in it gets the title and description: a membership list is personal data about other people, and it is visible to its own members and to somebody who manages users.

  The users control panel gained an **Account** action per row, answering the two questions it could not before. Which providers this person has configured, named and dated rather than as bare ids, with a badge on an identity whose provider has since been switched off or removed -- the case that looks like a broken login and reads like nothing. And when they last authenticated, which nothing in Plone records: "not in the retained log" is not the same as never, and the panel says so. 
- Login and identity buttons are drawn from the provider's own icon and colours, and the sign-in-methods page no longer asks for an address.

  A provider that carries an icon and colours is rendered as its own button; one that carries neither looks exactly as it did. The icon is inlined rather than served as an image, which is what lets a monochrome one take the button's text colour. The provider control panel grew a **Style** tab for all three, and a **Show on the login screen** switch beside **Enabled** -- two questions rather than one, so taking a provider off the login page no longer takes it away from everybody already signed in through it.

  The sign-in-methods page reads the backend's `available` listing rather than the login screen's, so a provider an operator has hidden is still something an existing user can attach. Magic link is no longer offered there as a form: the box asked for an address and mailed a link to it, which verified any mailbox somebody could reach. In its place is **Your email addresses** -- the addresses already on your profile, each with whether this site has verified it and a button to verify one that it has not. 
- Pointed the users control panel's {guilabel}`Edit` action at a user's Profile, when they have one.

  Volto's action opens a modal bound to `@userschema`, which writes through `portal_memberdata` — for a user whose fields live in a Profile that is the wrong form on the wrong store: it shows only the fields that schema names, nothing the Profile type added, and it edits a place nothing reads for that user. Edit is now a link to their Profile's own edit form. Everyone else is untouched: no `profile_url`, no change, so the site's own `admin` and every user on a site without the `[content]` extra still get the modal. @ericof

  The shadowed components moved out of `src/customizations/` while this landed: `PersonalTools`, `Toolbar` and the new `RenderUsers` are components under `src/components/` with their tests and stories beside them, and each customization file is now the docstring saying why the shadowing exists plus a one-line re-export. 
- The provider form now shows a driver's settings in the tabs the driver groups them into, rather than flattening every one of them into a single Settings column. An OIDC provider gets Settings, Accounts and Groups; a driver that declares no grouping still gets exactly one tab. @ericof 
- The sign-in methods page can say which of your addresses stands for you.

  A provider that knows several of your addresses puts all of them on your profile, so the question there is no longer which one to keep but which one this site should use. That is the *order* of the list -- the backend derives `email` from it, preferring the first verified address -- so **Make preferred** moves one to the front rather than setting a field. The whole list is sent with the `PATCH`, since sending one entry would replace the list with it.

  Offered on every address but the one already chosen, and only when the page was given a handler for it: a button that does nothing when clicked reads as a broken page. A verified address still wins over an unverified one above it, which is why the **Preferred** badge says who won rather than what was last clicked. @ericof 
- `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` is now read at run time, so it no longer decides what is in the image.

  It used to be read in the add-on's settings as `process.env.RAZZLE_IDENTITY_SHOW_PLONE_LOGIN`, written out literally — which webpack's DefinePlugin substitutes into the browser bundle while `pnpm build` runs. That made the answer a property of the built image: a value supplied to a running container reached the Node process and never the browser, so two sites wanting two answers needed two images.

  The Login component now asks at render time instead, through Volto's own `runtimeConfig`. That resolves `process.env` on the server, filtered to `RAZZLE_*` with computed keys DefinePlugin cannot rewrite, and `window.env` on the client, which the server serialized into the page while rendering it. Both sides therefore see the same value and the server-rendered markup matches what React hydrates — which reading `window.env` directly would not have given, since the server would render the default and the browser the real answer.

  `config.settings.identityShowPloneLogin` remains as the default and is still `false`, so a project shipping its own default keeps it and the environment overrides it. The word `false` still reads as off rather than as a non-empty string. The frontend `Dockerfile` no longer takes it as a build argument. @ericof 


#### Bugfix

- The login page no longer shows the password form for a moment before the providers arrive.

  `LoginForm` decided what to render from `providers` and `loading`, and the store slice starts neither loading nor loaded — so between the first render and the effect that dispatches, `loading` was false and `data` was empty. That is indistinguishable, to anything reading those two, from a site with no providers configured, and the branch for that is the local password form. It was drawn, then replaced a tick later by the buttons.

  The container now keys on whether the listing has *answered* — loaded, or failed — rather than on the emptiness of a list nobody has asked for yet. A failure is deliberately treated as an answer: the form's own fallbacks are what a site with no reachable provider list should get, and holding the wait for one would leave it with a spinner instead of the way in that still works.

  The description strip made the same guess in prose, naming the local password form and then replacing the sentence, so it waits too. @ericof [#11](https://github.com/collective/pas-plugins-identity/issues/11)
- The sign-in methods page stops offering email as a way in on a site that took it off the login page.

  A provider with `show_in_login` off is deliberately absent from `@login-providers` and present in `@identities`: a site can stop offering a provider to new sign-ins while people who already linked it keep using it. That is the right rule for an ordinary provider and the wrong one for email — if the magic link is not on the login page, nobody can sign in with it, and a page called "Sign-in methods" that lists it is telling the user something untrue.

  The page now asks for `@identities?expand=login-providers`, which is what the expandable component was added for and what nothing had used, and keys on whether the email driver is among the providers the login page actually offers.

  What changes is the claim, not the button. Verifying an address does a second job the login page has no say over — it is how a later provider login is recognised as the same person — so the verification stays and the sentence that promised a sign-in goes. Removing the button would have taken the account matching with it. @ericof [#16](https://github.com/collective/pas-plugins-identity/issues/16)
- Every label the control panels write themselves now goes through `react-intl`.

  The two schema helpers build Volto forms in plain modules rather than components, so they had no `useIntl` and their labels were English string literals — 17 in the provider form, 10 in the client form: field titles, help text, fieldset names and the form's own title. Every component in the package was already translated; these were the gap, and they are the text an operator reads most.

  Both helpers now take an `IntlShape` and format through `defineMessages`. Regenerating the catalogue also picked up ids that had never been extracted, so the shipped `.po` files were stale independently of this.

  One limitation is now asserted rather than left to be discovered: a driver's *own* field titles and descriptions arrive from the backend over `@identity-drivers` as plain strings rather than message ids, so nothing on the frontend can translate them. They render as sent. @ericof 
- Made the profile gate explain itself and give the user their journey back.

  Two things it did not do, both found by signing in to the demo with a GitHub account that keeps its address private. It dropped the user on an edit form with no indication of why, and once they filled it in it left them there — in that case stranded on the identity provider, half way through signing in to a different site, with no way onward.

  The gate now shows a warning naming the fields the backend says are missing, remembers where the user was going before it interrupted them, and sends them there the moment their profile stops being incomplete. First-login routing parks its destination the same way instead of discarding it.

  The destination is kept in `sessionStorage`, because the step that matters does not preserve a query string: saving the form navigates to the profile's own view. Every access is guarded, since some browsers throw on storage in a private window and there is none at all during server-side rendering; losing the return is a worse journey, throwing would be a blank page. @ericof 
- Shipped the licence with the package, and gave it its own description.

  `package.json` declared `"license": "MIT"` and the package carried no copy of the terms, which is the one thing the MIT licence asks of a distribution. `LICENSE` now sits beside `package.json`, where npm includes it in every tarball whether or not anything ignores it.

  The description was still the sentence the project was generated with — "A Plone add-on implementing a complete OAuth solution" — which is what npm shows in search results. It now says what this half does. `homepage` points at the published documentation rather than at the README anchor, and a `bugs` url was added so npm links the issue tracker. @ericof 
- Signing in to a relying party through this provider no longer ends on a Volto 404.

  The whole flow, from the demo stack: the relying party sends a browser to `@@oauth-authorize`, the backend has no session yet, and Plone's `require_login` bounces the visitor to the login page with the authorization request in `came_from` — *site-relative*. `helpers/navigate` read "starts with a slash" as "a route this app owns" and handed it to the router, so after the provider callback Volto asked plone.restapi for the content at `/@@oauth-authorize`, replaced the authorization request's parameters with its own `expand=` ones, got a 400 and rendered its own 404 at exactly that URL. The relying party received neither a code nor an error (Érico, 2026-08-30).

  Same origin is not the same application. `isBackendView` names the traversal grammar Zope publishes alongside Volto's routes — `@@` for a view, `++api++` / `++resource++` / `++plone++` for a namespace, `acl_users` for PAS — matched per segment, because a view can hang off any object. Those get a real navigation; every other site-relative path still goes through the router, and the open-redirect check on absolute targets is unchanged.

  The profile gate held a second copy of the same premise and returned a completed profile to `@@oauth-authorize` through the router as well — a 404 at the end of the journey the gate exists to protect. It calls `helpers/navigate` now, so the decision is made in one place, which is what it was supposed to be. @ericof 
- Stopped the signed-in user's profile being requested in a loop when the request fails.

  `UserProfileLoader` skipped fetching while a request was in flight and once the user was held, and neither is true after a failure: `loading` goes back to false and nothing was loaded, so the effect fired again on the very next render, for ever. A token that no longer authenticates but still decodes to a userid — which is exactly what a stale token against a rebuilt site is — produced about 150 requests a second against `@users/<id>` in the demo, over a thousand of them, until the tab was closed.

  It now asks once per userid, whether the answer arrives or fails, and asks again when the user changes. The regression test oscillates `loading` the way a failing round trip does; a single render cannot show this, and the first version of that test passed with the fix removed. @ericof 
- Taught the profile gate to honour a destination handed over by the backend. When the authorization endpoint pauses a federated sign-in at the profile form, it passes the request to resume as `return_url`; the gate takes that into the same memory it uses for its own interruptions, so there is one way back rather than two.

  Resuming it is a real navigation rather than a route change, because the target is a backend view: asking the router for `@@oauth-authorize` renders a Volto page that does not exist. Only same-origin targets are accepted — honouring an arbitrary `return_url` with a real navigation is an open redirect, and a link to somebody's profile carrying one would otherwise bounce a signed-in user anywhere. @ericof 
- The application stops throwing itself away to navigate, and asks in the page.

  Six places used `window.location.href` and three used `window.confirm` (Érico, 2026-08-29). A page load fetches the bundle again, rebuilds the store from nothing and re-renders every route already rendered — pure waste for an address this app owns, which three of those six were. A browser dialog blocks the whole browser, cannot be styled, reads as a different application than the panel around it, and forces a test to stub a global to reach the code behind it.

  `helpers/navigate` asks the question once: a site-relative path goes through the router, an absolute URL on this origin gets a real navigation, and anything else is refused — which also closes the open redirect in the `came_from` the callback was handed. The three genuinely external targets, a provider's authorize URL and `@@oauth-authorize`, say `{ external: true }` so the intent is on the call rather than in a comment. Returning to the identities page after a link now refetches the list, which is what the page load it replaced was really for.

  `ConfirmModal` replaces the three browser dialogs, with a destructive button that can be named after what it does — "Withdraw access" is not "Delete". The two plain `<a href>` to Volto routes are `<Link>`, flattened from the backend's absolute URL. @ericof 
- The provider form composes the backend's schema again, rather than being overwritten by it.

  Three things the schema cutover dropped, all of them invisible without a typecheck and none of them caught by a test.

  **The group map came back for every driver.** It used to be offered only for a driver that declares a `group_claim`, which is how the backend says its providers have groups at all. `IGitHubSettings` and `IEmailSettings` declare none, so a GitHub provider and a magic link were both asking an operator to map groups that do not exist — a question with no answer, and a map stored against such a provider grants nothing.

  **The driver picker was overwritten by a text box.** `IProviderRecords` has a `driver` field, because a provider's storage has one, and the merge of the served properties ran after the picker was put in — so the add form offered free text where it meant to offer a list of the registered drivers, and the choice that decides which settings the rest of the form shows.

  **Both mappings were rendered twice.** They are in the served default fieldset as the `Dict` fields they are stored as, and this package rebuilds them as row editors in a Mapping fieldset, because Volto has no Dict widget. A field named in two fieldsets is rendered in both.

  All three are one rule now: the three fields this file composes itself are dropped from the served half rather than merged, and `providerSchema`'s own tests describe what `@identity-providers` really sends — including the three — instead of a convenient subset that could not see any of it. @ericof 


#### Internal

- Every component has a story and the behaviour worth pinning has a test. Storybook was configured from the start and had no stories at all; the fixtures the stories share are the shapes the backend actually returns, taken from `types` rather than invented, so a story that renders is evidence about the real payload rather than about a payload somebody made up.

  The tests render components rather than inspecting them, through a `testing` helper that supplies the `IntlProvider` every component now needs. What they hold still is the reasoning the code is written against: that the login page does not redirect past a failure, that a plug stands down when it would lead nowhere, that a portrait's decoding does not change with the store that answers for it, and that the menu comes out in the order it is meant to. @ericof 
- Gave the provider form a story of its own. `ProvidersControlPanel` opens the form from `useState`, so no story of the panel can reach it, and the listing beside it shows nothing about a provider's mappings — which left both mapping editors with no story at all. This renders the generated schema straight into Volto's `Form`, with the vocabularies loaded, in three states: a driver that has groups, one that has none, and the add form. @ericof 
- Stories render their components in the surroundings those components have on a real page.

  Five pages here portal Volto's toolbar into `#toolbar`, an element Volto's app shell renders and Storybook does not, and Volto's toolbar is wrapped in `withCookies`. Both are read during render, so the stories for those pages did not render at all — one threw on a null portal container, the other on a cookie jar that was not there. A global decorator supplies the host, the provider, and the four store slices Volto's own chrome selects whatever the page is. Which four was established by removing each in turn rather than guessed: three of the seven first written were not read.

  The user-menu stories were a second case of the same thing. Every rule for `.pastanaga-menu`, `.pastanaga-menu-list` and `.toolbar` is nested under `#toolbar` in Volto's stylesheet, so the class names alone style nothing — three menu stories had a bare `<ul>` and rendered an unstyled column of links, and the shadowed personal-tools menu looked broken despite carrying the markup already. Three of the five that did have the markup carried their own copy of it, which is the other half of the problem: five copies of a nesting that belongs to Volto drift, and only one gets checked when Volto changes it.

  It is written once now, in `storybook/`, and rendered into the single `#toolbar` there can be — a second one earlier in the document would shadow the host the pages portal into. The login stories render inside the real `LoginPanel` rather than a `div` of the same width, so a change to the card cannot leave them behind. Tests cover the parts that would regress silently: that a page portalling its toolbar renders, that the menu markup lands where its stylesheet reaches it, and that only one `#toolbar` is ever made. @ericof 
- The layer half the comments and stories describe no longer exists, so they describe what is left.

  No behaviour changed, and that is the point worth recording: every state the add-on branches on survives the backend merge under a different name. "A site without the `[content]` extra" becomes "a user whose first login has not minted a Profile yet", or an account that predates the add-on — both real, both still reached by the same code. `profile_url` stays nullable and `profileHoldsTheFields` still keys on it.

  One claim in `helpers/profileSource` was made wrong by the merge rather than merely dated. It said every account this package creates is a `source_users` one; a user who signs in through a provider now has only a Profile and reports `identity_profile` as their source. The helper was already right to ignore `source` — that is exactly why — but the reason it gave for ignoring it no longer held.

  Two stories are renamed for the same reason: `NoProfileLayer` is `NoProfile`. @ericof 
- `tsc` runs, and `make lint` runs it.

  There was a `tsconfig.json` and no way to act on it: no script invoked the compiler and no gate called the script, so fifteen type errors had accumulated where nobody would meet them. `pnpm typecheck` runs `tsc --noEmit` and `make lint` runs it beside eslint, prettier and stylelint.

  Its `exclude` list was also not doing anything. Tests, stories and fixtures were listed as `**/*.test.{js,jsx,ts,tsx}` and friends — TypeScript's globs understand `*`, `?` and `**/` and have no brace expansion, so each pattern matched only a file named that literally. They were being checked all along, which is how the fixtures were found to describe a schema shape the backend stopped sending; the patterns are gone rather than corrected, because checking them is what caught it.

  The fifteen: `VoltoSchema` was deleted from `providerSchema.ts` by the cutover and its import moved to `types`, where it was never added — a type-only import, so nothing failed at runtime and no test noticed. The gate's `appExtras` entry was missing the `props` Volto declares required. Two `MyProfile` fixtures were missing a required field. `react-intl` 3.12 types `IntlProvider` without `children`, which React 17 supplied implicitly and React 18 does not, so `testing` exports it repaired and the tests that bring their own provider use that one. The stories were calling `providerSchema` with the signature it had before the cutover, and `stories/fixtures` still described drivers in the schema language the cutover removed. @ericof 


#### Documentation

- Replaced the frontend README's empty features comment with what the add-on registers: its routes, the two control panels, the profile and group views, the `provider_icon` widget, and why each of the three shadowed Volto components could not be extended instead. The Storybook badge pointed at a site that does not exist and now points at the published one, the install block names the `addons` array that actually registers the add-on, and the Volto 17 instructions went, since the package requires Volto 18. @ericof 
- Rewrote the README in plain Markdown, and corrected the Volto version.

  This file is the package's README on npm, which renders neither the centred `<div>` header the project was generated with nor GitHub's `> [!NOTE]` and `> [!IMPORTANT]` callouts — the first was dropped by the sanitizer and the second appeared with its marker showing. Both are ordinary Markdown now, and the file contains no HTML at all.

  It also claimed Volto 18 and above. The checkout pins 19.3.0, the peer dependencies are the Volto 19 stack, and the frontend install guide already said as much, so the README now says Volto 19 and links to that guide for the full requirement table. @ericof 



### Project


#### Breaking

- Users and groups as content is no longer an optional layer. The documentation, the federation demo and the CI matrix follow.

  The concepts pages that described three layers describe two. {doc}`concepts/layers` keeps the argument for the boundary that is left and adds the argument against the one that went: a layer earns its boundary when the combinations it creates are ones somebody wants and somebody tests, and `[content]` failed both halves — its dependency ships with Plone, so nobody was ever spared anything, while the option created a second configuration of every code path that touches a user.

  {doc}`how-to-guides/install` carries the upgrade note, prominently, because there is no upgrade step and the failure mode is silent: a site installed by an earlier version looks installed and has no content types, no catalog and no `identity_profile` plugin until the add-on is reinstalled.

  The federation demo's identity provider stops depending on a profile that no longer exists. The relying party gets the content types too, which it did not before — that follows from the merge rather than being chosen, and the demo README says so.

  The backend CI matrix drops from four dependency configurations to two, `core` and `+server`, and the import-linter contracts from two to one. @ericof 


#### Feature

- The demo stack's two hostnames follow `DEMO_STACK_DOMAIN`, defaulting to `localhost`.

  `id.localhost` and `plone.localhost` were written out eighteen times — Traefik's routing rules, the virtual-host rewrites that tell Zope what URL it is answering, the network aliases that make one hostname resolve in the browser and in a container, the issuer, and the redirect URI. Changing the domain meant changing all of them consistently, and the failure mode for missing one is an issuer that does not match itself.

  Google will not register a redirect URI on a `.localhost` host, which is what makes this more than tidiness: pointing `id.` and `plone.` at 127.0.0.1 in `/etc/hosts` and exporting `DEMO_STACK_DOMAIN` is now enough to run the whole demo under a domain a real provider will accept. The default is unchanged, so `make demo-stack-start` needs no DNS and no hosts file. @ericof 
- The documentation and Storybook are built and published together as one site.

  Storybook was deployed by `frontend.yml` straight to the root of the `gh-pages` branch, and the documentation was built and uploaded as an artifact that nothing ever published. Adding a docs deployment to that arrangement would have had the two halves overwriting each other, one per run, depending on which finished last.

  They are now assembled by a single job and deployed once: the documentation at the root, Storybook under `/storybook/`. Neither builder deploys on its own — `docs.yaml` and `tmp-frontend-storybook.yml` upload artifacts named after the ref, and `tmp-docs-publish.yml` downloads both, so one artifact and one deployment mean neither half can clobber the other.

  Storybook is built from `main.yml` rather than `frontend.yml`, only on the branch that publishes and only after the frontend jobs it would otherwise duplicate have passed. A skipped builder is handled rather than fatal: a docs-only change still publishes, falling back to the artifact name the skipped builder would have computed for this same ref.

  The `storybook-deploy` config output is now `deploy-docs`, since it gates the whole site. The two `tmp-` workflows are forks of their `plone/meta` counterparts, which deploy on their own and cannot be composed this way; the prefix marks them as living here only until upstream grows the same capability.

  This needs the repository's Pages source set to "GitHub Actions". @ericof 
- The federation demo stack now runs on a single PostgreSQL instead of two ZEO servers: a database each for the two sites' ZODBs through RelStorage, and a third for authentication records. Only the identity provider writes its records there, so the stack shows both arrangements at once. CI grew a `+sql` job so the new extra is installed and exercised alongside `core` and `+server`. @ericof 


#### Bugfix

- A push that changes no documentation no longer breaks the published site.

  `deploy-docs` assembles the artifacts uploaded by this run, and `download-artifact` only ever looks in this run. The docs job is path-filtered, so a backend-only push skipped it, left no artifact to fetch, and failed the deploy on its first step — with the site's own content unchanged and perfectly publishable.

  The fallback that was supposed to cover this named the artifact the skipped builder would have produced, which is a name rather than a file: it turned a skipped job into a failed deploy instead of rescuing it. Documentation and Storybook are both built unconditionally on the branch that publishes now, so the site always matches the commit it was built from, and the deploy takes its inputs from the jobs that actually ran. @ericof 
- Gave `SECURITY.md` a real reporting address.

  It carried the placeholder it was generated with — `security@example.org`, under a TODO saying to replace it before the first public release. Reports now go to `admins@plone.org`. For a package whose whole job is authentication, an address nobody reads is worse than no address at all: the finder concludes the project does not want to hear from them, and publishes instead. @ericof 


#### Internal

- Added the CI pipeline. The backend test suite runs in all four supported dependency configurations — core, `+profile`, `+server`, all — across Python 3.12, 3.13 and 3.14, with the layer-boundary contract checked as a job of its own.

  Three checks exist because the alternative is a gate that quietly stops meaning anything. `make check-clean-install` installs the package with no extras into a throwaway virtualenv and imports it, so a runtime dependency that only the test extra happens to supply cannot pass unnoticed. `make check-pragmas` requires a same-line justification on every `# pragma: no cover`. And the Docker-backed flow tests are mandatory in CI: without `PAS_IDENTITY_REQUIRE_DOCKER` a machine with no Docker skips them, which is right for a laptop and quietly wrong for a pipeline.

  The documentation is built with warnings as errors. @ericof 
- Added the federation demo: two full Plone sites in a browser, one signing users in against the other. `make demo-stack-start`, then open http://plone.localhost and sign in as a user who exists only on http://id.localhost. It lives in `docker-compose.demo.yml` with its own `demo-stack-*` targets, separate from the one-site development stack on purpose — growing that into this would build two Volto frontends for everyone running `make stack-start`.

  The provider is a Volto-first identity provider, which is what it should look like: only the cookie-auth challenge path is routed to the backend, `/login` is Volto's, and the consent screen is the frontend route rather than the server's standalone fallback. It offers magic-link login first, because that is the one way into the demo that needs nothing configured anywhere else — no OAuth client, no secret, no account at a third party. Nothing is delivered: `Products.PrintingMailHost` writes the message to the log, and `make demo-stack-logs` is where the link is.

  The relying party uses the `plone-identity` driver rather than the generic OIDC one, since that is the driver a Plone-to-Plone federation is meant to use and the one whose defaults the demo should be proving, and it allows the avatar to be fetched over plain HTTP because two containers on a laptop have no certificate between them. `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` is set per frontend — as a build argument, since Razzle bakes those into the browser bundle and a runtime one would never reach it: on for the provider, whose users are local, and off for the relying party, where a local password beside the federated sign-in would be a second way into the same account. The two frontends therefore build two images rather than sharing one.

  Documented in `docs/docs/tutorials/federation-demo.md`, with the design reasoning in `docs/docs/concepts/federation.md`. @ericof 
- Made the demo stack's example content something that can be exported back out of it. Each backend mounts its payload directory at `/example-content`, and the image carries an entrypoint with `import` and `export` verbs the upstream one does not have.

  The setup handlers already told anyone reading them to "configure a site, run `plone-exporter`, and commit what comes out". This is what makes that possible without a checkout inside the container. @ericof 
- Removed the working documents from the documentation rewrite.

  `docs/AUDIT.md`, `docs/AUDIT-CODE.md`, `docs/CHANGES-DOCS.md`, `docs/TUTORIAL-RUN-LOG.md` and `docs/HUMAN-ACTIONS.md` each opened with "Working file, not published" and referred to a branch that no longer exists. They were the scaffolding the rewrite was built on, and the rewrite has shipped. `docs/STYLE.md` stays: it is the house style, and it is still in force. @ericof 
- Renamed the demo stack's sign-in user to `dana`, whose password lives on their own Profile rather than in `source_users`. @ericof 
- The backend workflow builds what the container tests need, and stops asking every job for it.

  `Backend: Container integration` builds the federation demo image and runs the tests that drive real containers. The three-Python matrix, the two extras configurations and the coverage job no longer collect them, so none of them needs Docker or an image built from this tree. @ericof 
- The demo stack builds one frontend image instead of two.

  Both sites ran the same frontend and always had; they differed only in `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN`, which was a build argument because the value was substituted into the browser bundle. Now that it is read at run time, the difference is an environment variable and the second build had nothing left to do. `idp-frontend` builds the image and names it, `rp-frontend` runs the same one and waits on it so a clean `docker compose up` cannot race an image that does not exist yet.

  The documentation said `RAZZLE_` variables are substituted into the bundle when the frontend is built, and therefore that the demo builds two images. The first half is true only of `process.env.RAZZLE_SOMETHING` written out literally; both halves are corrected. @ericof 


#### Documentation

- Documented restricting sign-in to certain groups, including that it needs a group claim and that a provider whose driver has none refuses everybody. @ericof [#4](https://github.com/collective/pas-plugins-identity/issues/4)
- Documented the provider that sends verification flags as text, and its symptom: sign-in works and only the linking silently does not. @ericof [#5](https://github.com/collective/pas-plugins-identity/issues/5)
- Documented declining to let a provider create accounts, and why the two linking switches are required with it. @ericof [#6](https://github.com/collective/pas-plugins-identity/issues/6)
- Documented keeping a provider for sign-in while deciding group membership locally. @ericof [#7](https://github.com/collective/pas-plugins-identity/issues/7)
- Documented that a client's `scope` is a list, that the control panel offers the scopes this server releases claims for, and that a scope outside that list is still accepted through the API for a client whose own resource server checks it. @ericof [#9](https://github.com/collective/pas-plugins-identity/issues/9)
- Documented that the avatar fetch's timeout and size cap are settings rather than constants, on both pages that describe what the fetch enforces. @ericof [#10](https://github.com/collective/pas-plugins-identity/issues/10)
- Added a Contributing page to the documentation, and an `AGENTS.md` at the root of the repository.

  Setting up a checkout, the gates a change has to pass, which formatter owns which file type, the three towncrier scopes and the layer boundary were only in the README, where a reader arriving from the published documentation never saw them. They are a page now, and the README stays the short introduction it was.

  `AGENTS.md` is the same ground for coding agents, plus the traps that are only discoverable by hitting them: ruff's configuration lives in `backend/pyproject.toml` and covers the backend alone, `make check-imports` is not part of `make lint`, `frontend/core` is a `mrs.developer` checkout and not ours, and `sphinxcontrib-mermaid` reads its `:config:` option as JSON while claiming any leading `---` block inside the fence. @ericof 
- Added a state diagram for each of the two workflows to the profiles and groups reference, and said which permission guards each transition. The pages already listed the states; what they did not show is which transitions exist between them, or that reactivating a profile returns it to `incomplete` rather than to `complete`. @ericof 
- Added the documentation site: Sphinx with MyST on the Plone Sphinx Theme, generated from Cookieplone's `documentation_starter`, built in CI with warnings as errors and published from `docs/`. It is organized by Diátaxis, so every page belongs to exactly one quadrant: a tutorial, how-to guides, reference, and concepts. Vale runs the Microsoft style checks against a project vocabulary, and `make linkcheckbroken` keeps the cross-references honest.

  The how-to guides cover installing the package, configuring a provider and its secrets, reading the audit log, enabling back-channel logout, registering an OAuth client against the `[server]` layer, writing a driver, and both migrations. The reference covers the shipped drivers, the event contract this package treats as its public API, the audit log's endpoints and privacy defaults, the `[server]` layer's claims contract and OpenID Connect discovery, the `[content]` extra's content types and workflow states, the fields a migration report carries, and the security properties the test suite enforces.

  The concepts pages carry the reasoning: why one user id maps to many identities and the mapping is never guessed, why the three layers may not import each other, what `email_verified` asserts and why a provider's word is not enough, why a provider secret can be echoed back and a client secret cannot, why the content layer never wakes a content object and what that costs against `Products.membrane`, and why a federation issuer is configured rather than derived. The tutorial runs the federation demo end to end: two Plone sites, a consent screen, a magic link, and withdrawing consent.

  Writing a driver has a guide and a worked GitLab example, carrying the three rules a driver author has to follow: every config field declares an `order` and no two share one, `default_scope` is a tuple of permissions rather than the space-delimited string that goes on the wire, and `default_propertymap` is written against the normalized claim names and names only member fields a stock site has.

  The README carries the feature summary, the relationship to `pas.plugins.oidc` and `pas.plugins.authomatic`, and a "why not `Products.membrane`" section that says what was actually read rather than what was assumed: membrane's `getPropertiesForUser` adapts `brain._unrestrictedGetObject()`, so a property lookup wakes the content object, while its user enumeration is unaffected and stays on the brains. `SECURITY.md` records how to report a vulnerability and what this package guarantees.

  Keeping a site's users and groups as content is now covered too, which it was not when the feature landed. `concepts/users-as-content` explains why core declares a contract an optional layer provides, and `reference/user-content` states the four registry records, the `IUserContent` and `IGroupContent` contracts, `ICredentialStorage`, and the six ways the plugin declines. Both carry the ordering the feature depends on: the plugin has to be asked before `source_users` and `source_groups`, which never decline, so reordering PAS plugins switches the feature off with no error and no log line. The reference also said there was no write API for group membership, which `IGroupManagement` had made false. @ericof 
- Corrected the claim that an annotation is invisible to versioning.

  `user-content.md` explained why the optional password behavior stores its hash in an annotation rather than a field: a field is serialized, exported, indexed and snapshotted, and an annotation is none of those. Three of the four were right. CMFEditions copies annotations into a version snapshot, which the docs now say, along with what the add-on does about it. @ericof 
- Corrected the documented `pas.plugins.authomatic` extraction script, which did not work.

  It was written from a reading of authomatic's source and never run. Running it against a real 2.0.0 store on PostgreSQL/RelStorage found two faults, both of which produce a wrong answer rather than an error.

  It never called `setSite()`. `UserIdentities.propertysheet` reads authomatic's configuration out of the registry, and the registry is a local utility that `queryUtility` finds only once the site is the active component site; traversing to `app.Plone` does not make it one. The script therefore died on the first user with `AttributeError: 'NoneType' object has no attribute 'forInterface'` — and on a site with no authomatic users it exited `0` and printed an empty, perfectly valid dump instead, which is the worse of the two.

  It read the derived property sheet rather than the stored identity. That sheet is rebuilt by walking the providers currently in `json_config` and applying each one's `propertymap`, so an identity whose provider has since been removed, renamed, or was never configured on this site contributes nothing to it — silently. The stored `UserIdentity` still holds the name and the address. Reading the sheet would hand you users with no address at all, and every one of them is then skipped on import for exactly that reason.

  The documented script now sets the site and reads `_identities`, and the reference page says why both are load-bearing. @ericof 
- Corrected two things the root README got wrong.

  It claimed Volto 18 while the checkout pins 19.3.0 and the frontend install guide already said so, and its "Linting the codebase" section had lost its opening sentence to an orphan fragment reading "or `lint`:". @ericof 
- Documented group federation across the docs, not only where it is configured: the concept in `federation.md`, the membership half in `profiles-and-groups.md`, which drivers carry a group claim in the drivers reference, two entries in the security guarantees, and a step in the federation tutorial where a group actually crosses.

  Corrected two claims that were already stale: the drivers reference said the `plone-identity` driver takes the remote `sub` as the local userid, when it has taken `preferred_username` since it shipped. @ericof 
- Documented group federation: the `groups` claim in the claims reference, and how to map a provider's groups to local groups in the provider how-to. Corrected the claims reference's scope table while there — it had listed `profile` as releasing three claims when the server had been releasing five for some time. @ericof 
- Documented that a migration produces users, and the `users` field that reports them.

  The migration-reports reference now lists `users` beside `identities` and `providers`, and states the guarantee behind it: both migrations write through the plugin rather than into the identity store, so the event that mints a Profile is fired for every identity they claim, and a migrated person is in `@users` without waiting for their first sign-in. @ericof 
- Documented that the authorization endpoint enforces profile completeness itself, why the gate cannot do it during a federated sign-in, and what a client is told while the request is paused. @ericof 
- Documented the export/import of principals: a how-to guide covering the two console commands, the dry run and the offline `pas.plugins.authomatic` path, and a reference page giving the document format, both refusal and skip conditions, and the shape of a dump with a working extraction to produce one. @ericof 
- Documented the importer's provider-name check, and the flag that turns it off.

  The how-to now shows the `--allow-unknown-providers` form for importing before the providers are configured, and says what the flag does and does not change: the identities are written either way, and only the check that the name is one this site knows is skipped. The reference page lists the refusal alongside the others and explains why this one is worth knowing about. @ericof 
- Documented the role a user holds on their own profile. It is `Owner` now rather than `Editor`, and the reference page lists the eight permissions the workflow states so that owning a profile does not come to mean deleting it, adding content inside it, or opening it in the management screens. @ericof 
- Documented the separate permission that guards group membership on a profile, and that `fullname` is now required. @ericof 
- Documented the whole of this workload: the split between a provider working and a provider being advertised, the style an operator can give one, groups inside groups, a Profile's list of addresses, and the two new endpoints.

  The provider how-to gained the two switches and the **Style** tab, and lost a claim that had become false -- configuration has not been one JSON record since the records were split per setting.

  `concepts/profiles-and-groups` and `concepts/users-as-content` said group nesting was refused, and said why. The reason was half right: the recursion is real, and the conclusion drawn from it was not, because the group graph grows with the number of teams rather than the number of people and one catalog query returns all of it. Both pages now describe what happens instead, including what a cycle and a deactivated group do. `reference/user-content` narrowed its refusal to a group inside *itself*, and `reference/profiles` lost its "limits in version 1" note.

  `reference/profiles` describes the address list and the derived `email`, and `concepts/email-verification` gained the rule that a magic link only ever goes to an address already on your profile -- with the reason, which is that the proof is proof of control over whatever was typed.

  `reference/security-guarantees` gained three: the address rule, the icon sanitizing (and why it happens on save rather than on render), and what a nesting grants. A new how-to, **How to review a user's account**, covers the two questions the users control panel could not answer. 
- Documented what happens while a profile is incomplete: the redirect, the record that turns it off, and every path that is deliberately not held., including the OAuth authorization endpoints and the record for naming your own. @ericof 
- Documented what the two working profile states mean now that the add-on keeps them true, and the registry record naming the fields a profile must carry. It also records that a required field need not be required on the type, because `@types` reports both. @ericof 
- Documented where user profiles and groups may be created: only in the container the registry names, which the reference page now states along with the two add permissions and how to open a second folder deliberately. @ericof 
- Explained what a verified address is, and who decides whether a migration keeps one.

  The reference page now says that verification is an identity under the `email` provider rather than a flag — which is why an exported document carries it without a field for it, and why `email` is exempt from the provider-name check. Both that page and the how-to explain the two separate questions a migration asks: a site that trusts a provider at a login needs nothing, and a site that does not can still accept the addresses its old site collected by passing `--trust-verified-emails` for that run. The how-to says explicitly not to switch `trust_email_verification` on and off around an import instead, and why. @ericof 
- Gave the repository root a `LICENSE.md`.

  The two halves are licensed differently — `backend/` is GPL-2.0-only and `frontend/packages/volto-identity/` is MIT — and each carried its own text while the root carried none, so GitHub read the whole repository as unlicensed. The new file says which license covers which path, links both texts, and notes that `frontend/core` is a `mrs.developer` checkout of Volto rather than part of this repository. @ericof 
- Renamed the layer and its two content types throughout the documentation and the demo stack. The optional extra is `[content]` rather than `[profile]`, `IdentityProfile` is now `UserProfile` and `IdentityGroup` is now `UserGroup`.

  Each layer is also installed by its own GenericSetup profile now — `pas.plugins.identity.content:default` and `pas.plugins.identity.server:default` — so the add-ons control panel lists all three layers as separate entries. The install guide and the layers concept page say so, including why the two optional entries show no version. @ericof 
- Reworded the one sentence in the user-content reference that put spaces around an em dash, which was Vale's last remaining error. @ericof 
- Rewrote the documentation against the source, and grew it from 33 pages to 57.

  Eight reference pages did not exist and are now written: every endpoint with the permission it enforces, every registry record with its type and default, the provider form as the control panel actually composes it, the Volto add-on's surface, the six permissions, every GenericSetup profile, the driver contract, and what the alpha promises. Seven provider recipes join them, along with how-to guides for installing the frontend, troubleshooting by symptom, upgrading, linking accounts by email, mapping provider groups, and controlling account creation. Two concept pages are new: a mental model with diagrams, and a threat model.

  Writing them against the code found things the documentation had wrong. `google` and `github` have no group settings at all — their schema is `IOAuth2Settings`, which carries no group claim, no allowed-groups list and no sync switch — so the pages that told an operator to configure those fields were describing a form that does not exist. The `email` driver has no account settings either, and a missing `create_user` reads as `True`, so an `email` provider always creates accounts. The whole `IProfileSettings` group of twelve records was undocumented, as was `server_issuer`. Nine endpoints take sub-paths that the endpoint table listed as bare, where a bare POST is a `400`. ORCID was advertised as a shipped provider and no such driver exists.

  Reference pages are tables now rather than prose, and the reasoning that was mixed into them moved to the concept pages where it belongs. Every page ends somewhere. `reference/profiles.md` became `reference/profiles-and-groups.md`, because "profiles" already meant GenericSetup profiles two files away.

  The tutorial was run end to end before it was rewritten, which is how five more defects surfaced — including a magic-link section that could not be performed as written.

  Screenshots are captured by a committed Playwright harness rather than by hand, and a test fails when a page references one that nothing captures. Diagrams are Mermaid, so a typo in one is a diff. `docs/STYLE.md` records the house rules the rewrite followed. @ericof 
- Rewrote the email-verification concept page around who decides.

  The page said a provider's word never counts, and listed "the one place this is relaxed" as "nowhere". A provider the operator marks as trusting now verifies an address exactly as a magic link does, so the page explains the two switches, why the second one is not decoration, and why the drivers that ship trusting are the two that really check. The provider guide gained a section on setting them, the driver guide gained the attribute a new driver should almost always leave alone, and the security guarantees, glossary, profile reference, claims contract and events schema all follow. @ericof 
- Rewrote the three README files. The root one gained an install-in-your-project section, a packages table naming each half's registry and license, and entry points into the published documentation; its Black badge went, since the repository formats with Ruff, and six links to `frontend/` were repaired. The `Products.membrane` comparison moved to the users-as-content concept page, where the zero-wake property it turns on is explained. @ericof 
- Said plainly what a user deletion leaves behind.

  Deleting a user removes the Profile and the Plone account, and deliberately keeps the identity records — that part was already documented, because it is what lets somebody sign back in under the same userid. What was not documented is that the audit entries stay too, and that both hold personal data against a userid nobody can resolve any more: a claims snapshot on the identity, a login history on the audit entries, with an IP address on a site that has switched that on.

  Local roles are revoked by Plone on deletion and are not restored by a later sign-in, so this is a data-retention question rather than an access one. A deployment with an erasure obligation should unlink the identities before deleting the user. @ericof 
- Stopped citing GitHub as the provider that withholds an address, now that the add-on reads one from `GET /user/emails`. The reasons a profile arrives incomplete are stated without it. @ericof 
- The security guarantees describe how a client's redirect URIs are matched.

  Matching was documented nowhere a reader could reach: the rule lived in a docstring and in a planning file that ships with nobody. The reference page now states it — exact comparison by default, the two positions a wildcard is allowed in, and every position it is refused in — alongside a plain statement of what registering one costs, since every name a wildcard covers is somewhere this server will send a browser carrying an authorization code. @ericof 
- Warned, in the how-to and the reference page, that the provider must be named exactly as `pas.plugins.authomatic` named it.

  Its provider name is the left half of every identity key in a dump, and this package's provider id is what a login presents as the right one. Nothing can check that they match, because the provider is configured by hand in the target site after the import has finished. Getting it wrong is not an error: the import reports success, and then every migrated person signs in and is handed a brand-new account beside the one waiting for them, while the migrated profile keeps their name and their groups and belongs to nobody who can sign in.

  The reference page also now states where each half of the join comes from, so an operator migrating from a provider other than Google can work out whether their subject survives the trip. @ericof 
- Wrote down how a release is cut.

  Both packages go out together with one command, `uvx repoplone release <segment>`, and nothing in the repository said so. The contributing guide now names it, lists what each half's release step does, and states the two things that bite if forgotten: you have to be authenticated to PyPI and to npm before you start, and the frontend must be published by `pnpm` rather than `npm`, because only `pnpm` rewrites the `workspace:` and `catalog:` peer dependencies into real ranges. `AGENTS.md` carries the same pointer with an instruction not to run it — publishing, tagging and a GitHub release are not things an agent should do on somebody's credentials. @ericof 



