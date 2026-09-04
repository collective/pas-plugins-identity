A user's account is a page in the control panel rather than an overlay on a row.

The Account action opened `UserAccountPanel` inside a modal, which is the wrong container for it. What it shows is a page's worth of read-only facts about one person — which providers they have configured, which addresses are theirs, what they have done lately — it is not a form with an outcome, and as an overlay it could not be linked to, bookmarked, opened in a new tab or reached with the back button. An administrator comparing two accounts had to close one to open the other.

It is now a route at `/controlpanel/users/<userid>/account`, and the row's action is a `Link` — the same argument already made in that row for why Edit is an anchor and not a click handler. Volto's own control-panel pattern already covers everything below `/controlpanel/`, so the route needs no entry of its own.

The page is split into tabs: how they sign in, which addresses are theirs, and what they have done lately. Three separate questions about one person, and an administrator opening the page has one of them in mind rather than all three. When they last signed in stays outside the tabs, because it is the fact the page is about rather than one of its sections.

Reading the userid back off the path needed care: react-router decodes a route parameter only halfway — a space comes back decoded, a slash does not — so handing it straight to an action that escapes what it is given asked the backend for a userid nobody has. @ericof
