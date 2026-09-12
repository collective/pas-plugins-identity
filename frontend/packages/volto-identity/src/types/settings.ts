/**
 * The add-on's own frontend settings, as `config.settings.identity`.
 *
 * Declared with the package's other types rather than beside the install step
 * that fills in their defaults, `config/settings.ts`. The augmentation at the
 * end is what types `config.settings.identity` for everything reading it,
 * including a project's own configuration.
 * @module types/settings
 */

/** Every frontend setting this add-on reads, as `config.settings.identity`. */
export interface IdentitySettings {
  /**
   * Whether Plone's own username/password form is offered as well.
   *
   * Only the default: `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` overrides it at run
   * time.
   */
  showPloneLogin: boolean;
  /**
   * Whether `/login` starts the sign-in straight away when the only way in is
   * one provider.
   *
   * Only the default: `RAZZLE_IDENTITY_REDIRECT_TO_SOLE_PROVIDER` overrides it
   * at run time. Even when on, the page shows the button to a visitor who
   * arrived signed in, or who asked to choose with `?choose`.
   */
  redirectToSoleProvider: boolean;
  /**
   * The palette a user's initials are drawn on when they have no portrait.
   *
   * The shipped one is chosen for contrast against the white initials. One a
   * project supplies is not checked, and an empty list means the shipped one.
   */
  avatarColors: string[];
}

declare module '@plone/types' {
  export interface SettingsConfig {
    identity: IdentitySettings;
  }
}
