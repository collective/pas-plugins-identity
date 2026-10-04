/**
 * Asking which verified address stands for the signed-in user.
 *
 * A site can ask this at a first sign-in that brought more than one verified
 * address. The backend holds the Profile `incomplete` until its owner answers,
 * and the edit form cannot answer for them: which address stands for somebody
 * is the order of their addresses, a sign-in writes that order too, and so only
 * an explicit answer through `@confirm-email` counts.
 *
 * This draws the question and its outcome. Asking the backend for the profile
 * and sending the answer are each frontend's own, so they arrive as props.
 * @module components/ConfirmEmail/ConfirmEmailCard
 */
import React, { useState } from 'react';
import type { ReactNode } from 'react';

import { defineMessages } from '#i18n';

import type { ProfileEmail } from '../../types';
import { useIdentityUI } from '../IdentityUI/IdentityUI';
import LoginCard from '../Login/LoginCard';

import './ConfirmEmailCard.css';

const messages = defineMessages({
  title: {
    id: 'Confirm your email address',
    defaultMessage: 'Confirm your email address',
  },
  description: {
    id: 'confirm-email-description',
    defaultMessage:
      'You have more than one verified email address. Choose the one this ' +
      'site should use for you.',
  },
  legend: {
    id: 'Your verified addresses',
    defaultMessage: 'Your verified addresses',
  },
  submit: { id: 'confirm-email-submit', defaultMessage: 'Confirm' },
  loading: { id: 'confirm-email-loading', defaultMessage: 'Loading…' },
  done: {
    id: 'confirm-email-done',
    defaultMessage: 'This site will use {address} for you.',
  },
  nothing: {
    id: 'confirm-email-nothing',
    defaultMessage: 'There is no email address waiting to be confirmed.',
  },
  failed: {
    id: 'confirm-email-failed',
    defaultMessage:
      'That address could not be confirmed. Reload the page and try again.',
  },
  continue: { id: 'confirm-email-continue', defaultMessage: 'Continue' },
});

/**
 * Where the confirmation stands.
 *
 * - `loading`: the profile has not arrived.
 * - `nothing`: there is no confirmation waiting.
 * - `asking`: there is, and the user has not answered.
 * - `done`: they answered, and the backend recorded it.
 */
export type ConfirmEmailStatus = 'loading' | 'nothing' | 'asking' | 'done';

export interface ConfirmEmailCardProps {
  status: ConfirmEmailStatus;
  /**
   * The profile's addresses.
   *
   * Only the verified ones are offered: the backend refuses anything else,
   * and an unverified address would not stand for anybody even at the front
   * of the list.
   */
  emails: ProfileEmail[];
  /** The address the backend recorded, once it has. */
  recorded?: string | null;
  /** Whether an answer is on its way. */
  busy: boolean;
  /** Whether the backend refused the answer. */
  failed: boolean;
  onConfirm: (address: string) => void;
  /** Where to go once there is nothing more to answer. */
  continueHref?: string;
}

const ConfirmEmailCard: React.FC<ConfirmEmailCardProps> = ({
  status,
  emails,
  recorded,
  busy,
  failed,
  onConfirm,
  continueHref = '/',
}) => {
  const { t, Link } = useIdentityUI();
  const [chosen, setChosen] = useState<string | null>(null);

  const verified = emails.filter((entry) => entry.verified);
  // The address already standing for the user to begin with, so confirming
  // without changing anything is a single click.
  const selected =
    chosen ??
    verified.find((entry) => entry.preferred)?.address ??
    verified[0]?.address ??
    null;

  const onward = (
    <p className="identity-confirm-email__actions">
      <Link href={continueHref}>{t(messages.continue)}</Link>
    </p>
  );

  let body: ReactNode;
  if (status === 'done' && recorded) {
    body = (
      <>
        <p className="identity-confirm-email__status" role="status">
          {t(messages.done, { address: recorded })}
        </p>
        {onward}
      </>
    );
  } else if (status === 'loading') {
    body = (
      <p className="identity-confirm-email__status" role="status">
        {t(messages.loading)}
      </p>
    );
  } else if (status !== 'asking' || !verified.length) {
    body = (
      <>
        <p className="identity-confirm-email__status" role="status">
          {t(messages.nothing)}
        </p>
        {onward}
      </>
    );
  } else {
    body = (
      <form
        className="identity-confirm-email"
        onSubmit={(event) => {
          event.preventDefault();
          if (selected) {
            onConfirm(selected);
          }
        }}
      >
        <fieldset className="identity-confirm-email__choices">
          <legend>{t(messages.legend)}</legend>
          {verified.map((entry) => (
            <label
              key={entry.address}
              className="identity-confirm-email__choice"
            >
              <input
                type="radio"
                name="identity-confirm-email"
                value={entry.address}
                checked={entry.address === selected}
                disabled={busy}
                onChange={() => setChosen(entry.address)}
              />
              <span>{entry.address}</span>
            </label>
          ))}
        </fieldset>
        {failed ? (
          <p className="identity-confirm-email__error" role="alert">
            {t(messages.failed)}
          </p>
        ) : null}
        <button
          type="submit"
          className="identity-button identity-button--primary"
          disabled={!selected || busy}
        >
          {t(messages.submit)}
        </button>
      </form>
    );
  }

  const asking = status === 'asking' && verified.length > 0;
  return (
    <LoginCard
      title={t(messages.title)}
      description={asking ? t(messages.description) : undefined}
    >
      {body}
    </LoginCard>
  );
};

export default ConfirmEmailCard;
