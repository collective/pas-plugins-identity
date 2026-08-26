import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';
import { Table } from 'semantic-ui-react';

import RenderUsers from './RenderUsers';

const ROLES = [{ id: 'Member' }, { id: 'Reviewer' }, { id: 'Manager' }];

const STATE = { users: { update: { loading: false } } };

const STORE = {
  getState: () => STATE,
  dispatch: (action: unknown) => action,
  subscribe: () => () => {},
} as never;

const USERSCHEMA = {
  loaded: true,
  userschema: { properties: {}, fieldsets: [] },
};

const ALICE = {
  '@id': 'http://localhost:8080/Plone/@users/alice',
  id: 'alice',
  username: 'alice',
  fullname: 'Alice Liddell',
  email: 'alice@example.com',
  roles: ['Member'],
  source: 'source_users',
  identities: [],
  profile_url: null,
};

/**
 * One row of {menuselection}`Site Setup --> Users`. The whole point of the
 * row is in the menu behind the ellipsis, so open it to see anything: Edit
 * leads to the Profile for a user who has one, and to Volto's
 * member-properties modal for a user who does not.
 */
const meta: Meta<typeof RenderUsers> = {
  title: 'Identity/Controlpanels/RenderUsers',
  component: RenderUsers,
  decorators: [
    (Story) => (
      <Provider store={STORE}>
        <MemoryRouter>
          <Table compact>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell>User name</Table.HeaderCell>
                {ROLES.map((role) => (
                  <Table.HeaderCell key={role.id}>{role.id}</Table.HeaderCell>
                ))}
                <Table.HeaderCell />
              </Table.Row>
            </Table.Header>
            <Table.Body>
              <Story />
            </Table.Body>
          </Table>
        </MemoryRouter>
      </Provider>
    ),
  ],
  args: {
    user: ALICE as never,
    roles: ROLES,
    isUserManager: true,
    updateUser: () => {},
    onDelete: () => {},
    userschema: USERSCHEMA,
  },
};
export default meta;

type Story = StoryObj<typeof RenderUsers>;

/**
 * Their fields live in a Profile, so Edit is a link to that Profile's own
 * edit form — where their actual fields are, rather than the subset
 * `@userschema` names in a store nothing reads for them.
 */
export const BackedByAProfile: Story = {
  args: {
    user: {
      ...ALICE,
      profile_url: 'http://localhost:8080/Plone/profiles/alice',
    } as never,
  },
};

/**
 * The site's own `admin`, an account made before the extra was installed, or
 * any user on a site not running it. Volto's modal, exactly as before.
 */
export const NotBackedByAProfile: Story = {};

/**
 * Roles held through a group are shown as Plone's own icon rather than a
 * checkbox: they are not this row's to change.
 */
export const WithAnInheritedRole: Story = {
  args: {
    user: {
      ...ALICE,
      profile_url: 'http://localhost:8080/Plone/profiles/alice',
    } as never,
    inheritedRole: ['Reviewer'],
  },
};
