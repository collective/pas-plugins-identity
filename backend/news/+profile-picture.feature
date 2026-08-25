Gave the Profile a picture, and made it win over the member portrait.

The `[profile]` type had no image field at all, so there was no way to give a Profile a picture — the only portrait a user could have was the one synced from a provider into `portal_memberdata`, or one uploaded through user preferences. `picture` is a `NamedBlobImage` on the type now, editable like any other field on it.

Precedence is the Profile's, which is the decision recorded for this: a picture somebody chose and uploaded beats one a provider supplied, so `@users` reports the Profile's picture where there is one and the member portrait otherwise. Neither existing stays a real answer rather than a placeholder — the frontend draws the user's initials on a colour derived from their userid, and a portrait everybody shares would say "no image here" rather than "this is you".

`picture` is deliberately absent from the properties the PAS plugin serves: those come from catalog metadata, and a blob has no business in a brain. `core/portraits.py`'s docstring said the Profile having no image field was deliberate — that was true when it was written and is not any more, so it now documents the precedence instead. The FTI binds the Python schema, so the field appears on restart with no upgrade step. @ericof
