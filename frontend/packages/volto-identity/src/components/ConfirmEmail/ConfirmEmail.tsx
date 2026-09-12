/**
 * Asking which verified address stands for the signed-in user.
 *
 * A site can ask this at a first sign-in that brought more than one verified
 * address. The backend holds the Profile `incomplete` until its owner answers,
 * and the edit form cannot answer for them: which address stands for somebody
 * is the order of their addresses, a sign-in writes that order too, and so only
 * an explicit answer through `@confirm-email` counts. `ProfileGate` and the
 * first-login route send a user here when that answer is the only thing their
 * Profile is waiting on.
 *
 * It navigates nowhere once answered. The answer is `@my-profile` as it is
 * afterwards, the `myProfile` slice takes it in, and `ProfileGate` sees the
 * Profile released and returns the user to where they were going. A site that
 * does not mount the gate gets the confirmation and a way on.
 * @module components/ConfirmEmail/ConfirmEmail
 */
import React, { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';

import { confirmEmail, getMyProfile } from '../../actions';
import type { ProfileEmail } from '../../types';
import LoginPanel from '../Login/LoginPanel';

import './ConfirmEmail.scss';

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

const ConfirmEmail: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const asked = useRef(false);
  const [chosen, setChosen] = useState<string | null>(null);

  const token = useSelector((state: any) => state.userSession?.token);
  const profile = useSelector((state: any) => state.myProfile);
  const confirmation = useSelector((state: any) => state.emailConfirmation);

  useEffect(() => {
    // Asked only when nobody has: `ProfileGate` asks on every navigation, and
    // this page still has to work on a site that does not mount the gate.
    // Remembered in a ref rather than read off `loaded`, which a failed
    // request never becomes -- that would ask again on every render.
    if (!token || asked.current || profile?.loaded || profile?.loading) {
      return;
    }
    asked.current = true;
    dispatch(getMyProfile());
  }, [dispatch, token, profile?.loaded, profile?.loading]);

  // Verified only: the backend refuses anything else, and an unverified
  // address would not stand for anybody even at the front of the list.
  const verified: ProfileEmail[] = (profile?.data?.emails ?? []).filter(
    (entry: ProfileEmail) => entry.verified,
  );
  const selected =
    chosen ??
    verified.find((entry) => entry.preferred)?.address ??
    verified[0]?.address ??
    null;

  const recorded: string | undefined = confirmation?.loaded
    ? confirmation.data?.emails?.find((entry: ProfileEmail) => entry.preferred)
        ?.address
    : undefined;

  const onward = (
    <p className="identity-confirm-email__actions">
      <Link to="/">{intl.formatMessage(messages.continue)}</Link>
    </p>
  );

  let body: ReactNode;
  let asking = false;
  if (recorded) {
    body = (
      <>
        <p className="identity-confirm-email__status" role="status">
          {intl.formatMessage(messages.done, { address: recorded })}
        </p>
        {onward}
      </>
    );
  } else if (token && !profile?.loaded && !profile?.error) {
    body = (
      <p className="identity-confirm-email__status" role="status">
        {intl.formatMessage(messages.loading)}
      </p>
    );
  } else if (!profile?.data?.confirm_email || !verified.length) {
    body = (
      <>
        <p className="identity-confirm-email__status" role="status">
          {intl.formatMessage(messages.nothing)}
        </p>
        {onward}
      </>
    );
  } else {
    asking = true;
    body = (
      <form
        className="identity-confirm-email"
        onSubmit={(event) => {
          event.preventDefault();
          if (selected) {
            dispatch(confirmEmail(selected));
          }
        }}
      >
        <fieldset className="identity-confirm-email__choices">
          <legend>{intl.formatMessage(messages.legend)}</legend>
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
                disabled={Boolean(confirmation?.loading)}
                onChange={() => setChosen(entry.address)}
              />
              <span>{entry.address}</span>
            </label>
          ))}
        </fieldset>
        {confirmation?.error ? (
          <p className="identity-confirm-email__error" role="alert">
            {intl.formatMessage(messages.failed)}
          </p>
        ) : null}
        <button
          type="submit"
          className="identity-button identity-button--primary"
          disabled={!selected || Boolean(confirmation?.loading)}
        >
          {intl.formatMessage(messages.submit)}
        </button>
      </form>
    );
  }

  return (
    // The card the first-login wait and the login page are: this is the last
    // step of the same flow.
    <LoginPanel
      title={intl.formatMessage(messages.title)}
      description={
        asking ? intl.formatMessage(messages.description) : undefined
      }
    >
      {body}
    </LoginPanel>
  );
};

export default ConfirmEmail;
