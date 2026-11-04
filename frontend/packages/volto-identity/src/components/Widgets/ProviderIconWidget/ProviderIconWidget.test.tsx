import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '../../../testing';
import React from 'react';

import ProviderIconWidget, {
  base64Utf8,
  envelopeOf,
  iconSource,
} from './ProviderIconWidget';

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

/**
 * Read the file name back out of an envelope, as the backend does: base64,
 * then UTF-8.
 *
 * @param envelope The stored value.
 * @returns The name.
 */
function nameIn(envelope: string): string {
  const encoded = /^filenameb64:([^;]*);/.exec(envelope)?.[1] ?? '';
  const bytes = Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0));
  return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
}

/**
 * Choose a file in the widget's picker.
 *
 * @param name The file's name.
 * @param source What it holds.
 */
function choose(name: string, source: string): void {
  const input = document.querySelector(
    'input[type="file"]',
  ) as HTMLInputElement;
  fireEvent.change(input, {
    target: { files: [new File([source], name, { type: 'image/svg+xml' })] },
  });
}

describe('the envelope', () => {
  it('encodes a name as its UTF-8 bytes', () => {
    // What `plone.formwidget.namedfile` decodes it as.
    expect(base64Utf8('ícone.svg')).toBe(btoa('\xc3\xadcone.svg'));
  });

  it('carries any name, Latin-1 or not', () => {
    const envelope = envelopeOf(
      '门户 ícone.svg',
      `data:image/svg+xml;base64,${btoa(SVG)}`,
    );

    expect(nameIn(envelope as string)).toBe('门户 ícone.svg');
  });

  it('is null for a data URL that is not base64', () => {
    expect(envelopeOf('a.svg', 'data:image/svg+xml,<svg/>')).toBeNull();
  });
});

describe('ProviderIconWidget uploading', () => {
  it('stores the chosen file as an envelope', async () => {
    const onChange = vi.fn();
    render(<ProviderIconWidget id="icon" value="" onChange={onChange} />);

    choose('icon.svg', SVG);

    await waitFor(() => expect(onChange).toHaveBeenCalled());
    const [id, envelope] = onChange.mock.calls[0];
    expect(id).toBe('icon');
    expect(nameIn(envelope)).toBe('icon.svg');
    expect(iconSource(envelope)).toBe(SVG);
  });

  it('uploads a file whose name is not Latin-1', async () => {
    // `btoa` on the name threw, inside the reader's callback, and the upload
    // vanished without a word.
    const onChange = vi.fn();
    render(<ProviderIconWidget id="icon" value="" onChange={onChange} />);

    choose('门户.svg', SVG);

    await waitFor(() => expect(onChange).toHaveBeenCalled());
    expect(nameIn(onChange.mock.calls[0][1])).toBe('门户.svg');
  });

  it('uploads an accented Latin-1 name the backend can decode', async () => {
    // `btoa` took it, as one byte per letter, which is not UTF-8: the backend
    // refused the upload as undecodable.
    const onChange = vi.fn();
    render(<ProviderIconWidget id="icon" value="" onChange={onChange} />);

    choose('ícone.svg', SVG);

    await waitFor(() => expect(onChange).toHaveBeenCalled());
    expect(nameIn(onChange.mock.calls[0][1])).toBe('ícone.svg');
  });

  it('previews a file just chosen as an image, without inlining it', async () => {
    // Nothing has sanitized it yet: inlined, its event handlers would run.
    const hostile =
      '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><path/></svg>';
    let stored = '';
    const onChange = vi.fn((_id: string, value: string) => {
      stored = value;
    });
    const { rerender } = render(
      <ProviderIconWidget id="icon" value="" onChange={onChange} />,
    );

    choose('icon.svg', hostile);
    await waitFor(() => expect(onChange).toHaveBeenCalled());
    rerender(
      <ProviderIconWidget id="icon" value={stored} onChange={onChange} />,
    );

    const preview = screen.getByTestId('provider-icon-preview');
    expect(preview.querySelector('svg')).toBeNull();
    expect(preview.querySelector('img')?.getAttribute('src')).toBe(
      `data:image/svg+xml;base64,${btoa(hostile)}`,
    );
  });

  it('inlines a stored icon again once the value is not the one chosen', async () => {
    let stored = '';
    const onChange = vi.fn((_id: string, value: string) => {
      stored = value;
    });
    const { rerender } = render(
      <ProviderIconWidget id="icon" value="" onChange={onChange} />,
    );
    choose('icon.svg', SVG);
    await waitFor(() => expect(stored).not.toBe(''));

    // What the backend sends back after saving: sanitized, so not the bytes
    // that were chosen.
    const SANITIZED = SVG.replace('M0 0', 'M0 1');
    const saved = `filenameb64:${btoa('icon.svg')};datab64:${btoa(SANITIZED)}`;
    expect(saved).not.toBe(stored);
    rerender(
      <ProviderIconWidget id="icon" value={saved} onChange={onChange} />,
    );

    expect(
      screen.getByTestId('provider-icon-preview').querySelector('svg'),
    ).toBeTruthy();
  });

  it('clears the picker each time it opens, so the same file can be chosen again', () => {
    // A file input fires no change for the file it already holds: removing
    // an icon and choosing the same file again did nothing.
    render(<ProviderIconWidget id="icon" value="" onChange={vi.fn()} />);
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const cleared = vi.fn();
    Object.defineProperty(input, 'value', {
      configurable: true,
      get: () => 'C:\\fakepath\\icon.svg',
      set: cleared,
    });

    fireEvent.click(screen.getByRole('button', { name: /choose/i }));

    expect(cleared).toHaveBeenCalledWith('');
  });
});
