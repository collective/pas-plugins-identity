/**
 * What the sign-in block shows somebody who is signed in.
 *
 * The login card, headed with the welcome message rather than "Log in". The
 * block holds the same card whichever half of it is showing, so signing in
 * changes what the card says and not what it looks like.
 *
 * Presentational: every line arrives ready to print, and a line with nothing
 * to say is left out rather than printed empty.
 * @module components/Welcome/WelcomeCard
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';

import LoginCard from '../Login/LoginCard';
import type { ProfileEmail } from '../../types';

import './WelcomeCard.scss';

const messages = defineMessages({
  welcome: { id: 'Welcome', defaultMessage: 'Welcome' },
  profile: { id: 'Your profile', defaultMessage: 'Your profile' },
  email: { id: 'Preferred email', defaultMessage: 'Preferred email' },
  verified: { id: 'verified', defaultMessage: 'verified' },
  unverified: { id: 'not verified', defaultMessage: 'not verified' },
  provider: { id: 'Authenticated with', defaultMessage: 'Authenticated with' },
  lastLogin: { id: 'Last login', defaultMessage: 'Last login' },
});

export interface WelcomeCardProps {
  /**
   * The welcome message, placeholders already filled in.
   *
   * It heads the card. Empty, the card is headed "Welcome" instead: a card
   * with a blank heading reads as one that failed to load.
   */
  greeting: string;
  /** A link to the user's Profile, as a path inside this site. */
  profile?: { to: string; label: string } | null;
  /** The address standing for the user. */
  email?: ProfileEmail | null;
  /** The title of what they signed in with. */
  provider?: string | null;
  /** When they signed in before this, already formatted. */
  lastLogin?: string | null;
}

const WelcomeCard: React.FC<WelcomeCardProps> = ({
  greeting,
  profile,
  email,
  provider,
  lastLogin,
}) => {
  const intl = useIntl();
  const summary = Boolean(profile || email || provider || lastLogin);

  return (
    <div className="identity-welcome">
      <LoginCard title={greeting || intl.formatMessage(messages.welcome)}>
        {summary ? (
          <dl className="identity-welcome__summary">
            {profile ? (
              <>
                <dt>{intl.formatMessage(messages.profile)}</dt>
                <dd>
                  <Link to={profile.to}>{profile.label}</Link>
                </dd>
              </>
            ) : null}
            {email ? (
              <>
                <dt>{intl.formatMessage(messages.email)}</dt>
                <dd>
                  {email.address}{' '}
                  <span className="identity-welcome__verified">
                    (
                    {intl.formatMessage(
                      email.verified ? messages.verified : messages.unverified,
                    )}
                    )
                  </span>
                </dd>
              </>
            ) : null}
            {provider ? (
              <>
                <dt>{intl.formatMessage(messages.provider)}</dt>
                <dd>{provider}</dd>
              </>
            ) : null}
            {lastLogin ? (
              <>
                <dt>{intl.formatMessage(messages.lastLogin)}</dt>
                <dd>{lastLogin}</dd>
              </>
            ) : null}
          </dl>
        ) : null}
      </LoginCard>
    </div>
  );
};

export default WelcomeCard;
