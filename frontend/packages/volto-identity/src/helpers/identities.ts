/**
 * Working out what a user can still add, and how.
 * @module helpers/identities
 */

/**
 * The driver whose flow is a mailbox rather than a redirect.
 *
 * The login form renders it as an address field instead of a button, because
 * the thing being proven is control of a mailbox and only the person signing
 * in knows which one.
 *
 * It is *not* offered on the sign-in-methods page. The address a magic link
 * proves is whatever was typed, so a free-text box there verifies any mailbox
 * at all -- and a verified address is what a provider account can be
 * auto-attached to. The addresses this site will verify are the ones already
 * on your profile, and that page offers those instead. The backend enforces
 * the same rule in two places, so this constant is a label rather than a
 * gate: `@identities` leaves the provider out of `available`, and
 * `POST @identities` refuses an address that is not yours.
 */
export const EMAIL_DRIVER = 'email';
