---
myst:
  html_meta:
    "description": "Learning-oriented walkthroughs for pas.plugins.identity."
    "property=og:description": "Learning-oriented walkthroughs for pas.plugins.identity."
    "property=og:title": "Tutorials"
    "keywords": "Plone, pas.plugins.identity, tutorials, federation"
---

# Tutorials

A tutorial is an experience that takes place under the guidance of a tutor.
A tutorial is always learning-oriented.

Work through one from start to finish and you end up with something running.
You also end up understanding a part of the package that no amount of reading explains as well.

Do {doc}`federation-demo` first. It is the only tutorial today, and it is also
the fastest way to see every part of this package working at once: two sites, a
consent screen, a group crossing between them, and a magic link—in Docker, with
nothing to register anywhere.

You do not need a provider account, an organization, or a tenant to run it.

```{toctree}
:maxdepth: 1

federation-demo
```

Afterwards, {doc}`/concepts/mental-model` names everything you just watched
happen, and {doc}`/how-to-guides/install` starts a real setup.
