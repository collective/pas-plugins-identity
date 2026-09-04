Waits and refusals are drawn over the login card instead of replacing what they are about.

Both used to displace the page. A wait swapped the options for a line of unstyled text, so the card changed size and the reader lost their place; a refusal appeared as a paragraph that pushed everything below it down, moving the button somebody was about to press. Neither is a different page — they are something happening to the page already there.

`LoginOverlay` draws both, and the difference between them is who ends them. A wait carries a spinner and no control, because it is not the reader's to end. A refusal carries no spinner — nothing is happening, which is the whole message — and a filled button that dismisses it, because leaving it up hides the form somebody needs to try again in. What is dismissed is the *refusal that was read*, not refusals in general, so a second wrong password says so again rather than being swallowed by the first one's dismissal.

The picker keeps its buttons while a redirect is in flight and says where it is going, naming the provider that was pressed — which the single-provider page always did and the multi-provider one did not. Greying the buttons says they cannot be pressed; it does not say why.

The card's body no longer changes height between states, and centres what it holds, so a short one is not left against the top of a box more than twice its height. `MagicLinkForm` was rewritten to wear the same markup and classes as the password form, which are Volto's own: a bare label and input beside a fully dressed form, on the same card, one click apart, was the "fields look strange" of it. @ericof
