"""Building the URLs the server sends a browser back to."""

from urllib import parse


def redirect_with(redirect_uri: str, params: dict[str, str]) -> str:
    """Add response parameters to a client's redirect URI.

    RFC 6749, section 3.1.2: a redirection endpoint may carry a query of its
    own, which "MUST be retained when adding additional query parameters".
    The registered query is kept exactly as it was written, rather than
    parsed and re-encoded, because the client compares against what it
    registered.

    :param redirect_uri: The verified redirect URI.
    :param params: The parameters of the response.
    :returns: The URL to send the browser to.
    """
    parts = parse.urlsplit(redirect_uri)
    added = parse.urlencode(params)
    query = f"{parts.query}&{added}" if parts.query else added
    return parse.urlunsplit(parts._replace(query=query))
