import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '../../testing';
import React from 'react';

import ProviderIconWidget, { iconSource } from './ProviderIconWidget';

const SVG = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>';
const ENVELOPE = `filenameb64:${btoa('icon.svg')};datab64:${btoa(SVG)}`;

describe('iconSource', () => {
  it('reads the document out of the envelope', () => {
    expect(iconSource(ENVELOPE)).toBe(SVG);
  });

  it('is empty for a value that is not an envelope', () => {
    expect(iconSource('')).toBe('');
    expect(iconSource(undefined)).toBe('');
    expect(iconSource('<svg/>')).toBe('');
  });

  it('is empty rather than throwing on an undecodable payload', () => {
    // A field that cannot be decoded shows empty and is uploaded again. A
    // crash here would take the whole provider form with it.
    expect(iconSource('filenameb64:aaa;datab64:!!!not base64!!!')).toBe('');
  });
});

describe('ProviderIconWidget', () => {
  it('previews by inlining the document', () => {
    // Not through `/@@site-logo/<filename>`, which is what Volto's own
    // registry image widget does and which 404s for a provider icon.
    render(
      <ProviderIconWidget id="icon" value={ENVELOPE} onChange={vi.fn()} />,
    );

    expect(
      screen.getByTestId('provider-icon-preview').querySelector('svg'),
    ).toBeTruthy();
  });

  it('offers a replacement once there is an icon', () => {
    render(
      <ProviderIconWidget id="icon" value={ENVELOPE} onChange={vi.fn()} />,
    );

    expect(screen.getByRole('button', { name: /replace/i })).toBeTruthy();
  });

  it('offers only an upload when there is none', () => {
    render(<ProviderIconWidget id="icon" value="" onChange={vi.fn()} />);

    expect(screen.getByRole('button', { name: /choose/i })).toBeTruthy();
    expect(screen.queryByTestId('provider-icon-preview')).toBeNull();
  });
});

describe('ProviderIconWidget on a driver with a default icon', () => {
  const DEFAULT =
    '<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>';

  it("shows the driver's icon while nothing is uploaded", () => {
    render(
      <ProviderIconWidget
        id="icon"
        value=""
        default_icon={DEFAULT}
        onChange={vi.fn()}
      />,
    );

    expect(
      screen.getByTestId('provider-icon-default').querySelector('circle'),
    ).toBeTruthy();
    expect(screen.queryByTestId('provider-icon-preview')).toBeNull();
  });

  it('offers an upload and nothing to remove, since nothing is stored', () => {
    render(
      <ProviderIconWidget
        id="icon"
        value=""
        default_icon={DEFAULT}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByRole('button', { name: /choose/i })).toBeTruthy();
    expect(screen.queryByRole('button', { name: /remove/i })).toBeNull();
  });

  it('shows the upload instead once there is one', () => {
    render(
      <ProviderIconWidget
        id="icon"
        value={ENVELOPE}
        default_icon={DEFAULT}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByTestId('provider-icon-preview')).toBeTruthy();
    expect(screen.queryByTestId('provider-icon-default')).toBeNull();
  });
});
