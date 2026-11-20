/**
 * Login container: the page around the card, and whether it redirects.
 *
 * What the card says and what the form needs from the store and the router
 * are `useLogin`, which the sign-in block shares.
 * @module components/Login/Login
 */
import React, { useEffect } from 'react';
import { useHistory, useLocation } from 'react-router-dom';

import {
  clearHandoff,
  HANDOFF_PATH,
  readHandoffRequest,
  storeHandoff,
} from '../../helpers/handoff';
import {
  asksToChoose,
  redirectToSoleProvider,
} from '../../helpers/redirectToSoleProvider';
import LoginForm from './LoginForm';
import LoginPanel from './LoginPanel';
import { useLogin } from './useLogin';

const Login: React.FC = () => {
  const location = useLocation();
  const { replace } = useHistory();
  const { form, title, description, sessionOnArrival } = useLogin();

  // A local application asking for the token (`helpers/handoff`). Kept until
  // the consent page, which every way in ends at while it is pending.
  // Somebody already signed in is asked straight away: the question is the
  // same.
  //
  // Any other visit forgets an earlier request, so one somebody abandoned
  // does not ask its question at their next ordinary sign-in -- except
  // `?choose`, which is the callback page sending somebody back to the
  // options after a sign-in failed, in the middle of the same request.
  //
  // Only on this page, not in `useLogin`: the sign-in block shares that, and
  // a block on whatever page the profile gate shows must not forget it.
  useEffect(() => {
    const request = readHandoffRequest(location.search);
    if (request && request !== 'refused') {
      storeHandoff(request);
      if (sessionOnArrival) {
        replace(HANDOFF_PATH);
      }
    } else if (!asksToChoose(location.search)) {
      clearHandoff();
    }
  }, [location.search, sessionOnArrival, replace]);

  // Whether a sole provider may be started without showing its button. The
  // site answers first, and this visit can still say no:
  //
  // - Arriving signed in means something refused that session. A provider
  //   that still has a session of its own signs the visitor straight back in
  //   as the same account, and straight back here: a loop.
  // - `?choose` is somebody asking for the options -- among them the callback
  //   page, after a sign-in failed.
  const redirect =
    redirectToSoleProvider() &&
    !sessionOnArrival &&
    !asksToChoose(location.search);

  return (
    <LoginPanel title={title} description={description}>
      <LoginForm {...form} redirectToSoleProvider={redirect} />
    </LoginPanel>
  );
};

export default Login;
