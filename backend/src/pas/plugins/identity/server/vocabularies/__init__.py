"""Vocabularies the authorization server publishes.

Unlike :mod:`pas.plugins.identity.core.vocabularies`, nothing here is
protected. ``plone.restapi`` serves a vocabulary anonymously unless it is
named in :data:`plone.app.content.browser.vocabulary.PERMISSIONS`, and the
core ones had to be, because they describe the shape of the site's user
records. The scopes are the opposite: the same list is published to the whole
internet in the discovery document, which is the point of a discovery
document.
"""
