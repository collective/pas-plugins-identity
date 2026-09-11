/**
 * Reducers for the providers this site lets people sign in with.
 * @module reducers/providers
 */

import {
  CREATE_PROVIDER,
  DELETE_PROVIDER,
  LIST_PROVIDERS,
  REORDER_PROVIDERS,
  TEST_PROVIDER,
  UPDATE_PROVIDER,
} from '../constants/ActionTypes';
import type {
  ConfiguredProvider,
  ConnectionCheck,
  VoltoSchema,
} from '../types';
import { requestReducer } from './factory';

export const configuredProviders = requestReducer<ConfiguredProvider[]>(
  LIST_PROVIDERS,
  (result) => result?.items ?? [],
  [],
);

// The provider form's own schema, served beside the listing. Its own slice
// rather than a field on `configuredProviders`, because the panel asks for it
// on mount and Volto's `Form` reads `schema.fieldsets` on the first render --
// a listing that arrived without one would crash rather than render empty.
export const providerFormSchema = requestReducer<VoltoSchema | null>(
  LIST_PROVIDERS,
  (result) => result?.schema ?? null,
  null,
);

export const providerCreate = requestReducer<ConfiguredProvider | null>(
  CREATE_PROVIDER,
  (result) => result ?? null,
  null,
);

export const providerUpdate = requestReducer<boolean>(
  UPDATE_PROVIDER,
  () => true,
  false,
);

export const providerReorder = requestReducer<boolean>(
  REORDER_PROVIDERS,
  () => true,
  false,
);

export const providerDelete = requestReducer<boolean>(
  DELETE_PROVIDER,
  () => true,
  false,
);

export const providerTest = requestReducer<ConnectionCheck | null>(
  TEST_PROVIDER,
  (result) => result ?? null,
  null,
);
