/**
 * What the sign-in block says to somebody who is signed in.
 *
 * Pure, so the rules -- which placeholders exist, which sign-in is this one
 * and which the one before -- are tested without a store.
 * @module helpers/welcome
 */
import type { AccountIdentity, AuditEvent } from '../types';

/** The placeholders a welcome message may carry. */
export const WELCOME_PLACEHOLDERS = ['username', 'fullname'] as const;

/** A value for every placeholder. */
export type WelcomeValues = Record<
  (typeof WELCOME_PLACEHOLDERS)[number],
  string
>;

/** The audit event that means somebody got in. */
export const AUTHENTICATED = 'authenticated';

/**
 * How many audit events to ask `@user-account` for: the most it returns.
 *
 * The two sign-ins the block wants sit among every other kind of event --
 * links, verified addresses, refreshed claims -- so the default of ten can
 * leave them out.
 */
export const SIGN_IN_EVENTS = 100;

/**
 * Replace the placeholders in a welcome message.
 *
 * The result is text, and is rendered as text: a message is not a template
 * language, and nothing in it is markup. A name in braces that is not a
 * placeholder is left as it was, so a typo shows on the page rather than
 * vanishing from it.
 *
 * @param template The message, as the editor typed it.
 * @param values A value for every placeholder.
 * @returns The message with the placeholders filled in.
 */
export function fillPlaceholders(
  template: string,
  values: WelcomeValues,
): string {
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    Object.prototype.hasOwnProperty.call(values, name)
      ? values[name as keyof WelcomeValues]
      : match,
  );
}

/**
 * Pick this sign-in and the one before it out of a user's audit events.
 *
 * Only successful `authenticated` events count. A password sign-in records
 * none -- only a federated sign-in or a magic link does -- so for a session
 * that began with a password, `current` is whatever sign-in came before it.
 *
 * @param events The user's events, newest first, as `@user-account` sends them.
 * @returns The newest sign-in and the one before it, each `null` when the log
 *   holds none. The log is bounded, so `null` does not mean never.
 */
export function recentSignIns(events: AuditEvent[]): {
  current: AuditEvent | null;
  previous: AuditEvent | null;
} {
  const signIns = events.filter(
    (event) => event.event === AUTHENTICATED && event.success,
  );
  return { current: signIns[0] ?? null, previous: signIns[1] ?? null };
}

/**
 * Name the provider an event came from.
 *
 * @param provider The provider id an audit event carries.
 * @param identities The user's linked identities, which carry each provider's
 *   title.
 * @returns The provider's title, or its id when no identity names it.
 */
export function providerTitle(
  provider: string,
  identities: AccountIdentity[],
): string {
  return (
    identities.find((identity) => identity.provider === provider)?.title ||
    provider
  );
}
