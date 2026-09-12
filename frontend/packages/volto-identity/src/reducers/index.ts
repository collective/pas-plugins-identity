/**
 * Reducers for the identity login flows.
 *
 * One module per domain, matching `actions/`, with the request-lifecycle
 * factory they are all built from in `factory.ts`. This file is the
 * re-export surface and the map Volto installs, so nothing importing from the
 * package root has to know where a slice lives.
 *
 * `requestReducer` is deliberately not re-exported here. It was private to
 * this module before the split and it stays private to the package: every
 * export of this file is a reducer, which is what lets `reducers.test.ts`
 * assert that the map registers all of them.
 * @module reducers
 */

import { userAccount } from './account';
import {
  clientCreate,
  clientDelete,
  clientFormSchema,
  clientSecretRotate,
  clientUpdate,
  oauthClients,
} from './clients';
import { consentRequest, grantWithdraw, oauthGrants } from './consent';
import { identityDrivers } from './drivers';
import { groupMembers } from './groups';
import {
  identities,
  identityLinking,
  identityUnlink,
  linkableProviders,
} from './identities';
import { keyRotate, signingKeys } from './keys';
import { identityCallback, loginProviders, providerLogin } from './login';
import { magicLinkConfirm, magicLinkSend } from './magiclink';
import {
  emailConfirmation,
  myProfile,
  preferredEmail,
  userProfile,
} from './profile';
import {
  configuredProviders,
  providerCreate,
  providerDelete,
  providerFormSchema,
  providerReorder,
  providerTest,
  providersExportable,
  providerUpdate,
} from './providers';

export { userAccount } from './account';
export {
  clientCreate,
  clientDelete,
  clientFormSchema,
  clientSecretRotate,
  clientUpdate,
  oauthClients,
} from './clients';
export { consentRequest, grantWithdraw, oauthGrants } from './consent';
export { identityDrivers } from './drivers';
export { groupMembers } from './groups';
export {
  identities,
  identityLinking,
  identityUnlink,
  linkableProviders,
} from './identities';
export { keyRotate, signingKeys } from './keys';
export { identityCallback, loginProviders, providerLogin } from './login';
export { magicLinkConfirm, magicLinkSend } from './magiclink';
export {
  emailConfirmation,
  myProfile,
  preferredEmail,
  userProfile,
} from './profile';
export {
  configuredProviders,
  providerCreate,
  providerDelete,
  providerFormSchema,
  providerReorder,
  providerTest,
  providersExportable,
  providerUpdate,
} from './providers';

const reducers = {
  loginProviders,
  providerLogin,
  identityCallback,
  magicLinkSend,
  magicLinkConfirm,
  identities,
  linkableProviders,
  groupMembers,
  userAccount,
  identityLinking,
  identityUnlink,
  identityDrivers,
  configuredProviders,
  providerFormSchema,
  providersExportable,
  clientFormSchema,
  providerCreate,
  providerUpdate,
  providerReorder,
  providerDelete,
  providerTest,
  myProfile,
  preferredEmail,
  emailConfirmation,
  userProfile,
  oauthClients,
  clientCreate,
  clientUpdate,
  clientDelete,
  clientSecretRotate,
  signingKeys,
  keyRotate,
  consentRequest,
  oauthGrants,
  grantWithdraw,
};

export default reducers;
