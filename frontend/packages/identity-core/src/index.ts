/**
 * What the Volto and Aurora frontends of `pas.plugins.identity` share.
 *
 * Nothing in this package may import a frontend framework: not Volto, not
 * Aurora, not Redux, not a router, and not an i18n library. Its components
 * use React, `react-aria-components` and `@plone/components`, which both
 * frontends have, and take what differs between them -- translating,
 * linking, icons -- from an `IdentityUIProvider` each frontend's add-on
 * supplies.
 * @module identity-core
 */

// The tokens and base classes every component below reads.
import './styles.css';

export { default as CallbackCard } from './components/Callback/CallbackCard';
export type {
  CallbackCardProps,
  CallbackFailure,
} from './components/Callback/CallbackCard';
export { default as CompleteProfileCard } from './components/CompleteProfile/CompleteProfileCard';
export type { CompleteProfileCardProps } from './components/CompleteProfile/CompleteProfileCard';
export { default as ConfirmEmailCard } from './components/ConfirmEmail/ConfirmEmailCard';
export type {
  ConfirmEmailCardProps,
  ConfirmEmailStatus,
} from './components/ConfirmEmail/ConfirmEmailCard';
export { default as IdentitiesList } from './components/Identities/IdentitiesList';
export { default as ProfileEmails } from './components/Identities/ProfileEmails';
export { default as LoginCard } from './components/Login/LoginCard';
export type { LoginCardProps } from './components/Login/LoginCard';
export { default as LoginForm } from './components/Login/LoginForm';
export type { LoginFormProps } from './components/Login/LoginForm';
export {
  default as LoginOverlay,
  useDismissibleError,
} from './components/Login/LoginOverlay';
export { default as MagicLinkForm } from './components/Login/MagicLinkForm';
export { default as PasswordForm } from './components/Login/PasswordForm';
export { default as ProviderButton } from './components/Login/ProviderButton';
export * from './components/IdentityUI/IdentityUI';
export * from './constants/vocabularies';
export * from './endpoints';
export * from './helpers/avatar';
export * from './helpers/callback';
export * from './helpers/download';
export * from './helpers/firstLogin';
export * from './helpers/groupmap';
export * from './helpers/identities';
export * from './helpers/loginSettings';
export * from './helpers/navigate';
export * from './helpers/orderedList';
export * from './helpers/profileGate';
export * from './helpers/profileSource';
export * from './helpers/propertymap';
export * from './helpers/providerOrder';
export * from './helpers/returnUrl';
export * from './helpers/rowmap';
export * from './helpers/token';
export * from './helpers/welcome';
export * from './i18n';
export * from './types';

/**
 * Leave the configuration as it is.
 *
 * Volto transpiles only the packages registered as add-ons, and this package
 * ships TypeScript source, so `volto-identity` registers it as one. Volto
 * then requires every add-on to default-export a configuration function.
 * Aurora does not register it, and never calls this.
 *
 * @param config The frontend's configuration registry.
 * @returns The same configuration, unchanged.
 */
export default function applyConfig<T>(config: T): T {
  return config;
}
