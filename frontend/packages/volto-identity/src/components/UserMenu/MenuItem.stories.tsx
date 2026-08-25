import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';

import MenuItem from './MenuItem';

/**
 * One entry of the personal-tools menu.
 *
 * Shown inside a `<ul>` because that is where it lands: it renders the
 * `<li>` itself, and the menu's stylesheet is written against that nesting.
 */
const meta: Meta<typeof MenuItem> = {
  title: 'Identity/UserMenu/MenuItem',
  component: MenuItem,
  args: { id: 'toolbar-example', label: 'Preferences' },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <div className="personal-tools pastanaga-menu">
          <div className="pastanaga-menu-list">
            <ul>
              <Story />
            </ul>
          </div>
        </div>
      </MemoryRouter>
    ),
  ],
};
export default meta;

type Story = StoryObj<typeof MenuItem>;

/** Most entries go somewhere. */
export const ALink: Story = { args: { to: '/personal-information' } };

/** Preferences does not: it slides another panel over the toolbar. */
export const AButton: Story = { args: { onClick: () => {} } };

/** A label long enough to meet the arrow. */
export const LongLabel: Story = {
  args: { label: 'Sign-in methods and connected accounts', to: '/identities' },
};
