import { describe, expect, it } from 'vitest';

import { inOrder, reorderedIds } from './providerOrder';

describe('reorderedIds', () => {
  const ids = ['email', 'github', 'google'];

  it('moves a provider down, after the one it was dropped on', () => {
    expect(reorderedIds(ids, ['email'], 'google', 'after')).toEqual([
      'github',
      'google',
      'email',
    ]);
  });

  it('moves a provider up, before the one it was dropped on', () => {
    expect(reorderedIds(ids, ['google'], 'email', 'before')).toEqual([
      'google',
      'email',
      'github',
    ]);
  });

  it('reads a drop on a row as a drop before it', () => {
    expect(reorderedIds(ids, ['github'], 'email', 'on')).toEqual([
      'github',
      'email',
      'google',
    ]);
  });

  it('moves several, keeping the order they had', () => {
    expect(reorderedIds(ids, ['google', 'email'], 'github', 'after')).toEqual([
      'github',
      'email',
      'google',
    ]);
  });

  it('changes nothing for a provider dropped where it started', () => {
    // Nothing to save, so the caller sends no request.
    expect(reorderedIds(ids, ['github'], 'email', 'after')).toBeNull();
    expect(reorderedIds(ids, ['github'], 'github', 'before')).toBeNull();
  });

  it('changes nothing for an id the list does not have', () => {
    expect(reorderedIds(ids, ['nobody'], 'email', 'before')).toBeNull();
    expect(reorderedIds(ids, ['email'], 'nobody', 'before')).toBeNull();
  });

  it('leaves the list it was given alone', () => {
    const given = [...ids];

    reorderedIds(given, ['email'], 'google', 'after');

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
