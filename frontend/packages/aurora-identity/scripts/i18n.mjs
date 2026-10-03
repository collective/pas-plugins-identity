/**
 * Write this add-on's i18next catalogues from `identity-core`'s gettext ones.
 *
 * Run with `pnpm i18n`, after `identity-core`'s own `pnpm i18n`. The output
 * is committed: Aurora reads `locales/<lang>/common.json` from an add-on at
 * startup and does not run this. `make ci-i18n` in the Aurora harness fails
 * when the committed files are behind.
 */
import fs from 'node:fs';
import path from 'node:path';

import { i18nextLanguage, readPo, toCommonJson } from './po.mjs';

// Kept equal to `CATALOGUE` in lib/i18n.ts, which reads what this writes.
const CATALOGUE = 'identity';

const here = path.dirname(new URL(import.meta.url).pathname);
const source = path.resolve(here, '..', '..', 'identity-core', 'locales');
const target = path.resolve(here, '..', 'locales');

const languages = fs
  .readdirSync(source, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .sort();

for (const language of languages) {
  const po = path.join(source, language, 'LC_MESSAGES', 'volto.po');
  if (!fs.existsSync(po)) {
    continue;
  }
  const entries = readPo(fs.readFileSync(po, 'utf-8'));
  const directory = path.join(target, i18nextLanguage(language));
  fs.mkdirSync(directory, { recursive: true });
  fs.writeFileSync(
    path.join(directory, 'common.json'),
    toCommonJson(entries, CATALOGUE),
  );
  console.log(
    `${i18nextLanguage(language)}: ${Object.keys(entries).length} messages`,
  );
}
