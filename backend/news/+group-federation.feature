Gave groups a way across the federation.

A Plone site acting as an authorization server now releases a `groups` claim under the `profile` scope, carrying the groups PAS resolved for the principal, sorted, and never `AuthenticatedUsers`. `groups` is not a registered OIDC claim, but it is the name Keycloak, Okta and Entra all use, so a relying party that is not a Plone site can read it. Riding on `profile` is a deliberate trade, and the claims reference states it: a display scope now carries authorization data.

A relying party maps that claim to local groups per provider, not per driver — two realms behind the same driver are two different directories. Nothing is granted until an operator fills the map in, an unmapped name grants nothing and never creates a group, and a group missing from the site is skipped and logged.

Every login reconciles, so a membership revoked at the provider stops granting here without anyone editing the site. The reconciliation is fenced: each identity records what its own provider granted, so a login only ever takes back what that provider gave. A group granted by hand survives, and two providers cannot revoke each other's grants. @ericof
