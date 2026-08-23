/**
 * Control-panel container: store and dispatch around the panel.
 * @module components/ControlPanel/ProvidersControlPanel
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';

import {
  createProvider,
  deleteProvider,
  listDrivers,
  listProviders,
  testProvider,
  updateProvider,
} from '../../actions';
import ProvidersPanel from './ProvidersPanel';

const ProvidersControlPanel: React.FC = () => {
  const dispatch = useDispatch();
  const [checking, setChecking] = useState<string | null>(null);

  const providers = useSelector((state: any) => state.configuredProviders);
  const drivers = useSelector((state: any) => state.identityDrivers);
  const made = useSelector((state: any) => state.providerCreate);
  const saved = useSelector((state: any) => state.providerUpdate);
  const removed = useSelector((state: any) => state.providerDelete);
  const check = useSelector((state: any) => state.providerTest);

  useEffect(() => {
    dispatch(listProviders());
    dispatch(listDrivers());
  }, [dispatch]);

  useEffect(() => {
    if (made?.loaded || saved?.loaded || removed?.loaded) {
      // Re-read rather than patch the local copy: the backend re-masks the
      // config on the way out, and a locally patched copy would hold the
      // plaintext secret the operator just typed.
      dispatch(listProviders());
    }
  }, [dispatch, made?.loaded, saved?.loaded, removed?.loaded]);

  const onCreate = useCallback(
    (data: Record<string, unknown>) => {
      dispatch(createProvider(data));
    },
    [dispatch],
  );

  const onSave = useCallback(
    (providerId: string, data: Record<string, unknown>) => {
      dispatch(updateProvider(providerId, data));
    },
    [dispatch],
  );

  const onDelete = useCallback(
    (providerId: string) => {
      dispatch(deleteProvider(providerId));
    },
    [dispatch],
  );

  const onTest = useCallback(
    (providerId: string) => {
      setChecking(providerId);
      dispatch(testProvider(providerId));
    },
    [dispatch],
  );

  return (
    <ProvidersPanel
      providers={providers?.data ?? []}
      drivers={drivers?.data ?? []}
      loading={Boolean(providers?.loading || drivers?.loading)}
      busy={Boolean(made?.loading || saved?.loading || removed?.loading)}
      check={check?.data}
      checking={checking}
      onCreate={onCreate}
      onSave={onSave}
      onDelete={onDelete}
      onTest={onTest}
    />
  );
};

export default ProvidersControlPanel;
