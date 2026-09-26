"""The upgrade steps, and that a site can actually reach them.

An upgrade step is three things that have to agree: a profile version a site
can be behind, ZCML that GenericSetup has read, and a handler or an import
step that does the work. Any one of them alone is silent -- a step whose
package is never included does not appear in the control panel and does not
run, and nothing reports its absence -- so these assert the registration and
the effect separately: ``test_registration`` for every version at once, and a
module per version for what its step does.
"""

#: The profile every version here belongs to.
PROFILE = "pas.plugins.identity:default"
