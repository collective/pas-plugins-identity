"""The authorization server's HTTP endpoints.

Browser views rather than plone.restapi services throughout. The rest of this
package answers JSON to Volto, which speaks restapi; these endpoints answer
redirects and form posts to third-party OAuth clients, which do not.
"""
