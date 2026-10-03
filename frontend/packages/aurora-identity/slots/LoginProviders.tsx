/**
 * The providers on Aurora's login page.
 *
 * A button per provider, in the order an operator gave them, under the
 * password form Aurora draws itself. The list comes from the root loader --
 * see `config/server.ts` -- so the buttons are in the page as it is served.
 * @module slots/LoginProviders
 */
import { useLocation, useRouteLoaderData } from 'react-router';
import {
  EMAIL_DRIVER,
  ProviderButton,
  returnUrl,
} from '@plone-collective/identity-core';
import type { LoginProvider } from '@plone-collective/identity-core';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import { PROVIDERS_KEY } from '../config/constants';
import { startPath } from '../lib/paths';

import './LoginProviders.css';

export default function LoginProviders() {
  const rootData = useRouteLoaderData('root') as
    Record<string, unknown> | undefined;
  const location = useLocation();
  // The email "provider" is the magic link, which is a form, not a button.
  const providers = (
    (rootData?.[PROVIDERS_KEY] as LoginProvider[] | undefined) ?? []
  ).filter((provider) => provider.driver !== EMAIL_DRIVER);
  if (providers.length === 0) {
    return null;
  }
  const cameFrom = returnUrl(location.search, location.pathname);

  return (
    <AuroraIdentityUI>
      <div className="identity-login-providers">
        {providers.map((provider) => (
          <ProviderButton
            key={provider.id}
            id={provider.id}
            driver={provider.driver}
            label={provider.title}
            icon={provider.icon}
            background_color={provider.background_color}
            foreground_color={provider.foreground_color}
            // A whole-page navigation, not the router's: the start route
            // answers with a redirect to the provider, off this site.
            onSelect={() =>
              window.location.assign(
                startPath(provider.id, cameFrom === '/' ? '' : cameFrom),
              )
            }
          />
        ))}
      </div>
    </AuroraIdentityUI>
  );
}
