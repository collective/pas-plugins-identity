/**
 * Whether a user's fields live in a Profile content object.
 *
 * This asked `source === 'identity_profile'` first, and that was wrong: on a
 * real site it is never true. `source` is the PAS plugin the *account* came
 * from, and every account this package creates is a `source_users` one — the
 * `[content]` layer's plugin serves properties and enumeration, it does not
 * authenticate. So a user with a Profile at `/profiles/ericof` still reports
 * `"source": "source_users"`, and keying the menu on that hid the entry for
 * everybody.
 *
 * The question the menu actually needs is narrower than "does the site have
 * the layer" and wider than "which plugin authenticated": *is this person's
 * name, email and biography stored in a content object?* Having a Profile is
 * exactly that. The layer's PAS plugin sits above `mutable_properties`, so
 * wherever a Profile exists it is what answers for that user's fields — the
 * two conditions are one condition, and `profile_url` is how the payload
 * says it.
 *
 * The consequence for the menu is the one that was wanted: on a site without
 * the layer, or for a user first login has not minted a Profile for,
 * `profile_url` is null and Volto's own Profile entry keeps its slot,
 * leading to the member form where those users' fields really are.
 * @module helpers/profileSource
 */

/**
 * Whether this user's fields are held in a Profile.
 *
 * A value rather than the user it came from, so a caller can select it out
 * of the store on its own. `useSelector` compares what it returns by
 * identity: handed the whole user object it sees a change on every render
 * and re-renders forever.
 *
 * @param profileUrl The user's `profile_url`, when they have a Profile.
 * @returns Whether there is a Profile holding their fields, and therefore
 *   one to link to. A menu entry leading nowhere is worse than no entry.
 */
export function profileHoldsTheFields(
  profileUrl: string | null | undefined,
): boolean {
  return Boolean(profileUrl);
}
