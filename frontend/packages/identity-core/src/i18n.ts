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
 * Find where a `{` opened at `start` is closed, counting nested braces.
 *
 * @param text The message text.
 * @param start The index of the opening brace.
 * @returns The index of its closing brace, or -1 when it is never closed.
 */
function closing(text: string, start: number): number {
  let depth = 0;
  for (let index = start; index < text.length; index++) {
    if (text[index] === '{') {
      depth += 1;
    } else if (text[index] === '}') {
      depth -= 1;
      if (depth === 0) {
        return index;
      }
    }
  }
  return -1;
}

/**
 * Choose the branch of a `{count, plural, ...}` for a number.
 *
 * The ICU forms the catalogues use: `=N` for an exact number, then the
 * locale's plural category (`one`, `few`, `many`, ...), then `other`. In the
 * branch chosen, `#` is the number.
 *
 * @param body What follows `plural,` inside the braces.
 * @param count The number.
 * @param locale The reader's language, for its plural rules.
 * @returns The branch's text, or null when the body cannot be read.
 */
function pluralBranch(
  body: string,
  count: number,
  locale: string,
): string | null {
  const branches: Record<string, string> = {};
  let index = 0;
  while (index < body.length) {
    const open = body.indexOf('{', index);
    if (open < 0) {
      break;
    }
    const close = closing(body, open);
    if (close < 0) {
      return null;
    }
    branches[body.slice(index, open).trim()] = body.slice(open + 1, close);
    index = close + 1;
  }
  let category: string;
  try {
    category = new Intl.PluralRules(locale).select(count);
  } catch {
    category = new Intl.PluralRules('en').select(count);
  }
  const branch =
    branches[`=${count}`] ?? branches[category] ?? branches.other ?? null;
  return branch === null ? null : branch.replace(/#/g, String(count));
}

/**
 * Put each value into its `{placeholder}`.
 *
 * Plain placeholders, `{name}`, and plurals, `{count, plural, one {# field}
 * other {# fields}}`: the two kinds the catalogues hold. A placeholder
 * without a value is left as written, so a missing value shows rather than
 * vanishing.
 *
 * @param text The message text.
 * @param values The values.
 * @param locale The reader's language, for its plural rules.
 * @returns The text with every known placeholder replaced.
 */
export function interpolate(
  text: string,
  values?: MessageValues,
  locale = 'en',
): string {
  if (!values) {
    return text;
  }
  let result = '';
  let index = 0;
  while (index < text.length) {
    const plural = /\{\s*(\w+)\s*,\s*plural\s*,/g;
    plural.lastIndex = index;
    const found = plural.exec(text);
    if (!found) {
      break;
    }
    const close = closing(text, found.index);
    const name = found[1];
    const count = Number(values[name]);
    const branch =
      close >= 0 && name in values && !Number.isNaN(count)
        ? pluralBranch(text.slice(plural.lastIndex, close), count, locale)
        : null;
    result += text.slice(index, found.index);
    result +=
      branch ?? text.slice(found.index, close < 0 ? undefined : close + 1);
    index = close < 0 ? text.length : close + 1;
  }
  result += text.slice(index);
  return result.replace(/\{(\w+)\}/g, (placeholder, name: string) =>
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
