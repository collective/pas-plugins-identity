import type { ConfigType } from '@plone/registry';
import ProfileGate from '../components/ProfileGate/ProfileGate';
import { DEFAULT_AVATAR_COLORS } from '../helpers/avatar';

// `IdentitySettings`, the type of what `install` fills in below, is declared
// in `types/settings`.

/**
 * Read a boolean out of the environment.
 *
 * Only the words are accepted, and anything unset falls back to the default.
 * Deliberately not `Boolean(value)`: that reads the string `"false"` as true,
 * which turns an operator switching the password form *off* into a site that
 * still shows it.
 *
 * @param value The raw environment value.
 * @param fallback What an unset variable means.
 * @returns The decision.
 */
export function asBoolean(
  value: string | undefined,
  fallback: boolean,
): boolean {
  if (value === undefined || value === '') {
    return fallback;
  }
  return ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase());
}

export default function install(config: ConfigType) {
  // Off by default: a site installing this add-on has external providers,
  // and leaving the password form up next to them invites people to create a
  // second way into the same account.
  //
  // An identity provider built on this package is the case that wants it on:
  // its users *are* local, and it is the site people sign in to in order to
  // sign in elsewhere.
  //
  // **This is only the default.** The deployment answer is
  // `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN`, read at *run* time by the Login
  // component -- see `showPloneLogin` there. It is not read here, and that is
  // the whole point: written out literally, `process.env.RAZZLE_...` is
  // substituted into the browser bundle by webpack's DefinePlugin while
  // `pnpm build` runs, which makes the value a property of the image. Two
  // sites wanting two answers then need two images.
  //
  // A project that wants a different default overrides
  // `config.settings.identity.showPloneLogin` in its own configuration, and
  // the environment still wins over it.
  //
  // The sole-provider redirect is on by default, which is what the login page
  // did before it was a setting: one provider and nothing else is a page with
  // one button on it. A site turns it off with
  // `RAZZLE_IDENTITY_REDIRECT_TO_SOLE_PROVIDER`, read at run time the same way
  // -- see `redirectToSoleProvider`.
  //
  // Merged under whatever is already there rather than assigned: an add-on
  // configured before this one may have set a palette, and these are defaults.
  // The palette is a copy, so a project pushing onto it does not change the
  // shipped one for everybody else in the process.
  config.settings.identity = {
    showPloneLogin: false,
    redirectToSoleProvider: true,
    avatarColors: [...DEFAULT_AVATAR_COLORS],
    ...config.settings.identity,
  };

  // `@my-profile` rides on the content request rather than costing one of its
  // own. The gate asks on every navigation, and a navigation to a content
  // route is already a request -- so this turns two round trips into one for
  // every signed-in page view.
  //
  // It is sent for anonymous visitors too, and that is not an oversight:
  // `addExpandersToPath` receives `isAnonymous` but the filter using it is a
  // hardcoded list of `types` and `translations`, so an entry here cannot
  // declare itself authenticated-only. The backend component answers an
  // anonymous caller with nothing at all, which leaves a public site's payload
  // exactly as it was. The parameter still rides on anonymous content URLs; it
  // is constant, so it moves the cache key once rather than splitting it.
  config.settings.apiExpanders = [
    ...(config.settings.apiExpanders ?? []),
    { match: '', GET_CONTENT: ['my-profile'] },
  ];

  // The required-information gate, on every route.
  //
  // The backend has one too, and it lets `plone.restapi` requests through on
  // purpose: Volto fetches the edit form over the API, so gating those would
  // break the page the user is being sent to. Every navigation in this app is
  // such a request, which means the backend gate never fires here and this is
  // the one that does.
  //
  // An empty `match` mounts it everywhere, which is the point: a gate that
  // only covers some routes is a list of ways around it.
  config.settings.appExtras = [
    ...(config.settings.appExtras ?? []),
    // `props` is empty and still spelled out: `AppExtras` spreads it, so
    // omitting it renders the same, but Volto's `Settings.d.ts` declares it
    // required and the gate is the only entry this add-on adds.
    { match: '', component: ProfileGate, props: {} },
  ];
  return config;
}
