import { describe, expect, it } from 'vitest';

import { i18nextLanguage, readPo, toCommonJson } from './po.mjs';

const PO = `msgid ""
msgstr ""
"Language: de\\n"
"Content-Type: text/plain; charset=utf-8\\n"

#. Default: "Password"
#: components/Login/PasswordForm
msgid "Password"
msgstr "Passwort"

#: components/Login/LoginForm
msgid "Taking you to {provider}…"
msgstr "Sie werden zu {provider} geleitet…"

#: components/Login/LoginOverlay
msgid "Close"
msgstr ""

msgid "A long message "
"over two lines"
msgstr "Eine lange Nachricht "
"über zwei Zeilen"

msgid "Say \\"hello\\""
msgstr "Sag \\"hallo\\""
`;

describe('readPo', () => {
  const entries = readPo(PO);

  it('reads each translation under its id', () => {
    expect(entries.Password).toBe('Passwort');
    expect(entries['Taking you to {provider}…']).toBe(
      'Sie werden zu {provider} geleitet…',
    );
  });

  it('leaves out the header and untranslated entries', () => {
    expect(entries['']).toBeUndefined();
    expect('Close' in entries).toBe(false);
  });

  it('joins a string continued over several lines', () => {
    expect(entries['A long message over two lines']).toBe(
      'Eine lange Nachricht über zwei Zeilen',
    );
  });

  it('undoes escapes', () => {
    expect(entries['Say "hello"']).toBe('Sag "hallo"');
  });

  it('reads nothing else', () => {
    expect(Object.keys(entries)).toHaveLength(4);
  });
});

describe('i18nextLanguage', () => {
  it('writes a region the way i18next does', () => {
    expect(i18nextLanguage('pt_BR')).toBe('pt-BR');
    expect(i18nextLanguage('de')).toBe('de');
  });
});

describe('toCommonJson', () => {
  it('files the messages under one key, sorted', () => {
    expect(JSON.parse(toCommonJson({ b: '2', a: '1' }, 'identity'))).toEqual({
      identity: { a: '1', b: '2' },
    });
    expect(toCommonJson({ b: '2', a: '1' }, 'identity')).toBe(
      '{\n  "identity": {\n    "a": "1",\n    "b": "2"\n  }\n}\n',
    );
  });
});
