/**
 * Whether a user's fields live in a Profile content object.
 *
 * This asked `source === 'identity_profile'` first, and that was wrong.
 * `source` names whichever PAS plugin *enumerated* the account, and which one
 * that is depends on how the account was made: a user added with a password
 * has a `source_users` row and reports that, while an externally
 * authenticated one has only a Profile and reports `identity_profile`. Both
 * of them have their fields in a Profile, so keying the menu on `source` hid
 * the entry for whole classes of user.
 *
 * The question the menu actually needs is narrower: *is this person's name,
 * email and biography stored in a content object?* Having a Profile is
 * exactly that. The profile PAS plugin sits above `mutable_properties`, so
 * wherever a Profile exists it is what answers for that user's fields — and
 * `profile_url` is how the payload says so.
 *
 * The consequence for the menu is the one that was wanted: for a user first
 * login has not minted a Profile for, or an account that predates the add-on,
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
