Gave groups a way across the federation. A Plone site acting as an authorization server now releases a `groups` claim under the `profile` scope, carrying the groups PAS resolved for the principal, sorted, and never `AuthenticatedUsers`.

`groups` is not a registered OIDC claim, but it is the name Keycloak, Okta and Entra all use, so a relying party that is not a Plone site can read it. Riding on `profile` is a deliberate trade, and the claims reference states it: a display scope now carries authorization data. @ericof
