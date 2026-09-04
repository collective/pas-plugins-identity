/**
 * The "your sign-in methods" panel, without store or routing.
 *
 * Two sections, and they are tabs rather than a column: the providers you
 * sign in through, and the addresses that are yours. They were stacked, so
 * the page read as a pile of everything that could be said about how you get
 * in -- and the addresses, which is where the work usually is, were below
 * whatever length the provider list happened to be.
 *
 * The same tabs the control panel's account page wears, because this is that
 * page's question asked by the account's owner rather than by an
 * administrator.
 * @module components/Identities/IdentitiesList
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { Tabs } from '@plone/components';
import { Tab, TabList, TabPanel } from 'react-aria-components';

// `@plone/components` ships its CSS separately from its components; see the
// note on the same import in `UserAccountPanel`.
import '@plone/components/src/styles/basic/Tabs.css';

import type { Identity, LoginProvider, ProfileEmail } from '../../types';
import ProviderButton from '../Login/ProviderButton';
import ProfileEmails from './ProfileEmails';

import './IdentitiesList.scss';

const messages = defineMessages({
  loading: {
    id: 'Loading your sign-in methods',
    defaultMessage: 'Loading your sign-in methods…',
  },
  remove: { id: 'Remove', defaultMessage: 'Remove' },
  lastWayIn: {
    id: 'This is your only way to sign in. Add another first.',
    defaultMessage: 'This is your only way to sign in. Add another first.',
  },
  empty: {
    id: 'You have no external sign-in methods linked yet.',
    defaultMessage: 'You have no external sign-in methods linked yet.',
  },
  addAnother: { id: 'Add another', defaultMessage: 'Add another' },
  providers: { id: 'Sign-in methods', defaultMessage: 'Sign-in methods' },
  addresses: { id: 'Email addresses', defaultMessage: 'Email addresses' },
  sections: {
    id: 'identities-sections',
    defaultMessage: 'How you sign in',
  },
  failed: {
    id: 'That did not work. Please try again.',
    defaultMessage: 'That did not work. Please try again.',
  },
});

interface IdentitiesListProps {
  identities: Identity[];
  /**
   * Providers that could still be added.
   *
   * The backend's own `available`, not a filter applied here. It is the
   * *enabled* providers minus the ones already linked, which is a different
   * question from the login screen's listing -- a provider an operator has
   * taken off the login page is still one an existing user may attach.
   */
  available: LoginProvider[];
  /** The caller's own addresses, and which of them are verified. */
  emails: ProfileEmail[];
  /** Where the caller's profile is, when they have one. */
  profileUrl?: string | null;
  loading: boolean;
  busy: boolean;
  error?: unknown;
  /** Whether a confirmation mail has gone out for an address. */
  emailSent: boolean;
  onLink: (provider: LoginProvider) => void;
  /**
   * Whether the email provider is one of the ways in on the login page.
   *
   * Passed straight to `ProfileEmails`, where the reason it matters is
   * written down.
   */
  canSignInWithLink: boolean;
  onVerifyEmail: (address: string) => void;
  /** Move an address to the front of the caller's list, when they can. */
  onPreferEmail?: (address: string) => void;
  onUnlink: (identity: Identity) => void;
}

const IdentitiesList: React.FC<IdentitiesListProps> = ({
  identities,
  available,
  canSignInWithLink,
  emails,
  profileUrl,
  loading,
  busy,
  error,
  emailSent,
  onLink,
  onVerifyEmail,
  onPreferEmail,
  onUnlink,
}) => {
  const intl = useIntl();

  if (loading) {
    return (
      <div className="identity-identities" role="status">
        {intl.formatMessage(messages.loading)}
      </div>
    );
  }

  return (
    <div className="identity-identities">
      <Tabs className="identity-tabs">
        <TabList aria-label={intl.formatMessage(messages.sections)}>
          <Tab id="providers">{intl.formatMessage(messages.providers)}</Tab>
          <Tab id="addresses">{intl.formatMessage(messages.addresses)}</Tab>
        </TabList>

        <TabPanel id="providers">
          <ul className="identity-identities__list">
            {identities.map((identity) => (
              <li key={identity['@id']} data-provider={identity.provider}>
                <span className="identity-identities__title">
                  {identity.title}
                </span>
                <span className="identity-identities__subject identity-note">
                  {identity.subject}
                </span>
                <button
                  type="button"
                  className="identity-button identity-button--danger"
                  disabled={busy || !identity.can_unlink}
                  // Surfaced: the backend refuses to remove the last way in,
                  // and a button that only fails when pressed is worse than one
                  // that explains itself.
                  title={
                    identity.can_unlink
                      ? undefined
                      : intl.formatMessage(messages.lastWayIn)
                  }
                  data-action="unlink"
                  onClick={() => onUnlink(identity)}
                >
                  {intl.formatMessage(messages.remove)}
                </button>
              </li>
            ))}
          </ul>

          {identities.length === 0 ? (
            <p className="identity-identities__empty identity-note">
              {intl.formatMessage(messages.empty)}
            </p>
          ) : null}

          {available.length ? (
            <div className="identity-identities__add">
              <h3>{intl.formatMessage(messages.addAnother)}</h3>
              <ul>
                {available.map((provider) => (
                  <li key={provider.id}>
                    <ProviderButton
                      id={provider.id}
                      driver={provider.driver}
                      label={provider.title || provider.id}
                      icon={provider.icon}
                      background_color={provider.background_color}
                      foreground_color={provider.foreground_color}
                      disabled={busy}
                      onSelect={() => onLink(provider)}
                    />
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </TabPanel>

        <TabPanel id="addresses">
          <ProfileEmails
            emails={emails}
            profileUrl={profileUrl}
            loading={loading}
            busy={busy}
            sent={emailSent}
            canSignInWithLink={canSignInWithLink}
            onVerify={onVerifyEmail}
            onPrefer={onPreferEmail}
          />
        </TabPanel>
      </Tabs>

      {error ? (
        <p className="identity-error" role="alert">
          {intl.formatMessage(messages.failed)}
        </p>
      ) : null}
    </div>
  );
};

export default IdentitiesList;
