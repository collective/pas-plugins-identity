# Changelog

<!-- You should *NOT* be adding new change log entries to this file.
     You should create a file in the news directory instead.
     For helpful instructions, please see:
     https://6.docs.plone.org/contributing/index.html#contributing-change-log-label
-->

<!-- towncrier release notes start -->

## 1.0.0-alpha.3 (2026-09-07)

No significant changes.


## 1.0.0-alpha.2 (2026-09-07)


### Documentation

- Added the registry badges to the README.

  The package is on npm as of `1.0.0-alpha.1`. The README carries its version badge and, beside it, the version of the backend package it requires — the two are released together, and a reader on npm cannot otherwise see whether the halves they are about to install match. @ericof 

## 1.0.0-alpha.1 (2026-09-05)


### Breaking

- A client's scopes are edited as the list they are, and `OAuthClient.scope` is `string[]`. The two conversions the client form used to do existed only because the backend record was one line of space-separated text; the record is a list now, so the form binds to it directly and the listing renders the scopes comma-separated, the way the grants beside them already read. @ericof [#9](https://github.com/collective/pas-plugins-identity/issues/9)
- The provider form is composed from the backend's schema rather than built here.

  `providerSchema.ts` was 529 lines that turned a descriptor dict into Volto properties, with its own notion of field types, its own ordering, its own secret flag and its own untranslated English. All of that is the backend's answer now, serialized by `plone.restapi` from two interfaces and already translated into the site's language, so what is left here is composition: merge the provider's schema with the chosen driver's, prefix the driver's half so one flat form can carry a nested object, and add the two fields that exist only while a provider is being created.

  Nothing in the frontend decides what a field looks like any more. The colour fields ask for Volto's own `color_picker` and the icon asks for `provider_icon`, both named by the backend through `frontendOptions`. `DriverField` is gone from the types: nothing here describes a field.

  `ProviderIconWidget` is the one widget this add-on supplies. It sends and reads the same `filenameb64:…;datab64:…` envelope Plone stores `site_logo` in, but previews by inlining the document rather than through `/@@site-logo/<filename>` — Volto's own registry image widget builds that URL, and it answers 404 for a provider icon. Inlining is also exactly what the login button does with the same bytes, so what an operator sees is what a visitor gets.

  `fromFormData` no longer trims or corrects anything. Every rule about what a value may be lives on the backend schema, and cleaning up here would only hide which value a refusal is about. @ericof 


### Feature

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


### Bugfix

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


### Internal

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


### Documentation

- Replaced the frontend README's empty features comment with what the add-on registers: its routes, the two control panels, the profile and group views, the `provider_icon` widget, and why each of the three shadowed Volto components could not be extended instead. The Storybook badge pointed at a site that does not exist and now points at the published one, the install block names the `addons` array that actually registers the add-on, and the Volto 17 instructions went, since the package requires Volto 18. @ericof 
- Rewrote the README in plain Markdown, and corrected the Volto version.

  This file is the package's README on npm, which renders neither the centred `<div>` header the project was generated with nor GitHub's `> [!NOTE]` and `> [!IMPORTANT]` callouts — the first was dropped by the sanitizer and the second appeared with its marker showing. Both are ordinary Markdown now, and the file contains no HTML at all.

  It also claimed Volto 18 and above. The checkout pins 19.3.0, the peer dependencies are the Volto 19 stack, and the frontend install guide already said as much, so the README now says Volto 19 and links to that guide for the full requirement table. @ericof
