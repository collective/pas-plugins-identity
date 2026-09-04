import type { Meta, StoryObj } from '@storybook/react';
import { Provider } from 'react-redux';
import React from 'react';

import UserAvatar from './UserAvatar';
import { LOADED, PORTRAIT, USER, withUser } from '../../stories/fixtures';
import { withToolbarButton } from '../../storybook/withUserMenu';

const meta: Meta<typeof UserAvatar> = {
  title: 'Identity/UserMenu/UserAvatar',
  component: UserAvatar,
};
export default meta;

type Story = StoryObj<typeof UserAvatar>;

/**
 * Where it is actually seen.
 *
 * This add-on's `Toolbar.jsx` puts it on `#toolbar-personal` in place of
 * Volto's camera icon, at 30px on the toolbar's own ground. The stories below
 * show the component; this one shows the component in its place, which is the
 * only one that says whether 30px is enough to tell two people apart.
 */
export const OnTheToolbarButton: Story = {
  args: { size: '30px' },
  decorators: [withUser({ portrait: null }), withToolbarButton],
  // The toolbar is fixed and full width; boxing it in the page wrapper would
  // show it somewhere it never is.
  parameters: { fullBleed: true },
};

/** The user uploaded a portrait, so it is the portrait. */
export const WithPortrait: Story = {
  decorators: [withUser({ portrait: PORTRAIT })],
};

/**
 * The common case. Most people never upload a portrait, and Volto drew a
 * camera icon for all of them -- the same picture for everybody.
 */
export const Initials: Story = {
  decorators: [withUser({ portrait: null })],
};

/**
 * Several people at once, which is the only way to see the point of the
 * colour: it is derived from the userid, so the same person is the same
 * colour everywhere and two people in a list are told apart at a glance.
 *
 * Each avatar gets its own store, because the user is read from it rather
 * than passed in as a prop.
 */
export const DifferentPeople: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '0.5rem' }}>
      {[
        { id: 'alice', fullname: 'Alice Liddell' },
        { id: 'bob', fullname: 'Bob Ross' },
        { id: 'carol', fullname: 'Carol Danvers' },
        { id: 'dave', fullname: 'Dave Grohl' },
        { id: 'ericof', fullname: 'Érico Andrei' },
      ].map((who) => (
        <Provider
          key={who.id}
          store={
            {
              getState: () => ({
                userProfile: { ...LOADED, data: { ...USER, ...who } },
              }),
              dispatch: (action: unknown) => action,
              subscribe: () => () => {},
            } as never
          }
        >
          <UserAvatar size="48px" />
        </Provider>
      ))}
    </div>
  ),
};

/** A middle name must not push the surname out: this is ÉA, not ÉD. */
export const MiddleName: Story = {
  decorators: [withUser({ id: 'ericof', fullname: 'Érico de Andrei' })],
};

/** One word is the only case that takes two letters from the same word. */
export const SingleName: Story = {
  decorators: [withUser({ id: 'madonna', fullname: 'Madonna' })],
};

/** No name yet: the userid stands in rather than leaving an empty circle. */
export const NameNotLoadedYet: Story = {
  decorators: [withUser({ id: 'alice', fullname: null })],
};

/**
 * An anonymous visitor. The component mounts on every route, so this is a
 * state it really renders in, not a hypothetical.
 */
export const Anonymous: Story = {
  decorators: [withUser(null)],
};

/** The size the toolbar button asks for, beside the size the menu used to. */
export const Large: Story = {
  args: { size: '96px' },
  decorators: [withUser({ portrait: null })],
};

/**
 * A portrait URL that does not resolve falls back to the initials.
 *
 * A deleted portrait, or a stale URL after a rename. The browser's
 * broken-image glyph reads as a bug in the site rather than as a missing
 * photograph, which is what this avoids.
 */
export const BrokenPortrait: Story = {
  decorators: [withUser({ portrait: '/no-such-portrait.png' })],
};
