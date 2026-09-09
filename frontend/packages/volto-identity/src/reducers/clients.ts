/**
 * Reducers for the OAuth clients registered against this site.
 * @module reducers/clients
 */

import {
  CREATE_CLIENT,
  DELETE_CLIENT,
  LIST_CLIENTS,
  ROTATE_CLIENT_SECRET,
  UPDATE_CLIENT,
} from '../constants/ActionTypes';
import type { OAuthClient, VoltoSchema } from '../types';
import { requestReducer } from './factory';

export const oauthClients = requestReducer<OAuthClient[]>(
  LIST_CLIENTS,
  (result) => result?.items ?? [],
  [],
);

export const clientFormSchema = requestReducer<VoltoSchema | null>(
  LIST_CLIENTS,
  (result) => result?.schema ?? null,
  null,
);

// The create and rotate results keep the *whole* client rather than a list
// entry, because they are the only place the secret ever appears and the
// panel has to render it from somewhere.
export const clientCreate = requestReducer<OAuthClient | null>(
  CREATE_CLIENT,
  (result) => result ?? null,
  null,
);

export const clientSecretRotate = requestReducer<OAuthClient | null>(
  ROTATE_CLIENT_SECRET,
  (result) => result ?? null,
  null,
);

export const clientUpdate = requestReducer<OAuthClient | null>(
  UPDATE_CLIENT,
  (result) => result ?? null,
  null,
);

export const clientDelete = requestReducer<boolean>(
  DELETE_CLIENT,
  () => true,
  false,
);
