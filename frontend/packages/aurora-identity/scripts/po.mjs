/**
 * Reading gettext catalogues into Aurora's i18next ones.
 *
 * `identity-core`'s `.po` files are the messages' one source of truth:
 * Volto reads them as they are, and these functions turn them into the
 * `common.json` Aurora merges. Plain JavaScript, so `scripts/i18n.mjs` runs
 * with Node alone.
 * @module scripts/po
 */

/**
 * Undo a `.po` string's escapes.
 *
 * @param {string} text The text between the quotes.
 * @returns {string} The text it stands for.
 */
function unescape(text) {
  return text.replace(/\\(["\\nt])/g, (_, char) =>
    char === 'n' ? '\n' : char === 't' ? '\t' : char,
  );
}

/**
 * Read a `.po` file's translations.
 *
 * The header entry (empty `msgid`) and untranslated entries are left out:
 * an empty translation would hide the English text i18next falls back to.
 * Strings continued over several lines are joined.
 *
 * @param {string} source The `.po` file's text.
 * @returns {Record<string, string>} Each translated id, mapped to its
 *   translation.
 */
export function readPo(source) {
  const entries = {};
  let field = null;
  let current = { msgid: '', msgstr: '' };

  const flush = () => {
    if (current.msgid && current.msgstr) {
      entries[current.msgid] = current.msgstr;
    }
    current = { msgid: '', msgstr: '' };
    field = null;
  };

  for (const raw of source.split(/\r?\n/)) {
    const line = raw.trim();
    const keyword = /^(msgid|msgstr)\s+"(.*)"$/.exec(line);
    if (keyword) {
      if (keyword[1] === 'msgid' && field === 'msgstr') {
        flush();
      }
      field = keyword[1];
      current[field] = unescape(keyword[2]);
    } else if (field && /^".*"$/.test(line)) {
      current[field] += unescape(line.slice(1, -1));
    } else if (line === '' || line.startsWith('#')) {
      if (field === 'msgstr') {
        flush();
      }
    }
  }
  flush();
  return entries;
}

/**
 * The name i18next gives a gettext language.
 *
 * gettext writes a region with an underscore, i18next with a hyphen:
 * `pt_BR` is `pt-BR`.
 *
 * @param {string} language The gettext language.
 * @returns {string} The i18next language.
 */
export function i18nextLanguage(language) {
  return language.replace('_', '-');
}

/**
 * Build a `common.json` holding a catalogue's translations.
 *
 * Under one key, sorted, so Aurora's merge cannot collide with another
 * add-on's keys and a regenerated file differs only where a translation did.
 *
 * @param {Record<string, string>} entries What `readPo` read.
 * @param {string} catalogue The key to file them under.
 * @returns {string} The file's text.
 */
export function toCommonJson(entries, catalogue) {
  const sorted = Object.fromEntries(
    Object.keys(entries)
      .sort()
      .map((id) => [id, entries[id]]),
  );
  return `${JSON.stringify({ [catalogue]: sorted }, null, 2)}\n`;
}
