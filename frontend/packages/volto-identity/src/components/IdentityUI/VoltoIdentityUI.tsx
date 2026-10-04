/**
 * What Volto lends `identity-core`'s components.
 *
 * Its translations, through `react-intl`; its router, so a link does not
 * reload the application; and its icons. Every container rendering one of
 * those components wraps it in this, since Volto offers no place to wrap the
 * whole application.
 * @module components/IdentityUI/VoltoIdentityUI
 */
import React from 'react';
import type { ReactNode } from 'react';
import { useIntl } from 'react-intl';
import { Link as RouterLink } from 'react-router-dom';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import aheadSVG from '@plone/volto/icons/ahead.svg';
import backSVG from '@plone/volto/icons/back.svg';
import clearSVG from '@plone/volto/icons/clear.svg';
import deleteSVG from '@plone/volto/icons/delete.svg';
import rightArrowSVG from '@plone/volto/icons/right-key.svg';
import { IdentityUIProvider } from '@plone-collective/identity-core';
import type {
  IdentityLinkProps,
  Translate,
} from '@plone-collective/identity-core';

/**
 * Link through Volto's router.
 *
 * @param props The link.
 * @returns The router link.
 */
const VoltoLink = ({ href, className, children }: IdentityLinkProps) => (
  <RouterLink to={href} className={className}>
    {children}
  </RouterLink>
);

const icons = {
  submit: <Icon className="circled" name={aheadSVG} size="30px" />,
  clear: <Icon className="circled" name={clearSVG} size="30px" />,
  // The sizes the applications panel drew them at when it was Volto's.
  back: <Icon name={backSVG} size="18px" />,
  details: <Icon name={rightArrowSVG} size="20px" />,
  remove: <Icon name={deleteSVG} size="20px" />,
};

/**
 * Lend the components inside Volto's translations, router and icons.
 *
 * @param props The components to lend them to.
 * @returns The provider.
 */
export default function VoltoIdentityUI({ children }: { children: ReactNode }) {
  const intl = useIntl();
  const t: Translate = (message, values) => intl.formatMessage(message, values);
  return (
    <IdentityUIProvider
      t={t}
      Link={VoltoLink}
      icons={icons}
      locale={intl.locale}
    >
      {children}
    </IdentityUIProvider>
  );
}
