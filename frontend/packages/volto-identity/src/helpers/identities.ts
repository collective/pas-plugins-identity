/**
 * Working out what a user can still add, and how.
 * @module helpers/identities
 */

import type { Identity, LoginProvider } from '../types';

/**
 * The driver whose flow is a mailbox rather than a redirect.
 *
 * Lives here rather than in the component that first needed it, because two
 * screens now have to know: the login form renders it as an address field
 * instead of a button, and the identities page does the same. A second copy
 * of the string is how one of them ends up posting to an endpoint that
 * cannot answer -- which is exactly the 502 this constant exists to prevent.
 */
export const EMAIL_DRIVER = 'email';

/**
 * Return the providers a user has not linked yet.
 *
 * Offering a provider they already use would start a flow that ends in a
 * collision, which is a confusing way to learn you are already signed up.
 *
 * @param providers Every provider the site offers.
 * @param identities What the user already owns.
 * @returns The providers still worth offering.
 */
export function linkable(
  providers: LoginProvider[],
  identities: Identity[],
): LoginProvider[] {
  const linked = new Set(identities.map((identity) => identity.provider));
  return providers.filter((provider) => !linked.has(provider.id));
}

/**
 * Split what can be offered into the two ways of offering it.
 *
 * A redirect provider is a button: one click and the browser leaves. The
 * email provider needs an address typed first, because the thing being
 * proven is control of a mailbox and only the user knows which one.
 *
 * @param providers The providers still worth offering.
 * @returns The redirect providers, and the email provider if it is among
 *   them.
 */
export function splitLinkable(providers: LoginProvider[]): {
  redirect: LoginProvider[];
  email: LoginProvider | null;
} {
  return {
    redirect: providers.filter((provider) => provider.driver !== EMAIL_DRIVER),
    email:
      providers.find((provider) => provider.driver === EMAIL_DRIVER) ?? null,
  };
}
