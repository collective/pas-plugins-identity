import { afterEach, describe, expect, it } from 'vitest';
import React from 'react';

import config from '@plone/volto/registry';

import { render, screen } from '../../testing';
import { groupContent, profileContent } from '../../stories/fixtures';
import BelowTitleSlot from './BelowTitleSlot';

/**
 * Register a component into `belowTitle`, the way a deployment does.
 *
 * @param name The registration's name, unique within the slot.
 * @param component What to render.
 * @param predicates Volto's own filters, when the test needs them.
 */
function registerBadge(
  name: string,
  component: React.ComponentType<any>,
  predicates?: ((args: any) => boolean)[],
): void {
  config.registerSlotComponent({
    slot: 'belowTitle',
    name,
    component,
    ...(predicates ? { predicates } : {}),
  });
}

// A slot registration is global and outlives the test that made it, so the
// next file would inherit whatever this one registered.
afterEach(() => {
  delete config.slots.belowTitle;
});

describe('BelowTitleSlot', () => {
  it('renders nothing when a deployment has registered nothing', () => {
    // The state every site is in until it asks for something, so it has to
    // add no markup at all rather than an empty wrapper the CSS then has to
    // know about.
    const { container } = render(<BelowTitleSlot content={profileContent()} />);

    expect(container.innerHTML).toBe('');
  });

  it('renders a component a deployment registered', () => {
    registerBadge('badge', () => <span>Core team</span>);

    render(<BelowTitleSlot content={profileContent()} />);

    expect(screen.getByText('Core team')).toBeTruthy();
  });

  it('hands that component the content it was rendered for', () => {
    // The reason the slot is worth having: a badge is drawn from the person,
    // not from the page it happens to be on.
    registerBadge('badge', ({ content }) => <span>{content.fullname}</span>);

    render(<BelowTitleSlot content={profileContent()} />);

    expect(screen.getByText('Alice Liddell')).toBeTruthy();
  });

  it('renders a group as readily as a profile', () => {
    registerBadge('badge', ({ content }) => <span>{content['@type']}</span>);

    render(<BelowTitleSlot content={groupContent()} />);

    expect(screen.getByText('UserGroup')).toBeTruthy();
  });

  it('honours the predicates a registration carries', () => {
    // How a deployment says "profiles only" -- the mechanism the how-to
    // documents, so it is asserted here rather than taken on trust.
    registerBadge('profiles-only', () => <span>Core team</span>, [
      ({ content }: any) => content['@type'] === 'UserProfile',
    ]);

    render(<BelowTitleSlot content={groupContent()} />);

    expect(screen.queryByText('Core team')).toBeNull();
  });
});
