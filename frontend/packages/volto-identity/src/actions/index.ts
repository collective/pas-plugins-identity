/**
 * Actions for the identity login flows.
 *
 * Every one of them is a plain Volto API action: the `request` key is picked
 * up by Volto's api middleware, which does the fetch and dispatches the
 * `_PENDING` / `_SUCCESS` / `_FAIL` triple.
 *
 * One module per domain, and this file is the re-export surface, so anything
 * importing from the package root is unaffected by where a given action
 * lives. Import from the domain module in new code; the domains are the same
 * ones `reducers/` uses.
 * @module actions
 */

export { getUserAccount } from './account';
export {
  createClient,
  deleteClient,
  listClients,
  rotateClientSecret,
  updateClient,
} from './clients';
export { getConsentRequest, listGrants, withdrawGrant } from './consent';
export { listDrivers } from './drivers';
export { listGroupMembers } from './groups';
export { listIdentities, startLinking, unlinkIdentity } from './identities';
export { listKeys, rotateKey } from './keys';
export {
  completeCallback,
  listLoginProviders,
  startProviderLogin,
} from './login';
export { confirmMagicLink, sendMagicLink } from './magiclink';
export { getMyProfile, getUserProfile, setPreferredEmail } from './profile';
export {
  createProvider,
  deleteProvider,
  listProviders,
  testProvider,
  updateProvider,
} from './providers';
