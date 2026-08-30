/**
 * Shapes the backend actually returns.
 * @module types
 */

/**
 * How a provider's button should look.
 *
 * Served on the public listing, so it carries presentation and nothing else:
 * an icon, and the two colours the button is drawn in. Every field may be
 * empty, and empty means "use the frontend's own styling" rather than a
 * placeholder every provider shares.
 */
export interface ProviderStyle {
  /**
   * SVG source, sanitized by the backend on the way in.
   *
   * Rendered inline rather than as an `<img>`, which is what lets it inherit
   * the button's colour. The backend keeps an allowlist of elements and
   * attributes and refuses anything that references a URL, which is what
   * makes inlining it safe -- see `core/svg.py`.
   */
  icon?: string;
  background_color?: string;
  foreground_color?: string;
}

/** One provider offered on the login page, from `@login-providers`. */
export interface LoginProvider extends ProviderStyle {
  '@id': string;
  id: string;
  title: string;
  driver: string;
  /**
   * Whether a user may start a link against this from a form.
   *
   * False for magic link: the address it would prove is whatever was typed,
   * and the addresses this site verifies are the ones already on a person's
   * profile. The backend leaves such providers out of `available` as well;
   * this is here so a client can explain the absence rather than only
   * observe it.
   */
  supports_manual_link?: boolean;
}

/** Answer from `@login-providers/<id>`: where to send the browser. */
export interface AuthorizeRedirect {
  provider: string;
  authorize_url: string;
}

/** Answer from `@identity-callback` and `@magic-link-confirm`. */
export interface TokenResponse {
  token: string;
  came_from?: string;
}

/**
 * Answer from `POST @identities` for a provider with no authorize URL.
 *
 * The email provider's "provider" is a mailbox, so there is nowhere to send
 * the browser: the flow continues when the link in the message is clicked.
 */
export interface EmailLinkSent {
  provider: string;
  sent: true;
}

/** Either shape `POST @identities` answers with. */
export type LinkStarted = AuthorizeRedirect | EmailLinkSent;

/** Answer from `@magic-link-confirm` when the token was minted for linking. */
export interface IdentityLinked {
  linked: {
    provider: string;
    subject: string;
  };
}

/** Everything `@magic-link-confirm` can answer with. */
export type ConfirmResponse = TokenResponse | IdentityLinked;

/** Reducer state shared by every request this add-on makes. */
export interface RequestState {
  loading: boolean;
  loaded: boolean;
  error: unknown | null;
}

/** One identity the signed-in user owns, from `@identities`. */
export interface Identity {
  '@id': string;
  provider: string;
  subject: string;
  title: string;
  created: string;
  last_login: string | null;
  /** False when this is the user's last way in. */
  can_unlink: boolean;
}

/** A driver and the form it needs, from `@identity-drivers`. */
/**
 * A JSON schema as `plone.restapi` serializes an interface.
 *
 * The shape every Plone form is built from, and the reason this add-on no
 * longer describes fields of its own.
 */
export interface JsonSchema {
  properties?: Record<string, Record<string, unknown>>;
  required?: string[];
  fieldsets?: { id: string; title: string; fields: string[] }[];
}

/**
 * A composed form schema, as Volto's `Form` consumes one.
 *
 * The same three keys as `JsonSchema` and none of them optional, which is the
 * whole difference: a `JsonSchema` is what arrived over the wire and may be
 * missing anything, while this is what a helper in this package built out of
 * one, and `Form` renders nothing at all when handed a schema without
 * `properties`.
 */
export interface VoltoSchema {
  properties: Record<string, Record<string, unknown>>;
  required: string[];
  fieldsets: { id: string; title: string; fields: string[] }[];
}

export interface Driver {
  id: string;
  title: string;
  /**
   * The driver's settings, as an ordinary JSON schema.
   *
   * Serialized by `plone.restapi` from the driver's `settings_schema`, so it
   * carries `properties`, `required`, `fieldsets` and widget hints, already
   * translated. The frontend composes it into the provider form and has no
   * opinion about what is in it.
   */
  schema: JsonSchema;
  /**
   * Claim path to user field, seeded into a new provider's mapping.
   *
   * A starting point rather than a rule: it is written into the form like
   * anything typed there, and an operator edits or empties it before saving.
   */
  default_propertymap?: Record<string, string>;
  /**
   * Provider group name to local group id, seeded into a new provider's map.
   *
   * Almost always empty, and honestly so: group names are a fact about one
   * deployment's directory, not about a driver.
   */
  default_groupmap?: Record<string, string>;
}

