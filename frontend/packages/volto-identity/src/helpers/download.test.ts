import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { downloadText } from './download';

describe('downloadText', () => {
  const clicked: { name?: string; href?: string | null } = {};
  let blob: Blob | undefined;

  beforeEach(() => {
    // jsdom implements neither, and nothing here needs a real object URL.
    URL.createObjectURL = vi.fn((given: Blob) => {
      blob = given;
      return 'blob:export';
    }) as typeof URL.createObjectURL;
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clicked.name = this.download;
      clicked.href = this.getAttribute('href');
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('saves the text under the name given', () => {
    downloadText('pas.plugins.identity.providers.xml', '<registry/>');

    expect(clicked.name).toBe('pas.plugins.identity.providers.xml');
    expect(clicked.href).toBe('blob:export');
    expect(blob?.size).toBe('<registry/>'.length);
    expect(blob?.type).toBe('application/xml');
  });

  it('leaves no link behind in the page', () => {
    downloadText('providers.xml', '<registry/>');

    expect(document.querySelector('a[download]')).toBeNull();
  });

  it('releases the file once the click has been handled', async () => {
    downloadText('providers.xml', '<registry/>');

    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:export');
  });
});
