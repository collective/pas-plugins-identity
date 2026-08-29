"""The content types a user and a group are.

Two Dexterity containers and their schemas, and nothing else: what a Profile
*does* -- how it is catalogued, reconciled, served as a property sheet --
lives with the machinery that does it, so that reading this package tells you
what a user is rather than everything that happens to one.

Both classes are declared in the FTI by dotted name and are stored under it in
the ZODB, so moving either one is a data migration rather than a refactor.
Their markers are applied in ``configure.zcml`` beside them, against the class
rather than through the FTI, so a test that instantiates one directly gets the
same subscribers a real object does.
"""
