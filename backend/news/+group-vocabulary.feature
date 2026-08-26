Added a `pas.plugins.identity.Groups` vocabulary, and a Profile's `Groups` field now chooses from it instead of taking free text.

The field stores group ids, and nothing checked that one named a group. The groups plugin filters an unknown id out rather than failing, so a typo produced a membership that granted nothing and said nothing — the worst shape a mistake about who is in which group can take. Every group PAS knows is offered, not only the ones that are content, because membership names an id without caring which plugin answers for it; `AuthenticatedUsers` is left out, since nobody is explicitly a member of it.

A Profile that already names a group which has since been deleted stays readable: the vocabulary constrains what may be written, and the doctor goes on reporting the stale id as `unknown-group`. @ericof
