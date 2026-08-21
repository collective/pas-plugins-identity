/**
 * Working out what a user can still add.
 * @module helpers/identities
 */

import type { Identity, LoginProvider } from '../types';

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
