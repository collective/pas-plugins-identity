"""Helpers with no policy in them and nothing registered.

What lives here is the mechanical half of the layer: normalise an address,
sanitize an SVG, resolve a dotted claim path, close a group graph. None of it
reads the registry, decides anything about a login, or is wired into ZCML --
which is the line, and the reason the modules that *do* stay one level up
beside the things that call them.

A caller reaching for something here should be able to read the one function
it needs without learning anything about the rest of the package.
"""
