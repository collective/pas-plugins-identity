import { describe, expect, it } from 'vitest';

import {
  cellText,
  newRowId,
  reorderedRows,
  rowKeys,
  withRowIds,
} from './orderedList';

describe('rowKeys', () => {
  it('keys an entry by its @id', () => {
    expect(rowKeys([{ '@id': 'a' }, { '@id': 'b' }])).toEqual(['a', 'b']);
  });

  it('keys an entry without one by what it holds', () => {
    // A string list's entries: nothing else to key them by.
    expect(rowKeys([{ value: 'x' }, { value: 'y' }])).toEqual([
      '#{"value":"x"}',
      '#{"value":"y"}',
    ]);
  });

  it('keeps an entry its key when the list is reordered', () => {
    // A position key would move to whichever entry took the place, and the
    // table keeps focus and tells a screen reader what moved by key.
    const [x, y] = rowKeys([{ value: 'x' }, { value: 'y' }]);

    expect(rowKeys([{ value: 'y' }, { value: 'x' }])).toEqual([y, x]);
  });

  it('tells repeats apart, so no two rows share a key', () => {
    expect(rowKeys([{ value: 'x' }, { value: 'x' }])).toEqual([
      '#{"value":"x"}',
      '#{"value":"x"}~2',
    ]);
    expect(rowKeys([{ '@id': 'a' }, { '@id': 'a' }])).toEqual([
      'a',
      '#{"@id":"a"}',
    ]);
  });
});

describe('reorderedRows', () => {
  const rows = [{ '@id': 'a' }, { '@id': 'b' }, { '@id': 'c' }];

  it('puts the dragged entry before the target', () => {
    expect(reorderedRows(rows, ['c'], 'a', 'before')).toEqual([
      { '@id': 'c' },
      { '@id': 'a' },
      { '@id': 'b' },
    ]);
  });

  it('puts the dragged entry after the target', () => {
    expect(reorderedRows(rows, ['a'], 'c', 'after')).toEqual([
      { '@id': 'b' },
      { '@id': 'c' },
      { '@id': 'a' },
    ]);
  });

  it('moves several, keeping their order', () => {
    expect(reorderedRows(rows, ['c', 'a'], 'b', 'after')).toEqual([
      { '@id': 'b' },
      { '@id': 'a' },
      { '@id': 'c' },
    ]);
  });

  it('moves entries keyed by what they hold', () => {
    const strings = [{ value: 'x' }, { value: 'y' }];
    const [x, y] = rowKeys(strings);

    expect(reorderedRows(strings, [y], x, 'before')).toEqual([
      { value: 'y' },
      { value: 'x' },
    ]);
  });

  it('reads a drop on an entry as before it', () => {
    expect(reorderedRows(rows, ['c'], 'b', 'on')).toEqual([
      { '@id': 'a' },
      { '@id': 'c' },
      { '@id': 'b' },
    ]);
  });

  it('is null for a drop that changes nothing', () => {
    expect(reorderedRows(rows, ['b'], 'b', 'before')).toBeNull();
    expect(reorderedRows(rows, ['a'], 'b', 'before')).toBeNull();
    expect(reorderedRows(rows, ['b'], 'a', 'after')).toBeNull();
  });

  it('is null for a key the list does not have', () => {
    expect(reorderedRows(rows, ['b'], 'z', 'before')).toBeNull();
    expect(reorderedRows(rows, ['z'], 'a', 'before')).toBeNull();
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
