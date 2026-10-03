/**
 * The page a provider redirects back to.
 *
 * One line while the sign-in completes, or the reason it did not and a way
 * back to the options. What happens around it -- reading the query string,
 * asking the backend, storing the session -- is each frontend's own, so this
 * draws the outcome and nothing else.
 * @module components/Callback/CallbackCard
 */
import React from 'react';

import { defineMessages } from '#i18n';
import { useIdentityUI } from '../IdentityUI/IdentityUI';
import LoginCard from '../Login/LoginCard';

import './CallbackCard.css';

const messages = defineMessages({
  title: { id: 'Log in', defaultMessage: 'Log in' },
  working: { id: 'Signing you in', defaultMessage: 'Signing you in…' },
  linking: {
    id: 'Confirming your address',
    defaultMessage: 'Confirming your address…',
  },
  refused: {
    id: 'The provider refused the sign-in.',
    defaultMessage: 'The provider refused the sign-in.',
  },
  incomplete: {
    id: 'This sign-in link is incomplete.',
    defaultMessage: 'This sign-in link is incomplete.',
  },
  invalid: {
    id: 'That sign-in link is no longer valid. Please start again.',
    defaultMessage: 'That sign-in link is no longer valid. Please start again.',
  },
  unavailable: {
    id: 'That sign-in option is not available right now.',
    defaultMessage: 'That sign-in option is not available right now.',
  },
  backToOptions: {
    id: 'Back to sign-in options',
    defaultMessage: 'Back to sign-in options',
  },
});

/**
 * Why a sign-in did not complete.
 *
 * `refused`
 *     The provider sent the user back with an error.
 * `incomplete`
 *     The link carried neither a code nor a token.
 * `invalid`
 *     The backend refused what the link carried: expired, used, or from
 *     another session.
 * `unavailable`
 *     The sign-in could not be started, or the backend could not be reached.
 */
export type CallbackFailure =
  | 'refused'
  | 'incomplete'
  | 'invalid'
  | 'unavailable';

export interface CallbackCardProps {
  /** Why the sign-in did not complete; absent while it is completing. */
  failure?: CallbackFailure | null;
  /** Whether the sign-in is linking an identity rather than signing in. */
  linking?: boolean;
  /**
   * Where the way back leads.
   *
   * To the options rather than to `/login`: on a site with one provider,
   * `/login` starts that provider again, and a provider that refused somebody
   * refuses them every time.
   */
  retryHref: string;
}

const CallbackCard: React.FC<CallbackCardProps> = ({
  failure,
  linking = false,
  retryHref,
}) => {
  const { t, Link } = useIdentityUI();
  return (
    <LoginCard title={t(messages.title)}>
      {failure ? (
        <>
          <p
            className="identity-callback identity-callback--error"
            role="alert"
          >
            {t(messages[failure])}
          </p>
          <p className="identity-callback identity-callback--retry">
            <Link href={retryHref}>{t(messages.backToOptions)}</Link>
          </p>
        </>
      ) : (
        <p className="identity-callback" role="status">
          {t(linking ? messages.linking : messages.working)}
        </p>
      )}
    </LoginCard>
  );
};

export default CallbackCard;
