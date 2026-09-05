---
myst:
  html_meta:
    "description": "The IDriver interface and the rules a driver must satisfy."
    "property=og:description": "The IDriver interface and the rules a driver must satisfy."
    "property=og:title": "Driver contract"
---

(reference-driver-contract)=

# Driver contract

What a driver must declare and satisfy.

To write one, follow {doc}`/how-to-guides/write-a-driver`. This page is the
checklist.

## The interface

<!-- source: backend/src/pas/plugins/identity/core/interfaces.py, IDriver -->

### Attributes

| Attribute | Purpose |
|---|---|
| `driver_id` | Unique id, such as `github`. Matches the utility name. |
| `title` | Shown in the control panel. |
| `settings_schema` | The schema the configuration form is generated from. |
| `default_scope` | Tuple of scopes requested when the provider names none. |
| `subject_keys` | Claim keys tried, in order, to find the subject. |
| `default_propertymap` | Claim path → Plone property, seeded into a new provider. |
| `default_group_claim` | The claim groups arrive in, or empty for a provider with none. |
| `default_groupmap` | Provider group → local group. Empty for every shipped driver. |
| `default_trust_email_verification` | Whether this provider's verification counts by default. |
| `supports_manual_link` | Whether an identity may be linked from the account page. |

Base class defaults (`core/drivers/base.py`): `settings_schema` is
`IOAuth2Settings`, `default_scope` is `()`, `subject_keys` is `('sub',)`,
`default_group_claim` is `''`, `default_trust_email_verification` is `False`.

### Methods

| Method | Contract |
|---|---|
| `normalize_claims(payload) -> Claims` | Turn the provider's payload into this package's claim names. |
| `subject(payload) -> str` | The stable identifier. Raises when no key in `subject_keys` is present. |

`BaseDriver` also provides `enrichment_endpoint`, `merge_enrichment`,
`reported_addresses` and `_email_verified` for drivers that need a second call to
the provider.

## The rules

Each is a rule a driver must satisfy, and what catches a violation.

| # | Rule | Enforced by |
|---|---|---|
| 1 | A field marked secret stays secret: masked on the way out of every API surface, omitted from GenericSetup export. Do not invent your own credential storage. | the serializers and the export tests |
| 2 | Every field has an `order`, and no two share one. | the driver contract test—a tie fails it rather than falling back to the alphabet |
| 3 | `default_scope` is a tuple, not a space-delimited string. | the contract test |
| 4 | `default_propertymap` names only member fields a stock site has, written against **normalized** claim names. | the contract test; `IUserDataSchema` guarantees only `fullname` and `email` |
| 5 | `default_group_claim` is set to the claim groups arrive in, or left empty when the provider has none. | the contract test |
| 6 | `default_groupmap` is empty unless the driver genuinely knows the far end's groups. | convention; every shipped driver is empty |
| 7 | `email_verified` is normalized to a boolean, and only `True` counts. | the contract test and `_email_verified` |
| 8 | `default_trust_email_verification` stays `False` unless the provider refuses to call an address verified until the account has answered mail at it. | review; only `google` and `github` set it |

### Why order is a number

A configuration schema travels as a JSON object, and `plone.restapi` serializes
those with sorted keys, so the order fields are declared in is gone by the time
the control panel builds a form. The number is what survives.

The inherited fields are spaced by ten, so a new field can be slotted between two
of them.

### Why only `True` counts

Several providers send the string `"true"`, and several send `1`. Everything that
reads the flag refuses anything that is not literally `True`, because a forged
unverified address that reads as truthy is an account takeover.

A provider that really does send a string is handled by the per-provider
`accept_string_booleans` switch, not by a driver being lenient.

See {doc}`/concepts/email-verification`.

### Why an empty group claim is not neutral

Leaving `default_group_claim` empty switches the feature off for that driver: no
`group_claim` field appears in the configuration form, and nobody is asked to map
the groups of a provider that has none.

A map stored against such a provider grants nothing rather than guessing at a
claim name.

Operators can override the claim with a dotted path, so a provider nesting groups
under `realm_access.roles` needs no driver of its own.

## Registration

A driver is a named utility providing `IDriver`, registered under its
`driver_id`. The control panel lists whatever is registered, and the form comes
from `settings_schema`, so a third-party driver needs no frontend change.

## Related

- {doc}`/how-to-guides/write-a-driver`—the procedure
- {doc}`shipped-drivers`—the five that ship, and their values
- {doc}`claims`—the claim names `normalize_claims` produces
- {doc}`events`—what a sign-in fires
- {doc}`stability`—the contract may change before 1.0.0
