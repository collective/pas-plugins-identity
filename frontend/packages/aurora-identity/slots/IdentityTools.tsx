/**
 * The ways to a signed-in user's own pages, among their tools.
 *
 * Rendered in Aurora's `authenticatedTools` slot, beside its own log-out
 * link, which is where the Volto add-on puts the same entries in its user
 * menu: the sign-in methods, and the applications the user has authorized --
 * that one only where the authorization server is installed, since nowhere
 * else has it anything to list.
 * @module slots/IdentityTools
 */
import { useRouteLoaderData } from 'react-router';
import { Link } from '@plone/components';
import {
  applicationsMessages,
  defineMessages,
  useIdentityUI,
} from '@plone-collective/identity-core';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import {
  APPLICATIONS_KEY,
  APPLICATIONS_PATH,
  IDENTITIES_PATH,
} from '../lib/paths';

const messages = defineMessages({
  title: { id: 'Sign-in methods', defaultMessage: 'Sign-in methods' },
});

/**
 * The links, translated the way the pages they lead to are.
 *
 * @returns The links.
 */
function Links() {
  const { t } = useIdentityUI();
  const root = useRouteLoaderData('root') as
    Record<string, unknown> | undefined;
  return (
    <>
      <Link href={IDENTITIES_PATH}>{t(messages.title)}</Link>
      {root?.[APPLICATIONS_KEY] ? (
        <Link href={APPLICATIONS_PATH}>{t(applicationsMessages.title)}</Link>
      ) : null}
    </>
  );
}

export default function IdentityTools() {
  return (
    <AuroraIdentityUI>
      <Links />
    </AuroraIdentityUI>
  );
}
