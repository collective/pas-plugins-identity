"""``@audit-log`` -- read the authentication event log.

``GET @audit-log``
    Your own entries.

``GET @audit-log?userid=<id>``
    Somebody else's. Managers only.

``GET @audit-log?scope=site``
    Everything, including the refusals that could not be attributed to
    anybody -- which is the view an operator investigating an attack wants.
    Managers only.

The default is deliberately the narrow one. A log that shows the whole site
to whoever asks is a list of who has accounts and when they signed in.
"""
