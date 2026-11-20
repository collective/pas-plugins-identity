/**
 * The question asked before the session token leaves the site.
 *
 * Without any store or routing in it. It names the person and the site,
 * because the browser may carry a session somebody forgot about, and a token
 * for the wrong account handed to a tool on this computer is the mistake
 * this page is there to make visible.
 *
 * Allow is a real form, posted by the browser to the loopback address: the
 * router cannot leave the origin, and a POST keeps the token out of the
 * browser's history and every server log on the way.
 * @module components/Handoff/HandoffPanel
 */
import React from 'react';
import { Container } from '@plone/components';
import { defineMessages, useIntl } from 'react-intl';

import type { HandoffRequest } from '../../helpers/handoff';

import '../Consent/ConsentPanel.scss';

const messages = defineMessages({
  heading: {
    id: 'Allow an application on this computer to use your account?',
    defaultMessage:
      'Allow an application on this computer to use your account?',
  },
  question: {
    id: 'An application on this computer asks to act as {user} on {site}.',
    defaultMessage:
      'An application on this computer asks to act as {user} on {site}.',
  },
  warning: {
    id: 'Only allow it if you started the sign-in from that application yourself.',
    defaultMessage:
      'Only allow it if you started the sign-in from that application ' +
      'yourself. It will be able to do anything you can do on this site.',
  },
  allow: { id: 'Allow', defaultMessage: 'Allow' },
  deny: { id: 'Deny', defaultMessage: 'Deny' },
});

export interface HandoffPanelProps {
  /** Where the token goes, and the state that goes with it. */
  request: HandoffRequest;
  /** The session token handed over on Allow. */
  token: string;
  /** Who the token signs in as. */
  user: string;
  /** The site the token is for. */
  site: string;
  /** Called as the browser starts posting the form. */
  onAllow: () => void;
  onDeny: () => void;
}

const HandoffPanel: React.FC<HandoffPanelProps> = ({
  request,
  token,
  user,
  site,
  onAllow,
  onDeny,
}) => {
  const intl = useIntl();

  return (
    <Container className="identity-consent identity-handoff">
      <h1>{intl.formatMessage(messages.heading)}</h1>
      <p>{intl.formatMessage(messages.question, { user, site })}</p>
      <p className="identity-note">{intl.formatMessage(messages.warning)}</p>

      <div className="identity-consent__actions">
        {/* Allow first, as on the authorization server's consent page. */}
        <form
          method="post"
          action={request.returnUrl}
          encType="application/x-www-form-urlencoded"
          onSubmit={onAllow}
        >
          <input type="hidden" name="token" value={token} />
          <input type="hidden" name="state" value={request.state} />
          <button
            type="submit"
            className="identity-button identity-button--primary"
          >
            {intl.formatMessage(messages.allow)}
          </button>
        </form>
        <button type="button" className="identity-button" onClick={onDeny}>
          {intl.formatMessage(messages.deny)}
        </button>
      </div>
    </Container>
  );
};

export default HandoffPanel;
