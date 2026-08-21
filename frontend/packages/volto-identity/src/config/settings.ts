import type { ConfigType } from '@plone/registry';

declare module '@plone/types' {
  export interface SettingsConfig {
    /** Whether Plone's own username/password form is offered as well. */
    identityShowPloneLogin: boolean;
  }
}

export default function install(config: ConfigType) {
  // Off by default: a site installing this add-on has external providers,
  // and leaving the password form up next to them invites people to create a
  // second way into the same account.
  config.settings.identityShowPloneLogin = false;
  return config;
}
