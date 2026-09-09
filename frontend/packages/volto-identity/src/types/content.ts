/**
 * The two content types this package ships, as Volto receives them.
 *
 * `types/api.ts` describes endpoint payloads. This file describes *content*:
 * what `GET /identity-profiles/alice` answers with, which is what a view is
 * handed and what the edit form round-trips.
 *
 * ## Why these are built with `Pick` rather than `extends Content`
 *
 * `@plone/types` declares `Content` for a type carrying Plone's usual
 * behaviors. Neither of these does. `UserProfile.xml` says so plainly --
 * *"Dublin Core behaviors would add metadata nobody serves, and every behavior
 * field is a field the churn test has to keep consistent"* -- and the FTI lists
 * four behaviors, none of them `plone.dublincore` or `volto.blocks`.
 *
 * So most of `Content` is absent from the payload, and a type that inherited
 * it would promise fields no view can read. Measured against a real
 * serialization rather than assumed, the following are **not** there:
 *
 * `blocks`, `blocks_layout`, `contributors`, `creators`, `effective`,
 * `exclude_from_nav`, `expires`, `language`, `preview_caption`,
 * `preview_image`, `relatedItems`, `rights`, `subjects`,
 * `table_of_contents`.
 *
 * `Pick` keeps the shared keys tied to `@plone/types`, so a change there is a
 * type error here rather than silent drift, while claiming nothing about the
 * fields these types do not have.
 *
 * ## The deviations worth naming
 *
 * `title`
 *     A Profile has no `title` **field** -- only a computed `Title()`, which
 *     `plone.restapi` does not serialize -- so it is absent from a Profile and
 *     required in `Content`. A Group declares `title` on its own schema and
 *     does have it. This is why `ProfileUserContent` omits it and
 *     `GroupContent` keeps it.
 *
 * `version`
 *     `Content` types it `number | null`. The real payload carries the string
 *     `'current'`.
 *
 * `subjects`
 *     `Content` declares the empty tuple `[]`, which no payload satisfies.
 *     Not picked here, because neither type has the field at all.
 *
 * `group_ids`
 *     Serialized as vocabulary terms, not as the plain strings the schema
 *     stores.
 */

import type { Content } from '@plone/types';

/**
 * The keys both of this package's types share with an ordinary Plone object.
 *
 * `version` is left out and restated below: the payload carries a string.
 */
type SharedContent = Pick<
  Content,
  | '@components'
  | '@id'
  | '@type'
  | 'UID'
  | 'allow_discussion'
  | 'description'
  | 'id'
  | 'is_folderish'
  | 'items'
  | 'items_total'
  | 'layout'
  | 'lock'
  | 'modified'
  | 'next_item'
  | 'parent'
  | 'previous_item'
  | 'review_state'
  | 'type_title'
  | 'versioning_enabled'
  | 'working_copy'
  | 'working_copy_of'
>;

/** What the payload actually carries where `Content` promises a number. */
interface ContentBase extends SharedContent {
  /** ISO 8601. */
  created: string;
  /** The working-copy label, such as `'current'`. Not a revision number. */
  version: string;
  /** Present because the type is versioned; empty unless somebody typed one. */
  changeNote?: string;
}

/**
 * One term of a vocabulary-backed field, as `plone.restapi` serializes it.
 *
 * `group_ids` is stored as a tuple of ids and comes back as terms, so a view
 * reading `.token` and a form writing plain strings are both correct and are
 * not the same shape.
 */
export interface VocabularyTerm {
  token: string;
  title: string;
}

/** A `NamedBlobImage` field, with the scales Plone generates for it. */
export interface ContentImage {
  download?: string;
  scales?: Record<string, { download?: string }>;
  filename?: string;
  'content-type'?: string;
  size?: number;
  width?: number;
  height?: number;
}

/**
 * A `UserProfile`, as Volto receives it.
 *
 * Named for the content type; `types/api.ts` has a `UserProfile` of its own
 * describing what `@users/<userid>` answers, which is a different payload
 * about the same person.
 *
 * Several fields are permission-gated rather than optional by nature.
 * `emails` and `email` carry `...content.viewpii`, and `home_page`,
 * `location` and `image` carry `...content.view`, so a caller without the
 * permission receives an object with the key absent. That is why they are
 * declared optional even though the schema always has them.
 */
export interface ProfileUserContent extends ContentBase {
  '@type': 'UserProfile';
  /** The name this person signs in with. Not the userid; the id is that. */
  login: string;
  fullname?: string;
  /** Derived from `emails`, read-only, and gated on `viewpii`. */
  email?: string;
  /** Every address on the profile, in the owner's order. Gated on `viewpii`. */
  emails?: string[];
  home_page?: string;
  location?: string;
  /** The picture the person uploaded. `null` when they have not. */
  image?: ContentImage | null;
  /** The groups this person is in, as vocabulary terms. */
  group_ids?: VocabularyTerm[];
}

/**
 * A `UserGroup`, as Volto receives it.
 *
 * Unlike a Profile this one does have `title`: the group's name is a field on
 * its own schema rather than something computed.
 */
export interface GroupContent extends ContentBase {
  '@type': 'UserGroup';
  title: string;
  /** The groups this group is nested inside, as vocabulary terms. */
  group_ids?: VocabularyTerm[];
}

/** Either of the two types this package files principals as. */
export type IdentityContent = ProfileUserContent | GroupContent;
