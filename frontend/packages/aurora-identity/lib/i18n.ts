/**
 * Translating `identity-core`'s messages with Aurora's i18next.
 *
 * The messages' source of truth is `identity-core`'s gettext catalogues,
 * which Volto reads as they are. For Aurora, `scripts/i18n.mjs` writes them
 * into this add-on's `locales/<lang>/common.json`, under one key, so Aurora
 * merges them into its own catalogue with every other add-on's.
 *
 * Their ids are English sentences, full of the `.` and `:` i18next would read
 * as key and namespace separators. So a lookup nests under `identity` with a
 * separator no sentence contains, and splits no namespace at all.
 * @module lib/i18n
 */
import { interpolate } from '@plone-collective/identity-core';
import type { Translate } from '@plone-collective/identity-core';

/** The key every message is filed under in `common.json`. */
export const CATALOGUE = 'identity';

/** Joins `CATALOGUE` to a message id: ASCII's unit separator. */
export const KEY_SEPARATOR = '\u001f';

/** The part of i18next's `t` this needs. */
type I18nextT = (
  key: string,
  options: {
    defaultValue: string;
    keySeparator: string;
    nsSeparator: false;
  },
) => string;

/**
 * Turn i18next's `t` into the translate function core components call.
 *
 * The placeholders are filled by core's `interpolate`, not by i18next, which
 * would look for `{{name}}` where the catalogues have `{name}`.
 *
 * @param t i18next's `t`, for the `common` namespace.
 * @param locale The reader's language, for the plural forms.
 * @returns The translate function.
 */
export function translateWith(t: I18nextT, locale = 'en'): Translate {
  return (message, values) =>
    interpolate(
      t(`${CATALOGUE}${KEY_SEPARATOR}${message.id}`, {
        defaultValue: message.defaultMessage,
        keySeparator: KEY_SEPARATOR,
        nsSeparator: false,
      }),
      values,
      locale,
    );
}
