/**
 * How one user gets in, and when they last did.
 *
 * Two questions an administrator could not ask anywhere in Plone. Which
 * providers this person has configured -- `@users` carries the identities as
 * bare ids, which is not something to show somebody -- and when they last
 * authenticated, which nothing in Plone records at all.
 *
 * Presentational: the route that shows this owns the request, so it can be
 * rendered in a story and in a test without a store.
 *
 * Three sections, and they are tabs rather than a column of headings. It is
 * three separate questions about one person -- how they get in, which
 * addresses are theirs, what they have done lately -- and an administrator
 * opening this page has one of them in mind, not all three. The same tabs the
 * sign-in methods page wears, since that page is this question asked by the
 * account's owner.
 * @module components/ControlPanel/UserAccountPanel
 */
import React from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { Tabs } from '@plone/components';
import { Tab, TabList, TabPanel } from 'react-aria-components';

// `@plone/components` ships its CSS separately from its components, so a Tabs
// rendered without this is unstyled -- the same split `PasswordForm` documents
// for TextField.css. `.identity-tabs` in the root stylesheet adds the add-on's
// own colours on top.
import '@plone/components/src/styles/basic/Tabs.css';

import type { UserAccount } from '../../types';

import './UserAccountPanel.scss';

const messages = defineMessages({
  loading: { id: 'user-account-loading', defaultMessage: 'Loading…' },
  failed: {
    id: 'user-account-failed',
    defaultMessage: 'That could not be read.',
  },
  lastAuthenticated: {
    id: 'Last signed in',
    defaultMessage: 'Last signed in',
  },
  never: {
    id: 'user-account-never',
    defaultMessage: 'Not in the retained log',
  },
  neverHelp: {
    id: 'user-account-never-help',
    defaultMessage:
      'Not the same as never: the authentication log is bounded, so an ' +
      'account dormant longer than the retention period has had its ' +
      'entries dropped.',
  },
  providers: { id: 'Sign-in methods', defaultMessage: 'Sign-in methods' },
  noProviders: {
    id: 'user-account-no-providers',
    defaultMessage: 'This account signs in with a password only.',
  },
  linked: { id: 'user-account-linked', defaultMessage: 'linked {date}' },
  lastUsed: {
    id: 'user-account-last-used',
    defaultMessage: 'last used {date}',
  },
  neverUsed: {
    id: 'user-account-never-used',
    defaultMessage: 'never used',
  },
  disabled: { id: 'Disabled', defaultMessage: 'Disabled' },
  disabledHelp: {
    id: 'user-account-disabled-help',
    defaultMessage:
      'The provider is switched off, so this identity cannot sign anybody in.',
  },
  gone: { id: 'Not configured', defaultMessage: 'Not configured' },
  goneHelp: {
    id: 'user-account-gone-help',
    defaultMessage:
      'The provider was removed while this identity was still stored ' +
      'against it. Nobody can sign in through it, and nothing was deleted.',
  },
  addresses: { id: 'Email addresses', defaultMessage: 'Email addresses' },
  verified: { id: 'Verified', defaultMessage: 'Verified' },
  noAddresses: {
    id: 'user-account-no-addresses',
    defaultMessage: 'This account has no profile, so it carries no addresses.',
  },
  events: { id: 'Recent activity', defaultMessage: 'Recent activity' },
  sections: {
    id: 'user-account-sections',
    defaultMessage: 'What this account is made of',
  },
  noEvents: {
    id: 'user-account-no-events',
    defaultMessage: 'Nothing recorded.',
  },
});

/**
 * Render an ISO timestamp for a reader.
 *
 * `toLocaleString` rather than a format of our own: an administrator reading
 * a login time wants it in the conventions of their own machine, and this
 * panel has no locale opinion worth imposing.
 *
 * @param value An ISO 8601 timestamp, or null.
 * @returns The formatted date, or null.
 */
export function formatDate(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  // An unparseable timestamp is a backend that changed shape; showing
  // "Invalid Date" in a control panel is worse than showing nothing.
  return Number.isNaN(parsed.getTime()) ? null : parsed.toLocaleString();
}

