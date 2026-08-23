/**
 * Login container: store, routing, and the redirect out to the provider.
 * @module components/Login/Login
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useLocation } from 'react-router-dom';

import {
  listLoginProviders,
  sendMagicLink,
  startProviderLogin,
} from '../../actions';
import { login } from '@plone/volto/actions/userSession/userSession';

import { returnUrl } from '../../helpers/returnUrl';
import type { LoginProvider } from '../../types';
import LoginForm from './LoginForm';
import LoginPanel from './LoginPanel';

const Login: React.FC = () => {
  const dispatch = useDispatch();
  const location = useLocation();
  const [redirecting, setRedirecting] = useState(false);

  const providers = useSelector((state: any) => state.loginProviders);
  const started = useSelector((state: any) => state.providerLogin);
  const magic = useSelector((state: any) => state.magicLinkSend);
  const userSession = useSelector((state: any) => state.userSession);

  useEffect(() => {
    dispatch(listLoginProviders());
  }, [dispatch]);

  useEffect(() => {
    if (redirecting && started?.loaded && started?.data?.authorize_url) {
      // A full page load, not a router push: the next stop is the provider's
      // own origin.
      window.location.href = started.data.authorize_url;
    }
  }, [redirecting, started]);

  const onSelectProvider = useCallback(
    (provider: LoginProvider) => {
      setRedirecting(true);
      dispatch(
        startProviderLogin(
          provider.id,
          returnUrl(location.search, location.pathname),
        ),
      );
    },
    [dispatch, location.search, location.pathname],
  );

  const onPasswordLogin = useCallback(
    (username: string, password: string) => {
      dispatch(login(username, password));
    },
    [dispatch],
  );

  // Volto stores the token and its own AppExtras redirects; all this has to
  // do is get the user back to where the flow started, which for an
  // authorization request is the whole request.
  useEffect(() => {
    if (userSession?.token) {
      window.location.href = returnUrl(location.search, location.pathname);
    }
  }, [userSession?.token, location.search, location.pathname]);

  const onSendMagicLink = useCallback(
    (email: string) => {
      dispatch(sendMagicLink(email));
    },
    [dispatch],
  );

  // The description names what is actually below, which differs by site: a
  // provider list, a password form, or both.
  const hasProviders = Boolean(providers?.data?.length);
  const description = hasProviders
    ? 'Choose how you would like to sign in.'
    : 'Sign in with your account on this site.';

  return (
    <LoginPanel title="Log in" description={description}>
      <LoginForm
        providers={providers?.data ?? []}
        loading={Boolean(providers?.loading)}
        starting={redirecting}
        error={started?.error}
        magicLinkSent={Boolean(magic?.data)}
        magicLinkLoading={Boolean(magic?.loading)}
        magicLinkError={magic?.error}
        onSelectProvider={onSelectProvider}
        onSendMagicLink={onSendMagicLink}
        passwordLoading={Boolean(userSession?.login?.loading)}
        passwordError={userSession?.login?.error}
        onPasswordLogin={onPasswordLogin}
      />
    </LoginPanel>
  );
};

export default Login;
