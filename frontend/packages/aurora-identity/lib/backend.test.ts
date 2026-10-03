import { describe, expect, it } from 'vitest';

import {
  backendUrl,
  FLOW_COOKIE,
  flowCookie,
  relayFlowCookie,
} from './backend';

describe('backendUrl', () => {
  it('names the public origin to the backend', () => {
    expect(
      backendUrl(
        'http://localhost:8080/Plone',
        'http://localhost:3000/login-identity?code=x',
        '/@identity-callback',
      ),
    ).toBe(
      'http://localhost:8080/VirtualHostBase/http/localhost:3000/Plone/++api++/VirtualHostRoot/@identity-callback',
    );
  });

  it('spells out the default port of the public protocol', () => {
    expect(
      backendUrl(
        'http://backend:8080/Plone/',
        'https://example.org/login',
        '/@login-providers',
      ),
    ).toBe(
      'http://backend:8080/VirtualHostBase/https/example.org:443/Plone/++api++/VirtualHostRoot/@login-providers',
    );
  });

  it('copes with a site at the backend root', () => {
    expect(
      backendUrl('http://backend:8080', 'http://site.test/', '/@my-profile'),
    ).toBe(
      'http://backend:8080/VirtualHostBase/http/site.test:80/++api++/VirtualHostRoot/@my-profile',
    );
  });
});

describe('flowCookie', () => {
  it('passes on the flow cookie alone', () => {
    expect(
      flowCookie(`auth_seven=secret; ${FLOW_COOKIE}=abc.def; other=1`),
    ).toBe(`${FLOW_COOKIE}=abc.def`);
  });

  it('is empty when the browser sent none', () => {
    expect(flowCookie('auth_seven=secret')).toBe('');
    expect(flowCookie(null)).toBe('');
  });

  it('does not take a cookie whose name merely ends the same', () => {
    expect(flowCookie(`x${FLOW_COOKIE}=forged`)).toBe('');
  });
});

describe('relayFlowCookie', () => {
  it("copies the backend's flow cookie and nothing else", () => {
    const backend = new Response(null, {
      headers: [
        ['Set-Cookie', `${FLOW_COOKIE}=abc; Path=/; HttpOnly; SameSite=Lax`],
        ['Set-Cookie', '__ac=ticket; Path=/'],
      ],
    });

    const relayed = relayFlowCookie(backend, new Response(null));

    expect(relayed.headers.getSetCookie()).toEqual([
      `${FLOW_COOKIE}=abc; Path=/; HttpOnly; SameSite=Lax`,
    ]);
  });
});
