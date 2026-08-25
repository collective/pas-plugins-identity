"""``GET @oauth-consent`` -- describe the request a user is being asked about.

The authorization endpoint decides everything: whether the client is known,
whether the redirect URI matches, whether the scopes are registered, and
whether this user has already agreed. When a frontend consent screen is
configured it redirects the browser there instead of rendering its own page,
and this is what that screen reads to find out *what it is asking about*.

Nothing here decides anything. It records no consent, issues no code and
changes nothing: the answer goes back to ``@@oauth-authorize``, which re-runs
every check before acting on it. A client disabled between the question and
the answer is refused on the way out as surely as on the way in, and that
stays true however the question was rendered.

What it does have to do is refuse to describe a request that is not worth
describing. A screen that renders "Allow *evil-app* to use your account?" for
a client this server never heard of is a phishing page hosted on the site's
own domain -- so an unknown client, a disabled one, or a redirect URI that
does not match is an error here exactly as it is there.
"""
