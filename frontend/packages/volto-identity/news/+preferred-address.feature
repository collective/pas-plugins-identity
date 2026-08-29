The sign-in methods page can say which of your addresses stands for you.

A provider that knows several of your addresses puts all of them on your profile, so the question there is no longer which one to keep but which one this site should use. That is the *order* of the list -- the backend derives `email` from it, preferring the first verified address -- so **Make preferred** moves one to the front rather than setting a field. The whole list is sent with the `PATCH`, since sending one entry would replace the list with it.

Offered on every address but the one already chosen, and only when the page was given a handler for it: a button that does nothing when clicked reads as a broken page. A verified address still wins over an unverified one above it, which is why the **Preferred** badge says who won rather than what was last clicked. @ericof
