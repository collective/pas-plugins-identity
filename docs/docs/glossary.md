---
myst:
  html_meta:
    "description": "Terms and definitions used throughout the pas.plugins.identity documentation."
    "property=og:description": "Terms and definitions used throughout the pas.plugins.identity documentation."
    "property=og:title": "Glossary"
    "keywords": "Plone, pas.plugins.identity, glossary, term, definition"
---

(glossary-label)=

# Glossary

```{glossary}
:sorted: true

audit log
    The record of every authentication event this package fires, and of the refusals that fire no event.
    It is an authentication event log, not a session ledger.

claim
    A statement a provider makes about a person, such as their name or email address.
    Drivers normalize the claims a provider sends into a fixed schema before anything else reads them.

client
    An application registered against a Plone site running the `[server]` layer, so that the application can sign its users in against that site.
    A client is identified by a `client_id` and authenticates with a secret this site stores only as a hash.

driver
    Static metadata describing what a kind of provider needs, plus a function turning that provider's answer into normalized claims.
    A driver holds no state and makes no decisions about accounts.
    Drivers are registered as named ZCA utilities, and the utility name is the driver id.

external identity
    The pair of a provider and that provider's own identifier for a person.
    One Plone user id may have many external identities.

issuer
    The URL that identifies an authorization server.
    A relying party compares the `issuer` field inside a discovery document to the URL it fetched the document from, byte for byte, and refuses the document if they differ.

magic link
    Sign-in by an emailed, signed, single-use token, provided by the `email` driver.
    It needs no external provider, and it is the verification this package performs itself.

Plone
    [Plone](https://plone.org/) is an open source content management system used to create, edit, and manage digital content, such as websites, intranets, and custom solutions.

Plone Sphinx Theme
plone-sphinx-theme
    [Plone Sphinx Theme](https://plone-sphinx-theme.readthedocs.io/) is a Sphinx theme for [Plone 6 Documentation](https://6.docs.plone.org/), [Plone Conference Training](https://training.plone.org/), and documentation of various Plone packages.

nested group
    A group that is a member of another group.
    Membership is stored on the member, so nesting is the same field on the same side, and everybody in the inner group is in the outer one.

preferred address
    The address a Profile's `email` resolves to: the first verified one in its `emails` list, or the first one at all when none is verified.

Profile
    A content object carrying one user's PAS property sheet.
    Its values are served from catalog metadata, so answering a property lookup never wakes the object.

provider
    A configured instance of a driver, holding this site's credentials for one particular service.
    Two GitHub organizations are two providers sharing one driver.

relying party
    An application that sends its users to an authorization server to sign in, and relies on what that server says about them.

subject
    A provider's own identifier for a person, sent as the `sub` claim in OpenID Connect.
    A subject is meaningful only within the provider that issued it.

verified address
    An address this site holds as proved, recorded as an `email` external identity owned by that user id.
    Either a magic link proved it, or a provider the operator marked as trusting vouched for it.
    A provider nobody marked does not make an address verified here, whatever it asserts.

Markedly Structured Text
MyST
    [Markedly Structured Text (MyST)](https://myst-parser.readthedocs.io/en/latest/) is a rich and extensible flavor of Markdown.
    This documentation is written in MyST.

Sphinx
    [Sphinx](https://www.sphinx-doc.org/en/master/) is a documentation generator that builds this documentation into HTML.

userid
    The canonical Plone identifier for a person.
    On accounts this package creates it is a random `uuid4` hex string, minted once and never rewritten.
```
