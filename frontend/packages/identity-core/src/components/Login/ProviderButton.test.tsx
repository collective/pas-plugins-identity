import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import React from 'react';

import ProviderButton from './ProviderButton';

const ICON =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">' +
  '<path d="M8 1l7 13H1z"/></svg>';

function renderButton(
  props: Partial<React.ComponentProps<typeof ProviderButton>> = {},
) {
  const onSelect = vi.fn();
  render(
    <ProviderButton
      id="acme"
      driver="oidc-generic"
      label="Acme SSO"
      onSelect={onSelect}
      {...props}
    />,
  );
  return { onSelect };
}

describe('ProviderButton', () => {
  it('wears the driver class when the provider has no look of its own', () => {
    renderButton();

    const button = screen.getByRole('button');
    expect(button.className).toContain('identity-provider--oidc-generic');
    expect(button.className).not.toContain('identity-provider--styled');
    expect(button.getAttribute('style')).toBeNull();
  });

  it('reports the press', () => {
    const { onSelect } = renderButton();

    fireEvent.click(screen.getByRole('button'));

    expect(onSelect).toHaveBeenCalled();
  });
});

describe('ProviderButton and the look an operator set', () => {
  it('wears the colours as an inline style', () => {
    renderButton({ background_color: '#4b3f72', foreground_color: '#ffffff' });

    const button = screen.getByRole('button') as HTMLButtonElement;
    expect(button.style.backgroundColor).toBeTruthy();
    expect(button.style.color).toBeTruthy();
  });

  it('marks itself so the stylesheet stands back', () => {
    // Otherwise the driver rules above would fight the inline style on
    // specificity, and which one won would depend on the driver.
    renderButton({ background_color: '#4b3f72' });

    expect(screen.getByRole('button').className).toContain(
      'identity-provider--styled',
    );
  });

  it('writes no style at all when neither colour is set', () => {
    // An empty string in a style object produces `background-color: ` in the
    // attribute, which some engines treat as a reset rather than as nothing.
    renderButton({ background_color: '', foreground_color: '' });

    expect(screen.getByRole('button').getAttribute('style')).toBeNull();
  });

  it('inlines the icon so it can take the button colour', () => {
    renderButton({ icon: ICON });

    expect(document.querySelector('.identity-provider__icon svg')).toBeTruthy();
  });

  it('keeps the label beside the icon', () => {
    renderButton({ icon: ICON });

    expect(screen.getByText('Acme SSO')).toBeTruthy();
  });

  it('hides the icon from assistive technology', () => {
    // The label says what the button does; the icon repeating it would be
    // read out twice.
    renderButton({ icon: ICON });

    const icon = document.querySelector('.identity-provider__icon');
    expect(icon?.getAttribute('aria-hidden')).toBe('true');
  });

  it('renders no icon element when there is no icon', () => {
    renderButton();

    expect(document.querySelector('.identity-provider__icon')).toBeNull();
  });
});
