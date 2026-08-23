import { describe, expect, it } from 'vitest';

import { blankRow, fromRows, toRows } from './propertymap';

describe('toRows', () => {
  it('turns a map into rows', () => {
    expect(toRows({ login: 'username' })).toEqual([
      { '@id': expect.any(String), claim: 'login', field: 'username' },
    ]);
  });

  it('gives every row an @id', () => {
    // ObjectListWidget keys its drag list on it and renders nothing for a
    // row without one -- a silent empty list, not an error.
    const rows = toRows({ login: 'username', name: 'fullname' });

    expect(rows.every((row) => row['@id'])).toBe(true);
    expect(rows[0]['@id']).not.toEqual(rows[1]['@id']);
  });

  it('survives an absent map', () => {
    expect(toRows(undefined)).toEqual([]);
  });
});

describe('blankRow', () => {
  it('is empty but identifiable', () => {
    const row = blankRow();

    expect(row.claim).toBe('');
    expect(row.field).toBe('');
    expect(row['@id']).toBeTruthy();
  });

  it('is distinct each time', () => {
    // Two unfinished rows must be able to coexist on screen.
    expect(blankRow()['@id']).not.toEqual(blankRow()['@id']);
  });
});

describe('fromRows', () => {
  it('turns rows back into a map', () => {
    expect(
      fromRows([{ '@id': 'a', claim: 'login', field: 'username' }]),
    ).toEqual({ login: 'username' });
  });

  it('drops a row the operator has not finished', () => {
    // A blank row is what pressing Add produces, and it must not be stored.
    expect(fromRows([blankRow()])).toEqual({});
    expect(fromRows([{ ...blankRow(), claim: 'login' }])).toEqual({});
    expect(fromRows([{ ...blankRow(), field: 'username' }])).toEqual({});
  });

  it('trims what the operator typed', () => {
    expect(
      fromRows([{ '@id': 'a', claim: ' login ', field: ' username ' }]),
    ).toEqual({ login: 'username' });
  });

  it('keeps the last of a repeated claim', () => {
    expect(
      fromRows([
        { '@id': 'a', claim: 'login', field: 'username' },
        { '@id': 'b', claim: 'login', field: 'fullname' },
      ]),
    ).toEqual({ login: 'fullname' });
  });

  it('survives absent rows', () => {
    expect(fromRows(undefined)).toEqual({});
  });

  it('round-trips', () => {
    const map = { login: 'username', 'address.formatted': 'location' };

    expect(fromRows(toRows(map))).toEqual(map);
  });

  it('ignores the row id', () => {
    expect(fromRows([{ '@id': 'anything', claim: 'a', field: 'b' }])).toEqual({
      a: 'b',
    });
  });
});
