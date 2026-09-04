Email sign-in is a button on the login page rather than a form standing open under it.

The page offered three ways in and treated them inconsistently. A provider was a button; a password was a button that opened its form in place of the list; the magic link was a label and an input rendered inline below everything else. That made the email field the only always-visible input on a page whose question is "choose how you would like to sign in", and the one option that did not look like an option.

Email is now a `ProviderButton` beside the others, wearing the provider's own title and colours, and pressing it opens the email field on the next step — the same second-step behaviour the password button already had, including the way back to the options. The two ways in that ask for something typed sit together at the end of the list, since neither leaves this origin.

One disclosure state replaced the boolean, so opening either form closes the other; two open forms is not a state this page has. The email provider stays out of every branch that redirects, because it answers with a message rather than an authorize URL. A site whose only way in is the magic link still gets the form outright: one way in is not a choice. @ericof
