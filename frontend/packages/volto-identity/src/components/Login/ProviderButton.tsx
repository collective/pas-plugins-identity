/**
 * One provider button on the login page.
 * @module components/Login/ProviderButton
 */
import React from 'react';
import type { LoginProvider } from '../../types';

interface ProviderButtonProps {
  provider: LoginProvider;
  disabled?: boolean;
  onSelect: (provider: LoginProvider) => void;
}

const ProviderButton: React.FC<ProviderButtonProps> = ({
  provider,
  disabled = false,
  onSelect,
}) => (
  <button
    type="button"
    className={`identity-provider identity-provider--${provider.driver}`}
    data-provider={provider.id}
    disabled={disabled}
    onClick={() => onSelect(provider)}
  >
    {provider.title || provider.id}
  </button>
);

export default ProviderButton;
