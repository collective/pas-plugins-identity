/**
 * Control-panel container: store and dispatch around the clients panel.
 * @module components/ControlPanel/ClientsControlPanel
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';

import {
  createClient,
  deleteClient,
  listClients,
  listKeys,
  rotateClientSecret,
  rotateKey,
  updateClient,
} from '../../actions';
import ClientsPanel from './ClientsPanel';
import type { OAuthClient } from '../../types';

const ClientsControlPanel: React.FC = () => {
  const dispatch = useDispatch();
  // Held here rather than read from the store on every render: the secret
  // must survive the re-listing that follows a create, and it must disappear
  // when the operator says they have saved it rather than when some other
  // request happens to resolve.
  const [minted, setMinted] = useState<OAuthClient | null>(null);

  const clients = useSelector((state: any) => state.oauthClients);
  const keys = useSelector((state: any) => state.signingKeys);
  const created = useSelector((state: any) => state.clientCreate);
  const rotated = useSelector((state: any) => state.clientSecretRotate);
  const updated = useSelector((state: any) => state.clientUpdate);
  const removed = useSelector((state: any) => state.clientDelete);
  const keyRotated = useSelector((state: any) => state.keyRotate);

  useEffect(() => {
    dispatch(listClients());
    dispatch(listKeys());
  }, [dispatch]);

  useEffect(() => {
    if (created?.loaded || updated?.loaded || removed?.loaded) {
      // Re-read rather than patch the local copy: the listing never carries
      // the secret, and a locally patched entry would.
      dispatch(listClients());
    }
  }, [dispatch, created?.loaded, updated?.loaded, removed?.loaded]);

  useEffect(() => {
    if (keyRotated?.loaded) {
      dispatch(listKeys());
    }
  }, [dispatch, keyRotated?.loaded]);

  useEffect(() => {
    const answer = created?.loaded ? created.data : null;
    if (answer?.secret) {
      setMinted(answer);
    }
  }, [created?.loaded, created?.data]);

  useEffect(() => {
    const answer = rotated?.loaded ? rotated.data : null;
    if (answer?.secret) {
      setMinted(answer);
    }
  }, [rotated?.loaded, rotated?.data]);

  const onCreate = useCallback(
    (data: Record<string, unknown>) => {
      dispatch(createClient(data));
    },
    [dispatch],
  );

  const onToggle = useCallback(
    (clientId: string, enabled: boolean) => {
      dispatch(updateClient(clientId, { enabled }));
    },
    [dispatch],
  );

  const onRotateSecret = useCallback(
    (clientId: string) => {
      dispatch(rotateClientSecret(clientId));
    },
    [dispatch],
  );

  const onDelete = useCallback(
    (clientId: string) => {
      dispatch(deleteClient(clientId));
    },
    [dispatch],
  );

  const onRotateKey = useCallback(() => {
    dispatch(rotateKey());
  }, [dispatch]);

  const onDismissSecret = useCallback(() => setMinted(null), []);

  return (
    <ClientsPanel
      clients={clients?.data ?? []}
      keys={keys?.data ?? null}
      loading={Boolean(clients?.loading)}
      busy={Boolean(
        created?.loading ||
          updated?.loading ||
          removed?.loading ||
          rotated?.loading ||
          keyRotated?.loading,
      )}
      minted={minted}
      onCreate={onCreate}
      onToggle={onToggle}
      onRotateSecret={onRotateSecret}
      onDelete={onDelete}
      onRotateKey={onRotateKey}
      onDismissSecret={onDismissSecret}
    />
  );
};

export default ClientsControlPanel;
