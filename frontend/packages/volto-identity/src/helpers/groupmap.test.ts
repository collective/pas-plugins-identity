import { describe, expect, it } from 'vitest';

import { fromGroupRows, toGroupRows } from './groupmap';

describe('toGroupRows', () => {
  it('turns a map into rows', () => {
    expect(toGroupRows({ editors: 'site-editors' })).toEqual([
      { '@id': expect.any(String), group: 'editors', local: 'site-editors' },
    ]);
  });

  it('gives every row an @id', () => {
    // ObjectListWidget keys its drag list on it and renders nothing for a
    // row without one -- a silent empty list, not an error.
    const rows = toGroupRows({ editors: 'site-editors', staff: 'site-staff' });

    expect(rows.every((row) => row['@id'])).toBe(true);
    expect(rows[0]['@id']).not.toEqual(rows[1]['@id']);
  });

  it('keeps the stored order', () => {
    const rows = toGroupRows({ staff: 'site-staff', editors: 'site-editors' });

    expect(rows.map((row) => row.group)).toEqual(['staff', 'editors']);
  });

  it('survives an absent map', () => {
    expect(toGroupRows(undefined)).toEqual([]);
  });
});

describe('fromGroupRows', () => {
  it('turns rows back into a map', () => {
    expect(
      fromGroupRows([{ '@id': 'a', group: 'editors', local: 'site-editors' }]),
    ).toEqual({ editors: 'site-editors' });
  });

  it('drops a row the operator has not finished', () => {
    // A blank row is what pressing Add produces, and it must not be stored.
    // It matters more here than in the property map: a half-written row that
    // reached the backend as a key with an empty value is a mapping that
    // grants nothing while looking on screen like one that grants something.
    const blank = { '@id': 'a', group: '', local: '' };

    expect(fromGroupRows([blank])).toEqual({});
    expect(fromGroupRows([{ ...blank, group: 'editors' }])).toEqual({});
    expect(fromGroupRows([{ ...blank, local: 'site-editors' }])).toEqual({});
  });

  it('trims both halves', () => {
    const rows = [
      { '@id': 'a', group: '  editors  ', local: '  site-editors  ' },
    ];

    expect(fromGroupRows(rows)).toEqual({ editors: 'site-editors' });
  });

  it('keeps the last of a repeated provider group', () => {
    // Which is what the object it becomes would do anyway.
    const rows = [
      { '@id': 'a', group: 'editors', local: 'site-editors' },
      { '@id': 'b', group: 'editors', local: 'site-staff' },
    ];

    expect(fromGroupRows(rows)).toEqual({ editors: 'site-staff' });
  });

  it('lets two provider groups grant the same local group', () => {
    const rows = [
      { '@id': 'a', group: 'editors', local: 'staff' },
      { '@id': 'b', group: 'authors', local: 'staff' },
    ];

    expect(fromGroupRows(rows)).toEqual({ editors: 'staff', authors: 'staff' });
  });

  it('survives absent rows', () => {
    expect(fromGroupRows(undefined)).toEqual({});
  });
});
