/**
 * Upload the SVG a login button is drawn with.
 *
 * Volto ships `RegistryImageWidget` for exactly this shape of value — the
 * `filenameb64:<name>;datab64:<bytes>` envelope Plone stores `site_logo` in —
 * and this widget sends and reads the identical envelope, so the backend
 * field is an ordinary `schema.Bytes`.
 *
 * What it does not reuse is the preview. `RegistryImageWidget` builds one from
 * `/@@site-logo/<filename>`, which is Plone's own view and answers 404 for a
 * provider icon. This previews by decoding the envelope and inlining the
 * document, which costs no request and is exactly what the login button does
 * with the same bytes — so what an operator sees here is what a visitor gets.
 *
 * Refusing a non-SVG file is the backend's job and is done on the field
 * constraint, so an upload that slips past the accept filter is still refused
 * with a message naming what was wrong. The filter here is a courtesy, not a
 * check.
 * @module components/Widgets/ProviderIconWidget
 */
import React from 'react';
import { Button } from 'semantic-ui-react';
import { defineMessages, useIntl } from 'react-intl';

import FormFieldWrapper from '@plone/volto/components/manage/Widgets/FormFieldWrapper';

import './ProviderIconWidget.scss';

const messages = defineMessages({
  choose: { id: 'Choose a file', defaultMessage: 'Choose a file' },
  replace: {
    id: 'Replace existing file',
    defaultMessage: 'Replace existing file',
  },
  remove: { id: 'Remove', defaultMessage: 'Remove' },
  hint: {
    id: 'provider-icon-hint',
    defaultMessage:
      'An SVG file. It is drawn in the button, so it takes the button' +
      ' colours; anything else is refused.',
  },
});

/** What the envelope looks like, and how its two halves are named. */
const ENVELOPE = /^filenameb64:([^;]*);datab64:(.*)$/;

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

interface ProviderIconWidgetProps {
  id: string;
  value?: string;
  onChange: (id: string, value: string) => void;
  isDisabled?: boolean;
  [key: string]: unknown;
}

const ProviderIconWidget: React.FC<ProviderIconWidgetProps> = (props) => {
  const { id, value, onChange, isDisabled } = props;
  const intl = useIntl();
  const input = React.useRef<HTMLInputElement>(null);
  const source = iconSource(value);

  const onFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const parsed = /^data:(.*);(.*),(.*)$/.exec(String(reader.result ?? ''));
      if (!parsed) {
        return;
      }
      onChange(id, `filenameb64:${btoa(file.name)};datab64:${parsed[3]}`);
    };
    reader.readAsDataURL(file);
  };

  return (
    <FormFieldWrapper {...props} className="provider-icon-widget">
      {source ? (
        <div
          className="provider-icon-widget__preview"
          data-testid="provider-icon-preview"
          // The same document the login button inlines. It reached here from
          // the backend, which sanitizes an icon on assignment rather than on
          // render, so what is stored is already what is safe to draw.
          dangerouslySetInnerHTML={{ __html: source }}
        />
      ) : null}

      <input
        ref={input}
        type="file"
        accept="image/svg+xml,.svg"
        hidden
        onChange={onFile}
      />
      <Button
        type="button"
        disabled={isDisabled}
        onClick={() => input.current?.click()}
      >
        {intl.formatMessage(source ? messages.replace : messages.choose)}
      </Button>
      {source ? (
        <Button
          type="button"
          basic
          disabled={isDisabled}
          onClick={() => onChange(id, '')}
        >
          {intl.formatMessage(messages.remove)}
        </Button>
      ) : null}
      <p className="help">{intl.formatMessage(messages.hint)}</p>
    </FormFieldWrapper>
  );
};

export default ProviderIconWidget;
