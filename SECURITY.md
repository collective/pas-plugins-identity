# Security policy

## Supported versions

This package is pre-release. Until 1.0.0, only the latest release is
supported.

## Reporting a vulnerability

Please report security issues **privately**, not in the public issue tracker.

<!-- TODO: replace with the project's real reporting address before the first
     public release. -->

Contact: `security@example.org`

Please include:

- what the issue is and what an attacker can do with it;
- the version or commit you found it in;
- steps to reproduce, if you have them.

You will get an acknowledgement within a few working days, and we will keep
you informed while we work on a fix.

## Scope

In scope: anything that lets somebody authenticate as a user they are not,
attach an identity to an account that is not theirs, read a client secret or a
token, or read another user's audit log.

Worth reporting even though they are documented: the provider-avatar fetch
(off by default — see the documentation for why) and anything that defeats the
guards around it.

Out of scope: a Plone site configured to trust a hostile identity provider.
Choosing your provider is a trust decision this package cannot make for you.

## What we guarantee

The security properties this package enforces, each with a test, are listed in
the documentation under *Security*.
