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
