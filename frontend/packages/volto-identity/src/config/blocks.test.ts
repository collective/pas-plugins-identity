import { describe, expect, it } from 'vitest';
import { createIntl } from 'react-intl';

import install from './blocks';

/**
 * Install the blocks into a configuration holding only some blocks.
 *
 * @param blocksConfig What was registered before.
 * @returns The blocks afterwards.
 */
function configured(blocksConfig: Record<string, unknown> = {}) {
  const config: any = { blocks: { blocksConfig } };
  install(config);
  return config.blocks.blocksConfig;
}

describe('install', () => {
  it('registers the sign-in block', () => {
    const block = configured().identitySignIn;

    expect(block.id).toBe('identitySignIn');
    expect(block.view).toBeDefined();
    expect(block.edit).toBeDefined();
  });

  it('keeps it out of the page block chooser until a project says so', () => {
    expect(configured().identitySignIn.restricted).toBe(true);
  });

  it('keeps the blocks already registered', () => {
    const teaser = { id: 'teaser' };

    expect(configured({ teaser }).teaser).toBe(teaser);
  });

  it('starts a new block with a welcome message and every line on', () => {
    // `blockSchema` is where Volto takes a new block's defaults from.
    const intl = createIntl({ locale: 'en', messages: {}, onError: () => {} });
    const { properties } = configured().identitySignIn.blockSchema({ intl });

    expect(properties.greeting.default).toBe('Hello {fullname}!');
    expect(properties.showProfile.default).toBe(true);
    expect(properties.showEmail.default).toBe(true);
    expect(properties.showProvider.default).toBe(true);
    expect(properties.showLastLogin.default).toBe(true);
    expect(properties.previewAnonymous.default).toBeUndefined();
  });

  it('formats its messages without a formatting error', () => {
    // The default greeting and the description name `{username}` and
    // `{fullname}`, which react-intl reads as arguments. Left without values
    // they still print, from the message source, but only after reporting an
    // error on every call.
    const errors: unknown[] = [];
    const intl = createIntl({
      locale: 'en',
      defaultLocale: 'en',
      messages: {},
      onError: (error) => errors.push(error),
    });

    configured().identitySignIn.blockSchema({ intl });

    expect(errors).toEqual([]);
  });
});

describe('install, with a grid', () => {
  /**
   * Install the blocks into a configuration holding a grid block.
   *
   * @param gridBlock The grid block as registered before.
   * @returns The blocks afterwards.
   */
  function withGrid(gridBlock: Record<string, unknown>) {
    const config: any = { blocks: { blocksConfig: { gridBlock } } };
    install(config);
    return config.blocks.blocksConfig;
  }

  it('offers the sign-in block inside a grid', () => {
    const { gridBlock } = withGrid({ allowedBlocks: ['image', 'slate'] });

    expect(gridBlock.allowedBlocks).toEqual([
      'image',
      'slate',
      'identitySignIn',
    ]);
  });

  it('gives a grid without a block config of its own none', () => {
    // The grid renders its children from its own `blocksConfig` when it has
    // one, and from the global one otherwise. One holding only the sign-in
    // block would take slate and images out of every grid.
    const { gridBlock } = withGrid({ allowedBlocks: ['slate'] });

    expect(gridBlock.blocksConfig).toBeUndefined();
  });

  it('adds itself to a grid that has a block config of its own', () => {
    const slate = { id: 'slate' };
    const blocks = withGrid({
      allowedBlocks: ['slate'],
      blocksConfig: { slate },
    });

    expect(blocks.gridBlock.blocksConfig.slate).toBe(slate);
    expect(blocks.gridBlock.blocksConfig.identitySignIn).toBe(
      blocks.identitySignIn,
    );
  });

  it('offers it once, however often it is installed', () => {
    const config: any = {
      blocks: { blocksConfig: { gridBlock: { allowedBlocks: ['slate'] } } },
    };

    install(config);
    install(config);

    expect(config.blocks.blocksConfig.gridBlock.allowedBlocks).toEqual([
      'slate',
      'identitySignIn',
    ]);
  });

  it('does not need a grid at all', () => {
    // A project may have removed it.
    expect(() => configured()).not.toThrow();
  });
});