/** A configured provider as the control panel sees it. */
export interface ConfiguredProvider extends ProviderStyle {
  '@id': string;
  id: string;
  driver: string;
  title: string;
  /** Whether the provider may be used at all -- to sign in, and to link. */
  enabled: boolean;
  /**
   * Whether the login screen offers a button for it.
   *
   * A separate question from `enabled`. An enabled provider that is not
   * shown stays linkable from a user's own sign-in methods and still signs
   * in an account already linked to it, which is what a staff-only provider
   * looks like.
   */
  show_in_login: boolean;
  config: Record<string, unknown>;
  /** Claim path to Plone user field, applied on every login. */
  propertymap: Record<string, string>;
  /**
   * Provider group name to local group id, applied on every login.
   *
   * Empty grants nothing. Only groups this provider granted are ever taken
   * back, so a group granted locally survives every sign-in.
   */
  groupmap: Record<string, string>;
}

/** Answer from the per-provider connection check. */
export interface ConnectionCheck {
  ok: boolean;
  error?: string;
  authorization_endpoint?: string;
  token_endpoint?: string;
  has_jwks?: boolean;
}

/** Answer from `@my-profile`: where the caller's Profile is, and how far along. */
export interface MyProfile {
  '@id': string;
  userid: string;
  /** Absolute URL of the Profile, or null when the user has none. */
  profile: string | null;
  /** Workflow state, or null when the user has no Profile. */
  review_state: string | null;
  /**
   * Required fields the Profile has no value for.
   *
   * Why `review_state` is `incomplete`, and what the gate tells the user it
   * wants. Empty for a complete Profile and for a user without one.
   */
  missing: string[];
  /**
   * The addresses the Profile carries, and which of them are verified.
   *
   * Optional because a client may be talking to a backend that predates it,
   * and every consumer therefore has to tolerate its absence -- an empty
   * list and a missing key mean the same thing here.
   */
  emails?: ProfileEmail[];
}

/**
 * One address on a Profile.
 *
 * `verified` means this site holds the address as proved: either the person
 * followed a magic link sent here, or a provider the operator marked as
 * trusted vouched for it. A provider nobody marked still counts for nothing.
 * `preferred` marks the one the Profile's `email` resolves to, so a page can
 * show it without reimplementing the rule that picks it -- the first verified
 * address, or the first address at all.
 */
export interface ProfileEmail {
  address: string;
  verified: boolean;
  preferred: boolean;
}

/**
 * A user as `@users/<userid>` describes them once this add-on is installed.
 *
 * Only the fields this package adds or reads are named; the endpoint carries
 * the whole of Plone's own user representation alongside them.
 */
export interface UserProfile {
  '@id': string;
  id: string;
  /** The name this user signs in with; not the same as the userid. */
  username?: string | null;
  fullname?: string;
  email?: string;
  /** Portrait URL, when the user has uploaded one. */
  portrait?: string | null;
  /** The PAS plugin the userid came from, as PAS itself resolved it. */
  source: string | null;
  /** External identities linked to this account. */
  identities: Identity[];
  /** The user's Profile, when they have one. */
  profile_url: string | null;
}

/** One member of a group, from `@group-members/<id>`. */
export interface GroupMember {
  '@id': string;
  id: string;
  fullname: string;
  login: string;
  profile_url: string | null;
  /**
   * The groups this person is actually in.
   *
   * Which is how a listing can account for somebody being on it: a member of
   * an inner group appears in the outer group's list, and this says through
   * which.
   */
  through: string[];
}

/** A group named in a nesting, with enough to render a link. */
export interface NestedGroup {
  '@id': string;
  id: string;
  title: string;
}

/** What `@group-members/<id>` answers with. */
export interface GroupMembers {
  '@id': string;
  group: string;
  items_total: number;
  items: GroupMember[];
  /** Groups nested inside this one, at any depth. */
  nested_groups: NestedGroup[];
  /** Groups this one is nested inside, as stored rather than as closed. */
  parent_groups: NestedGroup[];
  batching?: Record<string, string>;
}

