/**
 * The applications a user has authorized, without store or routing.
 *
 * The mirror image of the identities page: that one lists the providers
 * somebody signs in *with*, this one the applications they signed in *to*.
 *
 * Shaped like the control panels — a table of what exists, then one
 * application's details on their own — for the same reason those are: a row
 * per thing scans, and the detail nobody is looking at costs nothing to read.
 * The claims in particular are the reason: a person scanning four
 * applications wants their names, and a person deciding whether to withdraw
 * one wants every field it can read.
 *
 * Two things it is careful about, and both are about not lying to the reader.
 * It names what each scope actually releases rather than the scope itself,
 * because "profile" tells a person nothing while "name, preferred_username,
 * picture" is what they agreed to hand over. And it says out loud that
 * withdrawing does not stop an access token already issued: those are
 * self-encoded with no denylist and live out their lifetime, so a screen
 * promising an instant cutoff would be promising something the server cannot
 * do.
 * @module components/Applications/ApplicationsPanel
 */
import React from 'react';
import { FormattedMessage, defineMessages, useIntl } from 'react-intl';
import { Button, Table } from 'semantic-ui-react';

import Icon from '@plone/volto/components/theme/Icon/Icon';
import backSVG from '@plone/volto/icons/back.svg';
import deleteSVG from '@plone/volto/icons/delete.svg';
import rightArrowSVG from '@plone/volto/icons/right-key.svg';

import type { OAuthGrant, OAuthGrants } from '../../types';

import './ApplicationsPanel.scss';

const messages = defineMessages({
  loading: {
    id: 'Loading the applications you have authorized',
    defaultMessage: 'Loading the applications you have authorized…',
  },
  empty: {
    id: 'You have not authorized any application.',
    defaultMessage:
      'You have not authorized any application. Anything you sign in to with ' +
      'this account will ask you first, and appear here afterwards.',
  },
  unavailable: {
    id: 'That list could not be loaded.',
    defaultMessage: 'That list could not be loaded.',
  },
  columnApplication: { id: 'Application', defaultMessage: 'Application' },
  columnAuthorized: { id: 'Authorized', defaultMessage: 'Authorized' },
  columnReads: { id: 'Reads', defaultMessage: 'Reads' },
  columnActions: { id: 'Actions', defaultMessage: 'Actions' },
  details: { id: 'Details', defaultMessage: 'Details' },
  back: { id: 'Back to the list', defaultMessage: 'Back to the list' },
  nothing: { id: 'Nothing', defaultMessage: 'Nothing' },
  fields: {
    id: '{count, plural, one {# field} other {# fields}}',
    defaultMessage: '{count, plural, one {# field} other {# fields}}',
  },
  granted: {
    id: 'You authorized this application on {date}.',
    defaultMessage: 'You authorized this application on {date}.',
  },
  canRead: { id: 'It can read:', defaultMessage: 'It can read:' },
  readsNothing: {
    id: 'Nothing beyond the fact that you signed in.',
    defaultMessage: 'Nothing beyond the fact that you signed in.',
  },
  scopes: { id: 'Scopes agreed to', defaultMessage: 'Scopes agreed to' },
  unregistered: {
    id: 'This application is no longer registered on this site.',
    defaultMessage:
      'This application is no longer registered on this site. It cannot ask ' +
      'for anything, and you can remove the record.',
  },
  disabled: {
    id: 'This application is disabled and is being refused already.',
    defaultMessage:
      'This application is disabled and is being refused already.',
  },
  withdraw: { id: 'Withdraw access', defaultMessage: 'Withdraw access' },
  lingering: {
    id: 'Withdrawing signs it out and makes it ask again.',
    defaultMessage:
      'Withdrawing signs an application out everywhere and makes it ask you ' +
      'again next time. An access token it already holds keeps working for ' +
      'up to {minutes, plural, one {# minute} other {# minutes}} — this site ' +
      'cannot recall one that was already issued.',
  },
});

interface ApplicationsPanelProps {
  grants: OAuthGrants | null;
  loading: boolean;
  /** Whether the listing could not be read. */
  error?: unknown;
  /** The application whose details are on screen, if any. */
  selected: string | null;
  /** The client currently being withdrawn, if any. */
  withdrawing: string | null;
  onSelect: (clientId: string | null) => void;
  onWithdraw: (clientId: string) => void;
}

/**
 * Every field an application can read, named once.
 *
 * Deduplicated across scopes: the reader wants the list of things, not the
 * list of scopes that happen to contain them.
 *
 * @param grant The agreement.
 * @returns The claim names.
 */
function claimsOf(grant: OAuthGrant): string[] {
  return Array.from(new Set(grant.scopes.flatMap((scope) => scope.claims)));
}

