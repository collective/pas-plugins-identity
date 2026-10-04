import { describe, expect, it } from 'vitest';

import { endpoints } from './endpoints';

describe('endpoints', () => {
  it.each([
    [endpoints.userAccount('a b'), '/@user-account/a%20b'],
    [endpoints.userAccount('alice', 0), '/@user-account/alice?events=0'],
    [endpoints.clients(), '/@identity-clients'],
    [endpoints.client('a/b'), '/@identity-clients/a%2Fb'],
    [
      endpoints.clientSecretRotation('app'),
      '/@identity-clients/app/rotate-secret',
    ],
    [endpoints.consent('?client_id=x'), '/@oauth-consent?client_id=x'],
    [endpoints.grants(), '/@oauth-grants'],
    [endpoints.grant('a b'), '/@oauth-grants/a%20b'],
    [endpoints.drivers(), '/@identity-drivers'],
    [endpoints.groupMembers('staff'), '/@group-members/staff'],
    [
      endpoints.groupMembers('a b', 'jo&e'),
      '/@group-members/a%20b?query=jo%26e',
    ],
    [endpoints.identities(), '/@identities'],
    [endpoints.identities(true), '/@identities?expand=login-providers'],
    [endpoints.identity('github', 'a/1'), '/@identities/github/a%2F1'],
    [endpoints.keys(), '/@identity-keys'],
    [endpoints.keyRotation(), '/@identity-keys/rotate'],
    [endpoints.loginProviders(), '/@login-providers'],
    [endpoints.loginProvider('github'), '/@login-providers/github'],
    [
      endpoints.loginProvider('github', '/a page'),
      '/@login-providers/github?came_from=%2Fa%20page',
    ],
    [endpoints.login(), '/@login'],
    [endpoints.callback(), '/@identity-callback'],
    [endpoints.magicLink(), '/@magic-link'],
    [endpoints.magicLinkConfirm(), '/@magic-link-confirm'],
    [endpoints.user('alice'), '/@users/alice'],
    [endpoints.myProfile(), '/@my-profile'],
    [endpoints.confirmEmail(), '/@confirm-email'],
    [endpoints.providers(), '/@identity-providers'],
    [endpoints.provider('a b'), '/@identity-providers/a%20b'],
    [endpoints.providersExport(), '/@identity-providers/@export'],
    [endpoints.providersExport('github'), '/@identity-providers/github/export'],
    [
      endpoints.providerTest('github'),
      '/@identity-providers/github/test-connection',
    ],
  ])('builds %s', (built, expected) => {
    expect(built).toBe(expected);
  });
});
