/**
 * Messages, declared without an i18n library.
 *
 * Components in this package declare what they say with `defineMessages`
 * from here, and read the translate function a frontend provides through
 * `IdentityUIProvider`. Volto passes `react-intl`'s `formatMessage`, Aurora
 * passes i18next's `t`.
 *
 * Import it as `#i18n`, never by a relative path. The message extractor
 * recognises a `defineMessages` call by the module it was imported from, and
 * `#i18n` is the one name that stays the same from every file. The package's
 * `babel.config.js` tells the extractor so.
 * @module i18n
 */

/** A message: the id it is translated under, and its English text. */
export interface MessageDescriptor {
  id: string;
  defaultMessage: string;
}

/** Values to put into a message's `{placeholder}`s. */
export type MessageValues = Record<string, string | number>;

/** Turn a message into text in the reader's language. */
export type Translate = (
  message: MessageDescriptor,
  values?: MessageValues,
) => string;

/**
 * Declare a component's messages.
 *
 * Does nothing at runtime. It exists so the extractor can find the messages.
 *
 * @param messages The messages, keyed by the name the component uses.
 * @returns The same messages.
 */
export function defineMessages<T extends Record<string, MessageDescriptor>>(
  messages: T,
): T {
  return messages;
}

/**
 * Put each value into its `{placeholder}`.
 *
 * A placeholder without a value is left as written, so a missing value
 * shows rather than vanishing.
 *
 * @param text The message text.
 * @param values The values.
 * @returns The text with every known placeholder replaced.
 */
export function interpolate(text: string, values?: MessageValues): string {
  if (!values) {
    return text;
  }
  return text.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
    name in values ? String(values[name]) : placeholder,
  );
}

/**
 * Say every message in English.
 *
 * What a component says when no frontend has provided a translate function.
 *
 * @param message The message.
 * @param values Values for its placeholders.
 * @returns The English text.
 */
export const translateDefault: Translate = (message, values) =>
  interpolate(message.defaultMessage, values);
