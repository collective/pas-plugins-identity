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
import { returnUrl } from '../../helpers/returnUrl';
import type { LoginProvider } from '../../types';
import LoginForm from './LoginForm';

const Login: React.FC = () => {
  const dispatch = useDispatch();
  const location = useLocation();
  const [redirecting, setRedirecting] = useState(false);

  const providers = useSelector((state: any) => state.loginProviders);
  const started = useSelector((state: any) => state.providerLogin);
  const magic = useSelector((state: any) => state.magicLinkSend);

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

  const onSendMagicLink = useCallback(
    (email: string) => {
      dispatch(sendMagicLink(email));
    },
    [dispatch],
  );

  return (
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
    />
  );
};

export default Login;
