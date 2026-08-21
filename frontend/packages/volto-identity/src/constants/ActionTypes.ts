/**
 * Action types for the identity add-on.
 *
 * Namespaced with the package name: Volto merges every add-on's reducers into
 * one store, and a bare name like `LOGIN` would collide sooner or later.
 * @module constants/ActionTypes
 */

export const LIST_LOGIN_PROVIDERS = 'IDENTITY_LIST_LOGIN_PROVIDERS';
export const START_PROVIDER_LOGIN = 'IDENTITY_START_PROVIDER_LOGIN';
export const COMPLETE_CALLBACK = 'IDENTITY_COMPLETE_CALLBACK';
export const SEND_MAGIC_LINK = 'IDENTITY_SEND_MAGIC_LINK';
export const CONFIRM_MAGIC_LINK = 'IDENTITY_CONFIRM_MAGIC_LINK';
