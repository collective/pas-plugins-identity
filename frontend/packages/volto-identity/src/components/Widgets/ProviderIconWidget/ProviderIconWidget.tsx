/**
 * Upload the SVG a login button is drawn with.
 *
 * Volto ships `RegistryImageWidget` for exactly this shape of value — the
 * `filenameb64:<name>;datab64:<bytes>` envelope Plone stores `site_logo` in —
 * and this widget sends and reads the identical envelope, so the backend
 * field is an ordinary `schema.Bytes`. The name is encoded as UTF-8, which is
 * how `plone.formwidget.namedfile` decodes it: `btoa` on the name itself, as
 * Volto's widget does, throws for a name outside Latin-1 and writes an
 * accented Latin-1 name as bytes the backend refuses.
 *
 * What it does not reuse is the preview. `RegistryImageWidget` builds one from
 * `/@@site-logo/<filename>`, which is Plone's own view and answers 404 for a
 * provider icon.
 *
 * **A stored icon is inlined,** which costs no request and is exactly what the
 * login button does with the same bytes, so what an operator sees is what a
 * visitor gets. The backend sanitizes an icon when it is stored, so a stored
 * one is safe to inline.
 *
 * **A file just chosen is not stored yet,** and nothing has sanitized it: it
 * came from the operator's disk through a `FileReader`. Inlined, its event
 * handler attributes would run in the operator's session. It is previewed as
 * an image instead, which never runs anything, until the form is saved.
 *
 * Refusing a non-SVG file is the backend's job and is done on the field
 * constraint, so an upload that slips past the accept filter is still refused
 * with a message naming what was wrong. The filter here is a courtesy, not a
 * check.
 *
 * The buttons are `@plone/components`' and the file picker is react-aria's
 * `FileTrigger`, which clears its input each time it opens, so choosing the
 * same file again after removing it is a change like any other.
 * @module components/Widgets/ProviderIconWidget
 */
import React, { useState } from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { FileTrigger } from 'react-aria-components';
import { Button } from '@plone/components';

import FormFieldWrapper from '@plone/volto/components/manage/Widgets/FormFieldWrapper';

import '@plone/components/src/styles/basic/Button.css';
import './ProviderIconWidget.scss';

const messages = defineMessages({
  choose: { id: 'Choose a file', defaultMessage: 'Choose a file' },
  replace: {
    id: 'Replace existing file',
    defaultMessage: 'Replace existing file',
  },
  remove: { id: 'Remove', defaultMessage: 'Remove' },
  byDefault: {
    id: 'provider-icon-default',
    defaultMessage: "The driver's icon, used until one is uploaded.",
  },
  hint: {
    id: 'provider-icon-hint',
    defaultMessage:
      'An SVG file. It is drawn in the button, so it takes the button' +
      ' colours; anything else is refused.',
  },
  preview: {
    id: 'provider-icon-preview',
    defaultMessage: 'The chosen icon, shown as it was uploaded until saved',
  },
});

/** What the envelope looks like, and how its two halves are named. */
const ENVELOPE = /^filenameb64:([^;]*);datab64:(.*)$/;

/** The file types the picker offers. */
const ACCEPTED = ['image/svg+xml', '.svg'];

/**
 * Read the SVG source out of a stored value.
 *
 * @param value The field value, either an envelope or empty.
 * @returns The source, or an empty string when there is nothing to draw.
 */
export function iconSource(value: unknown): string {
  const match = ENVELOPE.exec(String(value ?? ''));
  if (!match) {
    return '';
  }
  try {
    // `atob` gives one byte per character, which is not the same as UTF-8
    // text: an icon carrying a non-ASCII character in a title would come back
    // mojibake without this step.
    const bytes = Uint8Array.from(atob(match[2]), (c) => c.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  } catch {
    // A value that is not decodable is not a crash: the field shows empty and
    // the operator uploads again.
    return '';
  }
}

/**
 * Encode text as the base64 of its UTF-8 bytes.
 *
 * @param text Any text, a file name included.
 * @returns The base64, which `atob` and Python's `b64decode` both read back
 *   as those bytes.
 */
export function base64Utf8(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let binary = '';
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

/**
 * Wrap a file read as a data URL in the envelope the field stores.
 *
 * @param name The file's name.
 * @param dataUrl What `FileReader.readAsDataURL` gave.
 * @returns The envelope, or null when the data URL is not base64.
 */
export function envelopeOf(name: string, dataUrl: string): string | null {
  const parsed = /^data:[^,]*;base64,(.*)$/.exec(dataUrl);
  return parsed ? `filenameb64:${base64Utf8(name)};datab64:${parsed[1]}` : null;
}

interface ProviderIconWidgetProps {
  id: string;
  value?: string;
  onChange: (id: string, value: string) => void;
  isDisabled?: boolean;
  /**
   * The chosen driver's icon, which the login button draws while nothing
   * is uploaded. `providerSchema` puts it on the field.
   */
  default_icon?: string;
  [key: string]: unknown;
}

const ProviderIconWidget: React.FC<ProviderIconWidgetProps> = (props) => {
  const { id, value, onChange, isDisabled, default_icon: defaultIcon } = props;
  const intl = useIntl();
  // The envelope this widget produced from a file just chosen. While the
  // field still holds it, nothing has sanitized it.
  const [chosen, setChosen] = useState<string | null>(null);
  const source = iconSource(value);
  const fresh = Boolean(value) && value === chosen;

  const onSelect = (files: FileList | null) => {
    const file = files?.[0];
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const envelope = envelopeOf(file.name, String(reader.result ?? ''));
      if (envelope) {
        setChosen(envelope);
        onChange(id, envelope);
      }
    };
    reader.readAsDataURL(file);
  };

  let preview: React.ReactNode = null;
  if (source && fresh) {
    const match = ENVELOPE.exec(String(value));
    preview = (
      <div
        className="provider-icon-widget__preview"
        data-testid="provider-icon-preview"
      >
        <img
          src={`data:image/svg+xml;base64,${match?.[2] ?? ''}`}
          alt={intl.formatMessage(messages.preview)}
        />
      </div>
    );
  } else if (source) {
    preview = (
      <div
        className="provider-icon-widget__preview"
        data-testid="provider-icon-preview"
        // A stored icon: the backend sanitized it on assignment, and this is
        // the same document the login button inlines.
        dangerouslySetInnerHTML={{ __html: source }}
      />
    );
  } else if (defaultIcon) {
    preview = (
      <>
        <div
          className="provider-icon-widget__preview provider-icon-widget__preview--default"
          data-testid="provider-icon-default"
          // Served by `@identity-drivers`, sanitized on the backend the way
          // an upload is, and what the login button draws right now.
          dangerouslySetInnerHTML={{ __html: defaultIcon }}
        />
        <p className="help">{intl.formatMessage(messages.byDefault)}</p>
      </>
    );
  }

  return (
    <FormFieldWrapper {...props} className="provider-icon-widget">
      {preview}
      <div className="provider-icon-widget__buttons">
        <FileTrigger acceptedFileTypes={ACCEPTED} onSelect={onSelect}>
          <Button isDisabled={isDisabled}>
            {intl.formatMessage(source ? messages.replace : messages.choose)}
          </Button>
        </FileTrigger>
        {source ? (
          <Button isDisabled={isDisabled} onPress={() => onChange(id, '')}>
            {intl.formatMessage(messages.remove)}
          </Button>
        ) : null}
      </div>
      <p className="help">{intl.formatMessage(messages.hint)}</p>
    </FormFieldWrapper>
  );
};

export default ProviderIconWidget;
