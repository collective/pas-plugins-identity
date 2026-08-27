Added the required-information gate. While a profile is `incomplete`, every page its owner asks for is answered with a redirect to the profile's edit form, so a provider that withheld an email address cannot leave a site with an account it knows nothing about.

Switched on by `pas.plugins.identity.enforce_required_profile_fields`, which ships on. Turning it off makes an incomplete profile a suggestion rather than a gate.

A gate like this can lock a site out — a required field nobody can supply would leave every user in a loop, with the settings that would undo it on the far side. Two things stop that, and both are in the code rather than in the documentation. Managers and site administrators are never held, because somebody has to be able to reach the control panel. The profile itself is never held, because redirecting the target of the redirect is a loop no configuration escapes.

Three other things pass through, for reasons about the request rather than the user: anything `plone.restapi` answers, because Volto fetches the edit form over the API and gating those would break the page the user is being sent to; anything that is not a browser asking for a page, because a gate on every request is a gate on every stylesheet; and signing out, because a user who would rather leave than fill the form in may. @ericof
