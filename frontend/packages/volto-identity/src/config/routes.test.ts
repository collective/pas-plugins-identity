import { describe, expect, it } from 'vitest';

import install, {
  CALLBACK_PATH,
  CLIENTS_CONTROLPANEL_PATH,
  CONSENT_PATH,
  CONTROLPANEL_PATH,
} from './routes';

/**
 * A config as Volto hands one to an add-on's install step.
 *
 * @returns The config object, with the keys this step appends to.
 */
function emptyConfig(): any {
  return { settings: { nonContentRoutes: [] }, addonRoutes: [] };
}

describe('the routes install step', () => {
  it('registers a route per page this add-on serves', () => {
    const config = emptyConfig();

    install(config);

    const paths = config.addonRoutes.map((route: any) => route.path);
    expect(paths).toContain(CALLBACK_PATH);
    expect(paths).toContain(CONSENT_PATH);
    expect(paths).toContain(CONTROLPANEL_PATH);
  });

  it('keeps its pages out of the content routes', () => {
    // Volto would otherwise ask the backend for a content object at each of
    // these paths, and render a 404 while the page itself works.
    const config = emptyConfig();

    install(config);

    expect(
      config.settings.nonContentRoutes.some((pattern: RegExp) =>
        pattern.test(CONSENT_PATH),
      ),
    ).toBe(true);
  });

  it('gives both control panels an icon', () => {
    // Keyed by configlet id, which is what the backend's controlpanel.xml
    // calls them. Without it Volto draws its generic placeholder, and these
    // two are the only unlabelled tiles in the listing.
    const config = emptyConfig();

    install(config);

    expect(
      config.settings.controlPanelsIcons['identity-providers'],
    ).toBeTruthy();
    expect(config.settings.controlPanelsIcons['identity-clients']).toBeTruthy();
  });

  it('keys the icons the way the panel routes are named', () => {
    // The configlet id is the last segment of the route, and a mismatch is
    // silent: the panel renders and the tile stays blank.
    const config = emptyConfig();

    install(config);

    for (const id of Object.keys(config.settings.controlPanelsIcons)) {
      expect(
        [CONTROLPANEL_PATH, CLIENTS_CONTROLPANEL_PATH].some((path) =>
          path.endsWith(`/${id}`),
        ),
      ).toBe(true);
    }
  });

  it('keeps whatever another add-on already registered', () => {
    const config = {
      settings: {
        nonContentRoutes: [/^\/other$/],
        controlPanelsIcons: { other: 'svg' },
      },
      addonRoutes: [{ path: '/other' }],
    } as any;

    install(config);

    expect(config.addonRoutes[0].path).toBe('/other');
    expect(config.settings.controlPanelsIcons.other).toBe('svg');
  });
});
