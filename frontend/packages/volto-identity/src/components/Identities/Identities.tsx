/**
 * Identities container: the linking UI in user settings.
 * @module components/Identities/Identities
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useLocation } from 'react-router-dom';

import {
  listIdentities,
  listLoginProviders,
  startLinking,
  unlinkIdentity,
} from '../../actions';
import { linkable } from '../../helpers/identities';
import type { Identity, LoginProvider } from '../../types';
import IdentitiesList from './IdentitiesList';

const Identities: React.FC = () => {
  const dispatch = useDispatch();
  const location = useLocation();
  const [redirecting, setRedirecting] = useState(false);

  const mine = useSelector((state: any) => state.identities);
  const offered = useSelector((state: any) => state.loginProviders);
  const linking = useSelector((state: any) => state.identityLinking);
  const removing = useSelector((state: any) => state.identityUnlink);

  useEffect(() => {
    dispatch(listIdentities());
    dispatch(listLoginProviders());
  }, [dispatch]);

  useEffect(() => {
    if (redirecting && linking?.loaded && linking?.data?.authorize_url) {
      window.location.href = linking.data.authorize_url;
    }
  }, [redirecting, linking]);

  useEffect(() => {
    if (removing?.loaded) {
      // The list is stale the moment an unlink succeeds, and can_unlink may
      // have changed for everything left.
      dispatch(listIdentities());
    }
  }, [dispatch, removing?.loaded]);

  const onLink = useCallback(
    (provider: LoginProvider) => {
      setRedirecting(true);
      dispatch(startLinking(provider.id, location.pathname));
    },
    [dispatch, location.pathname],
  );

  const onUnlink = useCallback(
    (identity: Identity) => {
      dispatch(unlinkIdentity(identity.provider, identity.subject));
    },
    [dispatch],
  );

  return (
    <IdentitiesList
      identities={mine?.data ?? []}
      available={linkable(offered?.data ?? [], mine?.data ?? [])}
      loading={Boolean(mine?.loading)}
      busy={redirecting || Boolean(removing?.loading)}
      error={linking?.error ?? removing?.error}
      onLink={onLink}
      onUnlink={onUnlink}
    />
  );
};

export default Identities;
