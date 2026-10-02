import { describe, expect, it } from 'vitest';

import { expandedProfile } from './expandedProfile';

describe('expandedProfile', () => {
  const component = { userid: 'alice', review_state: 'incomplete' };

  // The apiPath the test environment configures, which is what
  // `flattenToAppURL` measures against.
  const API = 'http://localhost:8080/Plone';

  function content(id: string, extra: any = component) {
    return {
      data: {
        '@id': `${API}${id}`,
        '@components': extra ? { 'my-profile': extra } : {},
      },
    };
  }

  it('returns the component when the content is this page', () => {
    expect(expandedProfile(content('/a-page'), '/a-page')).toEqual(component);
  });

  it('is null when the content is a different page', () => {
    // Volto keeps the last content it loaded, so a route that fetches none
    // leaves the previous page's answer in the store. Using it would read a
    // stale answer to a question whose whole point is freshness.
    expect(expandedProfile(content('/a-page'), '/identities')).toBeNull();
  });

  it('is null when the component is only an @id', () => {
    // Unexpanded. A URL is not an answer.
    expect(
      expandedProfile(content('/a-page', { '@id': '/@my-profile' }), '/a-page'),
    ).toBeNull();
  });

  it('is null when there is no component at all', () => {
    // An anonymous response, or a backend too old to offer it.
    expect(expandedProfile(content('/a-page', null), '/a-page')).toBeNull();
  });

  it('is null when nothing has loaded', () => {
    expect(expandedProfile(undefined, '/a-page')).toBeNull();
    expect(expandedProfile({}, '/a-page')).toBeNull();
  });

  it('matches the site root, which flattens to an empty string', () => {
    // The one path where the two spellings genuinely differ: the router says
    // `/` and `flattenToAppURL` says ``.
    expect(expandedProfile(content(''), '/')).toEqual(component);
  });
});
