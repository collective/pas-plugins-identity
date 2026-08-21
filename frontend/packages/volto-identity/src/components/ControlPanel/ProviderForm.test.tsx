import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';

import ProviderForm, { inputType, SECRET_SENTINEL } from './ProviderForm';
import type { Driver } from '../../types';

/**
 * The schemas the backend actually publishes for the v1 drivers, trimmed to
 * the fields that matter here. Gate 5 asks that the widget renders every one
 * of them from metadata, so all four are exercised.
 */
const DRIVERS: Record<string, Driver> = {
  github: {
    id: 'github',
    title: 'GitHub',
    schema: {
      client_id: { type: 'string', title: 'Client ID', secret: false },
      client_secret: { type: 'string', title: 'Client secret', secret: true },
      scope: { type: 'string', title: 'Scope', secret: false },
      auto_link_by_email: {
        type: 'bool',
        title: 'Attach by verified email',
        secret: false,
      },
    },
  },
  google: {
    id: 'google',
    title: 'Google',
    schema: {
      client_id: { type: 'string', title: 'Client ID', secret: false },
      client_secret: { type: 'string', title: 'Client secret', secret: true },
    },
  },
  'oidc-generic': {
    id: 'oidc-generic',
    title: 'Generic OIDC',
    schema: {
      issuer: {
        type: 'string',
        title: 'Issuer',
        secret: false,
        required: true,
      },
      client_id: { type: 'string', title: 'Client ID', secret: false },
      client_secret: { type: 'string', title: 'Client secret', secret: true },
    },
  },
  email: {
    id: 'email',
    title: 'Email',
    schema: {
      token_ttl: {
        type: 'int',
        title: 'Link lifetime (seconds)',
        secret: false,
      },
      rate_limit_per_hour: {
        type: 'int',
        title: 'Links per address per hour',
        secret: false,
      },
    },
  },
};

describe('inputType', () => {
  it('hides secrets', () => {
    expect(inputType({ type: 'string', title: 'x', secret: true })).toBe(
      'password',
    );
  });

  it('uses a number field for integers', () => {
    expect(inputType({ type: 'int', title: 'x', secret: false })).toBe(
      'number',
    );
  });

  it('falls back to text', () => {
    expect(inputType({ type: 'string', title: 'x', secret: false })).toBe(
      'text',
    );
  });
});

describe.each(Object.keys(DRIVERS))('ProviderForm for %s', (driverId) => {
  const driver = DRIVERS[driverId];

  it('renders a field per schema entry', () => {
    render(<ProviderForm driver={driver} values={{}} onChange={vi.fn()} />);

    for (const field of Object.values(driver.schema)) {
      expect(screen.getByLabelText(field.title)).toBeTruthy();
    }
  });

  it('renders secrets as password fields and others not', () => {
    render(<ProviderForm driver={driver} values={{}} onChange={vi.fn()} />);

    for (const field of Object.values(driver.schema)) {
      const input = screen.getByLabelText(field.title) as HTMLInputElement;
      if (field.secret) {
        expect(input.type).toBe('password');
      } else {
        expect(input.type).not.toBe('password');
      }
    }
  });

  it('reports every change by field name', () => {
    const onChange = vi.fn();
    render(<ProviderForm driver={driver} values={{}} onChange={onChange} />);
    const [name, field] = Object.entries(driver.schema)[0];

    const input = screen.getByLabelText(field.title);
    if (field.type === 'bool') {
      fireEvent.click(input);
      expect(onChange).toHaveBeenCalledWith(name, true);
    } else {
      fireEvent.change(input, { target: { value: '42' } });
      expect(onChange).toHaveBeenCalledWith(name, '42');
    }
  });
});

describe('ProviderForm secrets', () => {
  it('shows the mask the backend sent rather than blanking the field', () => {
    // The masked value is what a save must send straight back to mean "keep
    // the stored secret" (S7/I4). Clearing it would send an empty string,
    // which is a different instruction entirely.
    render(
      <ProviderForm
        driver={DRIVERS.github}
        values={{ client_secret: SECRET_SENTINEL }}
        onChange={vi.fn()}
      />,
    );

    const input = screen.getByLabelText('Client secret') as HTMLInputElement;
    expect(input.value).toBe(SECRET_SENTINEL);
  });

  it('never pre-fills a secret with anything real', () => {
    render(
      <ProviderForm driver={DRIVERS.github} values={{}} onChange={vi.fn()} />,
    );

    const input = screen.getByLabelText('Client secret') as HTMLInputElement;
    expect(input.value).toBe('');
    expect(input.placeholder).toBe(SECRET_SENTINEL);
  });

  it('renders booleans as checkboxes', () => {
    render(
      <ProviderForm
        driver={DRIVERS.github}
        values={{ auto_link_by_email: true }}
        onChange={vi.fn()}
      />,
    );

    const input = screen.getByLabelText(
      'Attach by verified email',
    ) as HTMLInputElement;
    expect(input.type).toBe('checkbox');
    expect(input.checked).toBe(true);
  });

  it('marks required fields', () => {
    render(
      <ProviderForm
        driver={DRIVERS['oidc-generic']}
        values={{}}
        onChange={vi.fn()}
      />,
    );

    expect((screen.getByLabelText('Issuer') as HTMLInputElement).required).toBe(
      true,
    );
  });

  it('disables everything while a save is in flight', () => {
    // Asserted on the fieldset rather than on each input: a disabled
    // fieldset disables its controls in a browser, but jsdom does not
    // reflect that on the children's `disabled` property, so checking the
    // inputs would pass or fail for reasons unrelated to the markup.
    const { container } = render(
      <ProviderForm
        driver={DRIVERS.google}
        values={{}}
        disabled
        onChange={vi.fn()}
      />,
    );

    expect(container.querySelector('fieldset')?.disabled).toBe(true);
  });
});