const ApplicationsPanel: React.FC<ApplicationsPanelProps> = ({
  grants,
  loading,
  error,
  selected,
  withdrawing,
  onSelect,
  onWithdraw,
}) => {
  const intl = useIntl();

  if (loading || (!grants && !error)) {
    return (
      <div className="identity-applications" role="status">
        {intl.formatMessage(messages.loading)}
      </div>
    );
  }

  if (!grants) {
    return (
      <div className="identity-applications">
        <p className="identity-error" role="alert">
          {intl.formatMessage(messages.unavailable)}
        </p>
      </div>
    );
  }

  /** How long access already granted can outlive a withdrawal. */
  const lingering = (
    <p className="identity-applications__lingering identity-note">
      <FormattedMessage
        {...messages.lingering}
        values={{
          // Rounded up: saying "up to 1 minute" for 90 seconds would
          // understate it.
          minutes: Math.max(1, Math.ceil(grants.access_token_ttl / 60)),
        }}
      />
    </p>
  );

  const current = selected
    ? grants.items.find((item) => item.client_id === selected)
    : undefined;

  if (current) {
    const claims = claimsOf(current);
    const busy = withdrawing === current.client_id;
    return (
      <div className="identity-applications" data-client={current.client_id}>
        <button
          type="button"
          className="identity-applications__back"
          onClick={() => onSelect(null)}
        >
          <Icon name={backSVG} size="18px" />
          {intl.formatMessage(messages.back)}
        </button>

        <h2>
          {current.title}{' '}
          <small>
            <code>{current.client_id}</code>
          </small>
        </h2>
        <p className="identity-note">
          {intl.formatMessage(messages.granted, {
            // The date only. The hour somebody clicked Allow is not
            // something they remember, and printing it invites them to try.
            date: intl.formatDate(current.granted_at, {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            }),
          })}
        </p>

        {!current.registered ? (
          <p className="identity-note" role="status">
            {intl.formatMessage(messages.unregistered)}
          </p>
        ) : !current.enabled ? (
          <p className="identity-note" role="status">
            {intl.formatMessage(messages.disabled)}
          </p>
        ) : null}

        <h3>{intl.formatMessage(messages.canRead)}</h3>
        {claims.length ? (
          <ul className="identity-applications__claims">
            {claims.map((claim) => (
              <li key={claim}>
                <code>{claim}</code>
              </li>
            ))}
          </ul>
        ) : (
          <p className="identity-note">
            {intl.formatMessage(messages.readsNothing)}
          </p>
        )}

        {/* The scopes as well as the claims, on the detail view only. They
            are what the client asked for and what a support conversation
            will be about; the claims are what the person actually cares
            about, which is why the list above leads. */}
        <h3>{intl.formatMessage(messages.scopes)}</h3>
        <p>
          <code>{current.scopes.map((scope) => scope.id).join(' ')}</code>
        </p>

        <button
          type="button"
          className="identity-button identity-button--danger"
          data-action="withdraw"
          disabled={busy}
          onClick={() => onWithdraw(current.client_id)}
        >
          {intl.formatMessage(messages.withdraw)}
        </button>

        {lingering}
      </div>
    );
  }

  if (!grants.items.length) {
    return (
      <div className="identity-applications">
        <p className="identity-applications__empty identity-note">
          {intl.formatMessage(messages.empty)}
        </p>
      </div>
    );
  }

  return (
    <div className="identity-applications">
      <Table selectable compact>
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell>
              {intl.formatMessage(messages.columnApplication)}
            </Table.HeaderCell>
            <Table.HeaderCell>
              {intl.formatMessage(messages.columnAuthorized)}
            </Table.HeaderCell>
            <Table.HeaderCell>
              {intl.formatMessage(messages.columnReads)}
            </Table.HeaderCell>
            <Table.HeaderCell textAlign="right">
              {intl.formatMessage(messages.columnActions)}
            </Table.HeaderCell>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {grants.items.map((grant) => {
            const count = claimsOf(grant).length;
            return (
              <Table.Row key={grant.client_id} data-client={grant.client_id}>
                <Table.Cell>
                  {grant.title}
                  {!grant.registered || !grant.enabled ? (
                    <p className="identity-note" role="status">
                      {intl.formatMessage(
                        grant.registered
                          ? messages.disabled
                          : messages.unregistered,
                      )}
                    </p>
                  ) : null}
                </Table.Cell>
                <Table.Cell>
                  {intl.formatDate(grant.granted_at, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </Table.Cell>
                <Table.Cell>
                  {/* A count in the row, the names on the detail view: four
                      rows of claim lists is a wall nobody reads. */}
                  {count
                    ? intl.formatMessage(messages.fields, { count })
                    : intl.formatMessage(messages.nothing)}
                </Table.Cell>
                <Table.Cell textAlign="right">
                  <Button
                    basic
                    icon
                    aria-label={intl.formatMessage(messages.details)}
                    title={intl.formatMessage(messages.details)}
                    onClick={() => onSelect(grant.client_id)}
                  >
                    <Icon name={rightArrowSVG} size="20px" />
                  </Button>
                  <Button
                    basic
                    icon
                    data-action="withdraw"
                    disabled={withdrawing === grant.client_id}
                    aria-label={intl.formatMessage(messages.withdraw)}
                    title={intl.formatMessage(messages.withdraw)}
                    onClick={() => onWithdraw(grant.client_id)}
                  >
                    <Icon name={deleteSVG} size="20px" />
                  </Button>
                </Table.Cell>
              </Table.Row>
            );
          })}
        </Table.Body>
      </Table>

      {lingering}
    </div>
  );
};

export default ApplicationsPanel;