interface UserAccountPanelProps {
  account?: UserAccount | null;
  loading: boolean;
  error?: unknown;
}

const UserAccountPanel: React.FC<UserAccountPanelProps> = ({
  account,
  loading,
  error,
}) => {
  const intl = useIntl();

  if (loading) {
    return (
      <div className="identity-account" role="status">
        {intl.formatMessage(messages.loading)}
      </div>
    );
  }
  if (error || !account) {
    return (
      <div className="identity-account" role="alert">
        {intl.formatMessage(messages.failed)}
      </div>
    );
  }

  const lastSeen = formatDate(account.last_authenticated);

  return (
    <div className="identity-account">
      <p className="identity-account__last">
        <strong>{intl.formatMessage(messages.lastAuthenticated)}: </strong>
        {lastSeen ?? (
          <span title={intl.formatMessage(messages.neverHelp)}>
            {intl.formatMessage(messages.never)}
          </span>
        )}
      </p>

      <Tabs className="identity-tabs">
        <TabList aria-label={intl.formatMessage(messages.sections)}>
          <Tab id="providers">{intl.formatMessage(messages.providers)}</Tab>
          <Tab id="addresses">{intl.formatMessage(messages.addresses)}</Tab>
          <Tab id="events">{intl.formatMessage(messages.events)}</Tab>
        </TabList>

        <TabPanel id="providers">
          {account.identities.length ? (
            <ul className="identity-account__list">
              {account.identities.map((identity) => (
                <li key={identity.provider} data-provider={identity.provider}>
                  <span className="identity-account__title">
                    {identity.title}
                  </span>
                  {!identity.provider_configured ? (
                    <span
                      className="identity-account__badge"
                      data-state="gone"
                      title={intl.formatMessage(messages.goneHelp)}
                    >
                      {intl.formatMessage(messages.gone)}
                    </span>
                  ) : !identity.provider_enabled ? (
                    <span
                      className="identity-account__badge"
                      data-state="disabled"
                      title={intl.formatMessage(messages.disabledHelp)}
                    >
                      {intl.formatMessage(messages.disabled)}
                    </span>
                  ) : null}
                  <span className="identity-note">
                    {intl.formatMessage(messages.linked, {
                      date: formatDate(identity.created) ?? identity.created,
                    })}
                    {', '}
                    {identity.last_login
                      ? intl.formatMessage(messages.lastUsed, {
                          date: formatDate(identity.last_login),
                        })
                      : intl.formatMessage(messages.neverUsed)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="identity-note">
              {intl.formatMessage(messages.noProviders)}
            </p>
          )}
        </TabPanel>

        <TabPanel id="addresses">
          {account.emails.length ? (
            <ul className="identity-account__list">
              {account.emails.map((entry) => (
                <li key={entry.address} data-address={entry.address}>
                  <span className="identity-account__title">
                    {entry.address}
                  </span>
                  {entry.verified ? (
                    <span
                      className="identity-account__badge"
                      data-state="verified"
                    >
                      {intl.formatMessage(messages.verified)}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="identity-note">
              {intl.formatMessage(messages.noAddresses)}
            </p>
          )}
        </TabPanel>

        <TabPanel id="events">
          {account.events.length ? (
            <ul className="identity-account__list">
              {account.events.map((event, index) => (
                <li
                  // Nothing in an audit entry is unique -- two sign-ins a second
                  // apart through the same provider are identical but for the
                  // timestamp -- and the list is a fixed newest-first slice that
                  // is never reordered, so the position is the honest key.
                  key={`${event.timestamp}-${index}`}
                  data-event={event.event}
                  data-success={String(event.success)}
                >
                  <span className="identity-account__title">{event.event}</span>
                  <span className="identity-note">
                    {event.provider}
                    {' · '}
                    {formatDate(event.timestamp) ?? event.timestamp}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="identity-note">
              {intl.formatMessage(messages.noEvents)}
            </p>
          )}
        </TabPanel>
      </Tabs>
    </div>
  );
};

export default UserAccountPanel;
