/**
 * What Aurora lends `identity-core`'s components.
 *
 * Its translations, through i18next, and its router, so a link does not
 * reload the application. The icons stay core's own until Aurora's are
 * chosen for them.
 * @module components/IdentityUI/AuroraIdentityUI
 */
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router';
import { IdentityUIProvider } from '@plone-collective/identity-core';
import type { IdentityLinkProps } from '@plone-collective/identity-core';

import { translateWith } from '../../lib/i18n';

/**
 * Link through Aurora's router.
 *
 * @param props The link.
 * @returns The router link.
 */
const AuroraLink = ({ href, className, children }: IdentityLinkProps) => (
  <RouterLink to={href} className={className}>
    {children}
  </RouterLink>
);

/**
 * Lend the components inside Aurora's translations and router.
 *
 * @param props The components to lend them to.
 * @returns The provider.
 */
export default function AuroraIdentityUI({
  children,
}: {
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <IdentityUIProvider t={translateWith(t)} Link={AuroraLink}>
      {children}
    </IdentityUIProvider>
  );
}
