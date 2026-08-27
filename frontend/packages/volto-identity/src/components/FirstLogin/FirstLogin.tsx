/**
 * First-login routing.
 *
 * A user who has just signed in for the first time has a Profile in the
 * `incomplete` state and nothing in it. Sending them straight to wherever
 * they were heading means they never see it; asking every user to fill one in
 * on every login would be worse. This route asks the backend which of the two
 * applies and navigates accordingly.
 *
 * Wire it as the destination a successful sign-in navigates to, passing the
 * user's original target along:
 *
 * ```tsx
 * <Callback onToken={(token, cameFrom) => {
 *   dispatch(loginSuccess(token));
 *   history.push(`/first-login?return_url=${encodeURIComponent(cameFrom)}`);
 * }} />
 * ```
 *
 * It is a separate route rather than logic inside `Callback` so that a site
 * without the `[content]` extra can simply not use it, and so the decision is
 * reachable from a magic-link sign-in as well as an OAuth one.
 * @module components/FirstLogin/FirstLogin
 */
import React, { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useHistory, useLocation } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';

import { getMyProfile } from '../../actions';
import { afterLogin } from '../../helpers/firstLogin';
import { returnUrl } from '../../helpers/returnUrl';
import LoginPanel from '../Login/LoginPanel';

import './FirstLogin.scss';

const messages = defineMessages({
  title: { id: 'Log in', defaultMessage: 'Log in' },
  working: { id: 'Signing you in', defaultMessage: 'Signing you in…' },
});

interface FirstLoginProps {
  /** Backend base URL, when it differs from the frontend's. */
  apiPath?: string;
}

const FirstLogin: React.FC<FirstLoginProps> = ({ apiPath = '' }) => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const history = useHistory();
  const location = useLocation();
  const dispatched = useRef(false);
  const navigated = useRef(false);

  const profile = useSelector((state: any) => state.myProfile);

  useEffect(() => {
    if (dispatched.current) {
      return;
    }
    dispatched.current = true;
    dispatch(getMyProfile());
  }, [dispatch]);

  useEffect(() => {
    if (navigated.current) {
      return;
    }
    // An error here is not a reason to strand the user on a spinner: they are
    // signed in either way, and the worst case of carrying on is that they
    // fill their profile in later.
    if (!profile?.loaded && !profile?.error) {
      return;
    }
    navigated.current = true;
    const fallback = returnUrl(location.search, '/');
    history.replace(
      profile?.error ? fallback : afterLogin(profile.data, fallback, apiPath),
    );
  }, [profile, history, location.search, apiPath]);

  return (
    // The same card the callback and the login page are: this is the last
    // step of the same flow, and a bare line of text here sat against the
    // left edge of the window.
    <LoginPanel title={intl.formatMessage(messages.title)}>
      <p className="identity-first-login" role="status">
        {intl.formatMessage(messages.working)}
      </p>
    </LoginPanel>
  );
};

export default FirstLogin;
