/**
 * The consent screen, without any store or routing in it.
 *
 * A relying party sent this browser here to be asked something personal, and
 * the whole value of asking it *here* rather than on a standalone page is
 * that it looks like the site the person believes they are signing in to. So
 * this is ordinary site markup, in the same panel the login page uses.
 *
 * Two things it says that the protocol does not require, and both are the
 * reason the screen exists:
 *
 * - **who would be agreeing.** The browser may hold a session the user forgot
 *   about, and agreeing on behalf of the wrong account is the mistake this
 *   screen is there to make visible.
 *
 * - **what each scope actually releases.** "profile" means nothing to the
 *   person being asked; "your name, username, website, picture and bio" is
 *   the real question. The backend sends the claim list, and a scope it does
 *   not recognise says so rather than being quietly dropped.
 * @module components/Consent/ConsentPanel
 */
import React from 'react';
import { Container } from '@plone/components';
import { defineMessages, useIntl } from 'react-intl';

import type { ConsentRequest } from '../../types';

import './ConsentPanel.scss';

const messages = defineMessages({
  loading: {
    id: 'Loading the request',
    defaultMessage: 'Loading the request…',
  },
  heading: {
    id: 'Allow {client} to use your account?',
    defaultMessage: 'Allow {client} to use your account?',
  },
  signedInAs: {
    id: 'You are signed in as {user}.',
    defaultMessage: 'You are signed in as {user}.',
  },
  willBeAbleTo: {
    id: 'It will be able to read:',
    defaultMessage: 'It will be able to read:',
  },
  nothingInParticular: {
    id: 'nothing beyond the fact that you signed in',
    defaultMessage: 'nothing beyond the fact that you signed in',
  },
  allow: { id: 'Allow', defaultMessage: 'Allow' },
  deny: { id: 'Deny', defaultMessage: 'Deny' },
  unavailable: {
    id: 'This authorization request cannot be shown.',
    defaultMessage:
      'This authorization request cannot be shown. It may have been sent by ' +
      'an application this site does not know, or it may have expired — ' +
      'start again from the application you were signing in to.',
  },
});

interface ConsentPanelProps {
  /** The request being asked about, once it has loaded. */
  request: ConsentRequest | null;
  loading: boolean;
  /** Whether describing the request failed. */
  error?: unknown;
  /** Whether an answer is on its way and the browser is leaving. */
  answering: boolean;
  onAnswer: (allow: boolean) => void;
}

const ConsentPanel: React.FC<ConsentPanelProps> = ({
  request,
  loading,
  error,
  answering,
  onAnswer,
}) => {
  const intl = useIntl();

  if (loading || (!request && !error)) {
    return (
      <Container className="identity-consent" role="status">
        {intl.formatMessage(messages.loading)}
      </Container>
    );
  }

  if (!request) {
    // No buttons. There is nothing to agree to, and an "Allow" here would be
    // agreeing to something this page could not describe.
    return (
      <Container className="identity-consent">
        <p className="identity-error" role="alert">
          {intl.formatMessage(messages.unavailable)}
        </p>
      </Container>
    );
  }

  // Every claim the request would release, deduplicated across scopes: a
  // reader wants the list of things, not the list of scopes that happen to
  // contain them.
  const claims = Array.from(
    new Set(request.scopes.flatMap((scope) => scope.claims)),
  );

  return (
    <Container className="identity-consent">
      <h1>
        {intl.formatMessage(messages.heading, {
          client: request.client.title,
        })}
      </h1>
      <p className="identity-consent__who identity-note">
        {intl.formatMessage(messages.signedInAs, {
          user: request.user.label,
        })}
      </p>

      <p>{intl.formatMessage(messages.willBeAbleTo)}</p>
      {claims.length ? (
        <ul className="identity-consent__claims">
          {claims.map((claim) => (
            <li key={claim}>
              <code>{claim}</code>
            </li>
          ))}
        </ul>
      ) : (
        <p className="identity-note">
          {intl.formatMessage(messages.nothingInParticular)}
        </p>
      )}

      <div className="identity-consent__actions">
        {/* Deny first in the DOM would put it first for a keyboard, and
            first is where a hurried Enter lands. Allow is the affirmative
            answer, so it is the one that has to be chosen. */}
        <button
          type="button"
          className="identity-button identity-button--primary"
          disabled={answering}
          onClick={() => onAnswer(true)}
        >
          {intl.formatMessage(messages.allow)}
        </button>
        <button
          type="button"
          className="identity-button"
          disabled={answering}
          onClick={() => onAnswer(false)}
        >
          {intl.formatMessage(messages.deny)}
        </button>
      </div>
    </Container>
  );
};

export default ConsentPanel;
