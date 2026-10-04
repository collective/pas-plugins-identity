/**
 * The way to the sign-in methods, among a signed-in user's tools.
 *
 * Rendered in Aurora's `authenticatedTools` slot, beside its own log-out
 * link, which is where the Volto add-on puts the same entry in its user
 * menu.
 * @module slots/IdentityTools
 */
import { Link } from '@plone/components';
import { defineMessages, useIdentityUI } from '@plone-collective/identity-core';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import { IDENTITIES_PATH } from '../lib/paths';

const messages = defineMessages({
  title: { id: 'Sign-in methods', defaultMessage: 'Sign-in methods' },
});

/**
 * The link, translated the way the page it leads to is.
 *
 * @returns The link.
 */
function IdentitiesLink() {
  const { t } = useIdentityUI();
  return <Link href={IDENTITIES_PATH}>{t(messages.title)}</Link>;
}

export default function IdentityTools() {
  return (
    <AuroraIdentityUI>
      <IdentitiesLink />
    </AuroraIdentityUI>
  );
}
