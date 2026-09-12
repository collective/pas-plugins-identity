/**
 * Login container: the page around the card, and whether it redirects.
 *
 * What the card says and what the form needs from the store and the router
 * are `useLogin`, which the sign-in block shares.
 * @module components/Login/Login
 */
import React from 'react';
import { useLocation } from 'react-router-dom';

import {
  asksToChoose,
  redirectToSoleProvider,
} from '../../helpers/redirectToSoleProvider';
import LoginForm from './LoginForm';
import LoginPanel from './LoginPanel';
import { useLogin } from './useLogin';

const Login: React.FC = () => {
  const location = useLocation();
  const { form, title, description, sessionOnArrival } = useLogin();

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
