/**
 * What Aurora lends `identity-core`'s components.
 *
 * Its translations, through i18next; its router, so a link does not reload
 * the application; Quanta's icons; and its own password-reset page. The
 * stylesheet beside this maps core's tokens onto Quanta's colours.
 * @module components/IdentityUI/AuroraIdentityUI
 */
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router';
import ArrowLeftSVG from '@plone/icons/svg/arrow-left.svg?react';
import ArrowRightSVG from '@plone/icons/svg/arrow-right.svg?react';
import BinSVG from '@plone/icons/svg/bin.svg?react';
import ChevronRightSVG from '@plone/icons/svg/chevron-right.svg?react';
import CloseSVG from '@plone/icons/svg/close.svg?react';
import { IdentityUIProvider } from '@plone-collective/identity-core';
import type {
  IdentityIcons,
  IdentityLinkProps,
  IdentityPaths,
} from '@plone-collective/identity-core';

import { translateWith } from '../../lib/i18n';

import './AuroraIdentityUI.css';

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

/** Quanta's, the ones Aurora's own login button wears. */
const icons: IdentityIcons = {
  submit: <ArrowRightSVG aria-hidden="true" focusable="false" />,
  clear: <CloseSVG aria-hidden="true" focusable="false" />,
  back: <ArrowLeftSVG aria-hidden="true" focusable="false" />,
  details: <ChevronRightSVG aria-hidden="true" focusable="false" />,
  remove: <BinSVG aria-hidden="true" focusable="false" />,
};

/** Aurora's own pages, where they are not where Volto has them. */
const paths: Partial<IdentityPaths> = {
  passwordReset: '/reset-password',
};

/**
 * Lend the components inside Aurora's translations, router and icons.
 *
 * @param props The components to lend them to.
 * @returns The provider.
 */
export default function AuroraIdentityUI({
  children,
}: {
  children: ReactNode;
}) {
  const { t, i18n } = useTranslation();
  return (
    <IdentityUIProvider
      t={translateWith(t, i18n.language)}
      locale={i18n.language}
      Link={AuroraLink}
      icons={icons}
      paths={paths}
    >
      {children}
    </IdentityUIProvider>
  );
}
