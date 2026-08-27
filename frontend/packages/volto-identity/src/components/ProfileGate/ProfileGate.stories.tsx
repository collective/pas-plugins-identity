/**
 * The gate renders nothing, so the story renders where it sent you.
 *
 * A component whose entire output is a redirect has no picture of its own.
 * What is worth seeing is the decision, so each story mounts the gate on a
 * route and shows the path the app ends up on -- which is the thing that goes
 * wrong, in both directions: a user let through with an unfinished profile,
 * or a user held on a page they can never leave.
 * @module components/ProfileGate/ProfileGate.stories
 */
import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';
import { MemoryRouter, useLocation } from 'react-router-dom';

import ProfileGate from './ProfileGate';
import { LOADED, LOADING, withStore } from '../../stories/fixtures';

const PROFILE = 'https://example.org/identity-profiles/alice';

/** Show the path the router is on, after the gate has had its say. */
const Where: React.FC = () => {
  const location = useLocation();
  return (
    <p style={{ fontFamily: 'monospace' }}>
      <strong>Now at:</strong> {location.pathname}
    </p>
  );
};

/** Mount the gate on a starting route and report where it left the app. */
function at(pathname: string) {
  return (Story: React.ComponentType) => (
    <MemoryRouter initialEntries={[pathname]}>
      <Story />
      <Where />
    </MemoryRouter>
  );
}

function profileState(review_state: string | null, profile: string | null) {
  return {
    ...LOADED,
    data: {
      '@id': '/@my-profile',
      userid: 'alice',
      profile,
      review_state,
    },
  };
}

const meta: Meta<typeof ProfileGate> = {
  title: 'Identity/ProfileGate',
  component: ProfileGate,
};
export default meta;

type Story = StoryObj<typeof ProfileGate>;

/** An unfinished profile: every page becomes its edit form. */
export const Held: Story = {
  decorators: [
    at('/news'),
    withStore({
      userSession: { token: 'a-token' },
      myProfile: profileState('incomplete', PROFILE),
    }),
  ],
};

/** Already on the profile. Redirecting here would be a loop with no exit. */
export const OnTheProfileAlready: Story = {
  decorators: [
    at('/identity-profiles/alice/edit'),
    withStore({
      userSession: { token: 'a-token' },
      myProfile: profileState('incomplete', PROFILE),
    }),
  ],
};

/** Signing out has to stay possible for somebody who would rather leave. */
export const SigningOut: Story = {
  decorators: [
    at('/logout'),
    withStore({
      userSession: { token: 'a-token' },
      myProfile: profileState('incomplete', PROFILE),
    }),
  ],
};

/** A finished profile goes where it was going. */
export const LetThrough: Story = {
  decorators: [
    at('/news'),
    withStore({
      userSession: { token: 'a-token' },
      myProfile: profileState('complete', PROFILE),
    }),
  ],
};

/** A site without the [content] layer has no profiles to hold anybody for. */
export const NoProfileLayer: Story = {
  decorators: [
    at('/news'),
    withStore({
      userSession: { token: 'a-token' },
      myProfile: profileState(null, null),
    }),
  ],
};

/** Anonymous. Nothing is asked and nothing is held. */
export const Anonymous: Story = {
  decorators: [at('/news'), withStore({ userSession: {}, myProfile: LOADING })],
};
