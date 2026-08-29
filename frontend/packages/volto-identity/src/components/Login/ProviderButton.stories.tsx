import type { Meta, StoryObj } from '@storybook/react';

import ProviderButton from './ProviderButton';
import { GITHUB, GOOGLE, KEYCLOAK, STYLED } from '../../stories/fixtures';

const meta: Meta<typeof ProviderButton> = {
  title: 'Identity/Login/ProviderButton',
  component: ProviderButton,
  args: {
    id: GOOGLE.id,
    driver: GOOGLE.driver,
    label: GOOGLE.title,
    disabled: false,
    onSelect: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ProviderButton>;

export const Google: Story = {};

export const GitHub: Story = {
  args: { id: GITHUB.id, driver: GITHUB.driver, label: GITHUB.title },
};

/** Any provider reached through discovery, which is most of them. */
export const GenericOIDC: Story = {
  args: { id: KEYCLOAK.id, driver: KEYCLOAK.driver, label: KEYCLOAK.title },
};

/**
 * The local password form, which the login page offers as one of these. Its
 * colours are `volto-authomatic`'s `plone` provider.
 */
export const Password: Story = {
  args: { driver: 'plone', label: 'Sign in with a password', id: undefined },
};

/**
 * Disabled while a redirect is already under way: a second click would start
 * a second flow whose state replaces the first one's.
 */
export const Redirecting: Story = { args: { disabled: true } };

/** A provider whose title the operator never set falls back to its id. */
export const Untitled: Story = { args: { label: GOOGLE.id } };

/**
 * A provider wearing the look an operator gave it in the control panel.
 *
 * The icon is inlined rather than served as an image, which is what lets a
 * monochrome one take the button's own text colour.
 */
export const Styled: Story = {
  args: {
    id: STYLED.id,
    driver: STYLED.driver,
    label: STYLED.title,
    icon: STYLED.icon,
    background_color: STYLED.background_color,
    foreground_color: STYLED.foreground_color,
  },
};

/** An icon and no colours: the theme's own button, with a mark on it. */
export const IconOnly: Story = {
  args: {
    id: STYLED.id,
    driver: STYLED.driver,
    label: STYLED.title,
    icon: STYLED.icon,
  },
};
