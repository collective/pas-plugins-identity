import { describe, expect, it } from 'vitest';

import { inOrder, movedIds } from './providerOrder';

describe('movedIds', () => {
  const ids = ['email', 'github', 'google'];

  it('moves a provider down into the place it was dropped in', () => {
    expect(movedIds(ids, 'email', 'google')).toEqual([
      'github',
      'google',
      'email',
    ]);
  });

  it('moves a provider up into the place it was dropped in', () => {
    expect(movedIds(ids, 'google', 'email')).toEqual([
      'google',
      'email',
      'github',
    ]);
  });

  it('swaps neighbours', () => {
    expect(movedIds(ids, 'github', 'email')).toEqual([
      'github',
      'email',
      'google',
    ]);
  });

  it('changes nothing for a provider dropped where it started', () => {
    // Nothing to save, so the caller sends no request.
    expect(movedIds(ids, 'github', 'github')).toBeNull();
  });

  it('changes nothing for a provider dropped outside the list', () => {
    expect(movedIds(ids, 'github', null)).toBeNull();
  });

  it('changes nothing for an id the list does not have', () => {
    expect(movedIds(ids, 'nobody', 'email')).toBeNull();
    expect(movedIds(ids, 'email', 'nobody')).toBeNull();
  });

  it('leaves the list it was given alone', () => {
    const given = [...ids];

    movedIds(given, 'email', 'google');

    expect(given).toEqual(ids);
  });
});

describe('inOrder', () => {
  const providers = [{ id: 'email' }, { id: 'github' }, { id: 'google' }];

  it('shows the providers in the order given', () => {
    expect(
      inOrder(providers, ['google', 'email', 'github']).map((p) => p.id),
    ).toEqual(['google', 'email', 'github']);
  });

  it('keeps a provider the order does not name, after the ones it does', () => {
    // One added since the order was taken is shown rather than lost.
    expect(inOrder(providers, ['google', 'email']).map((p) => p.id)).toEqual([
      'google',
      'email',
      'github',
    ]);
  });

  it('skips an id that names no provider', () => {
    // One deleted since the order was taken.
    expect(
      inOrder(providers, ['gone', 'github', 'email', 'google']).map(
        (p) => p.id,
      ),
    ).toEqual(['github', 'email', 'google']);
  });

  it('shows each provider once', () => {
    expect(
      inOrder(providers, ['github', 'github', 'email']).map((p) => p.id),
    ).toEqual(['github', 'email', 'google']);
  });
});