/** One identity as an administrator sees it, from `@user-account/<id>`. */
export interface AccountIdentity extends ProviderStyle {
  provider: string;
  title: string;
  subject: string;
  created: string;
  last_login: string | null;
  /** Whether the provider still exists in this site's configuration. */
  provider_configured: boolean;
  /** Whether it is enabled. An identity against a disabled provider cannot
   * sign anybody in, and looks like a broken login rather than a setting. */
  provider_enabled: boolean;
  /** Groups this provider granted at the last sign-in. */
  groups: string[];
}

/** One recorded authentication event. */
export interface AuditEvent {
  event: string;
  provider: string;
  success: boolean;
  timestamp: string;
  detail: Record<string, unknown>;
}

/**
 * How one account gets in, and when it last did.
 *
 * `@users/<id>` carries identities as bare ids; this names and styles them,
 * says whether each provider is still usable, and adds the two things Plone
 * records nowhere: when the person last authenticated, and by what route.
 */
export interface UserAccount {
  '@id': string;
  userid: string;
  fullname: string;
  profile_url: string | null;
  identities: AccountIdentity[];
  emails: ProfileEmail[];
  /**
   * ISO 8601, or null.
   *
   * Null is not "never signed in": the audit log is bounded, so an account
   * dormant longer than the retention period has had its entries purged.
   */
  last_authenticated: string | null;
  events_total: number;
  events: AuditEvent[];
}

/** One registered OAuth client: who may log in *to* this site. */
export interface OAuthClient {
  '@id': string;
  client_id: string;
  title: string;
  redirect_uris: string[];
  grant_types: string[];
  scope: string;
  auth_method: string;
  public: boolean;
  enabled: boolean;
  service_user: string;
  /**
   * The plaintext secret. Present only in the response that minted it, at
   * registration or rotation, and never readable again: the server stores a
   * hash. Anything holding this has to show it to the operator at once.
   */
  secret?: string;
  /** The server's own words about that, shown alongside the secret. */
  notice?: string;
}

/**
 * A pending authorization request, as `@oauth-consent` describes it.
 *
 * Nothing here is a decision. The answer goes back to `authorize_url` with
 * `params` and the `authenticator`, and the authorization endpoint re-runs
 * every check before acting on it.
 */
export interface ConsentRequest {
  '@id': string;
  /** The application asking. */
  client: { id: string; title: string };
  /** Who would be agreeing, so a forgotten session is visible. */
  user: { id: string; label: string };
  /** What is being asked for, in the order the client asked. */
  scopes: { id: string; claims: string[] }[];
  /** Where the answer goes. */
  authorize_url: string;
  /** The authorization request, to hand back unchanged. */
  params: Record<string, string>;
  /** plone.protect's token, bound to this user. */
  authenticator: string;
}

/**
 * One application a user has authorized, as `@oauth-grants` lists them.
 *
 * The mirror image of an `Identity`: that is a provider they sign in *with*,
 * this is an application they signed in *to*.
 */
export interface OAuthGrant {
  '@id': string;
  client_id: string;
  /** What the consent screen called it; the id when nothing else is left. */
  title: string;
  /** Whether the client is still registered on this site. */
  registered: boolean;
  enabled: boolean;
  /** ISO 8601, when the agreement was last given. */
  granted_at: string;
  /** What was agreed to, and what each scope releases. */
  scopes: { id: string; claims: string[] }[];
}

/** What `@oauth-grants` answers with. */
export interface OAuthGrants {
  '@id': string;
  items: OAuthGrant[];
  /**
   * Seconds an access token already minted may still be accepted.
   *
   * Withdrawing consent cannot reach one: they are self-encoded with no
   * denylist. The screen says so rather than implying a cutoff.
   */
  access_token_ttl: number;
}

/** One key in the signing ring. Metadata only; never key material. */
export interface SigningKey {
  kid: string;
  /** Whether this is the key currently signing. */
  active: boolean;
}

/** The signing ring, as the admin API describes it. */
export interface SigningKeyRing {
  '@id': string;
  algorithm: string;
  /** How many keys the ring holds before the oldest is dropped. */
  ring_size: number;
  jwks_uri: string;
  items_total: number;
  items: SigningKey[];
}
