import { describe, expect, it } from 'vitest';

import {
  cellText,
  movedRows,
  newRowId,
  rowKeys,
  withRowIds,
} from './orderedList';

describe('rowKeys', () => {
  it('keys an entry by its @id', () => {
    expect(rowKeys([{ '@id': 'a' }, { '@id': 'b' }])).toEqual(['a', 'b']);
  });

  it('keys an entry without one by its position', () => {
    // A string list's entries: nothing to key them by but where they are.
    expect(rowKeys([{ value: 'x' }, { value: 'y' }])).toEqual(['#0', '#1']);
  });

  it('keys a repeated @id by position, so no two rows share a key', () => {
    expect(rowKeys([{ '@id': 'a' }, { '@id': 'a' }])).toEqual(['a', '#1']);
  });
});

describe('movedRows', () => {
  const rows = [{ '@id': 'a' }, { '@id': 'b' }, { '@id': 'c' }];

  it("puts the dragged entry in the target's place", () => {
    expect(movedRows(rows, 'c', 'a')).toEqual([
      { '@id': 'c' },
      { '@id': 'a' },
      { '@id': 'b' },
    ]);
  });

  it('moves entries keyed by position', () => {
    expect(movedRows([{ value: 'x' }, { value: 'y' }], '#1', '#0')).toEqual([
      { value: 'y' },
      { value: 'x' },
    ]);
  });

  it('is null for a drop that changes nothing', () => {
    expect(movedRows(rows, 'b', 'b')).toBeNull();
    expect(movedRows(rows, 'b', null)).toBeNull();
  });
});

describe('newRowId', () => {
  it('is a version 4 UUID', () => {
    expect(newRowId()).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
  });

  it('is different every time', () => {
    expect(newRowId()).not.toBe(newRowId());
  });
});

describe('withRowIds', () => {
  it('gives an entry without an @id one', () => {
    const [row] = withRowIds([{ title: 'Blog' }]);

    expect(row.title).toBe('Blog');
    expect(typeof row['@id']).toBe('string');
  });

  it('leaves an entry that has one as it was', () => {
    const row = { '@id': 'a', title: 'Blog' };

    expect(withRowIds([row])[0]).toBe(row);
  });
});

describe('cellText', () => {
  const network = {
    title: 'Network',
    choices: [
      ['github', 'GitHub'],
      ['mastodon', 'Mastodon'],
    ],
  };

  it('is empty for a value that is not there', () => {
    expect(cellText(undefined, undefined)).toBe('');
    expect(cellText(undefined, null)).toBe('');
    expect(cellText(undefined, '')).toBe('');
  });

  it('shows a choice by its label', () => {
    expect(cellText(network, 'github')).toBe('GitHub');
  });

  it('shows a token no choice has as the token', () => {
    expect(cellText(network, 'myspace')).toBe('myspace');
  });

  it('shows a picked link by its title, or its @id without one', () => {
    // What the object browser stores for a link: a list of one object.
    expect(
      cellText(undefined, [{ '@id': 'https://x.org', title: 'x.org' }]),
    ).toBe('x.org');
    expect(cellText(undefined, [{ '@id': 'https://x.org' }])).toBe(
      'https://x.org',
    );
  });

  it('joins a list', () => {
    expect(cellText(network, ['github', 'mastodon'])).toBe('GitHub, Mastodon');
  });

  it('shows anything else as text', () => {
    expect(cellText(undefined, 3)).toBe('3');
  });
});
