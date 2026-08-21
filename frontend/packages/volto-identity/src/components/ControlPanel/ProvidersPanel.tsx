/**
 * The provider control panel, without store or routing.
 * @module components/ControlPanel/ProvidersPanel
 */
import React, { useState } from 'react';
import type { ConfiguredProvider, ConnectionCheck, Driver } from '../../types';
import ProviderForm from './ProviderForm';

interface ProvidersPanelProps {
  providers: ConfiguredProvider[];
  drivers: Driver[];
  loading: boolean;
  busy: boolean;
  check?: ConnectionCheck | null;
  checking?: string | null;
  onSave: (providerId: string, values: Record<string, unknown>) => void;
  onDelete: (providerId: string) => void;
  onTest: (providerId: string) => void;
}

const ProvidersPanel: React.FC<ProvidersPanelProps> = ({
  providers,
  drivers,
  loading,
  busy,
  check,
  checking,
  onSave,
  onDelete,
  onTest,
}) => {
  const [edits, setEdits] = useState<Record<string, Record<string, unknown>>>(
    {},
  );

  if (loading) {
    return (
      <div className="identity-controlpanel" role="status">
        Loading providers…
      </div>
    );
  }

  if (!providers.length) {
    return (
      <div className="identity-controlpanel identity-controlpanel--empty">
        <p>No providers are configured yet.</p>
      </div>
    );
  }

  return (
    <div className="identity-controlpanel">
      {providers.map((provider) => {
        const driver = drivers.find((d) => d.id === provider.driver);
        const values = { ...provider.config, ...(edits[provider.id] ?? {}) };

        return (
          <section
            key={provider['@id']}
            className="identity-controlpanel__provider"
            data-provider={provider.id}
          >
            <h2>{provider.title || provider.id}</h2>

            {driver ? (
              <ProviderForm
                driver={driver}
                values={values}
                disabled={busy}
                onChange={(name, value) =>
                  setEdits((current) => ({
                    ...current,
                    [provider.id]: {
                      ...(current[provider.id] ?? {}),
                      [name]: value,
                    },
                  }))
                }
              />
            ) : (
              // An orphaned provider: its add-on is gone, so there is no
              // schema to render. The backend masks every value of one of
              // these, so there is nothing safe to show either.
              <p className="identity-error" role="alert">
                The driver <code>{provider.driver}</code> is not installed. This
                provider cannot be edited or used.
              </p>
            )}

            <div className="identity-controlpanel__actions">
              <button
                type="button"
                disabled={busy || !driver}
                onClick={() => onSave(provider.id, values)}
              >
                Save
              </button>
              <button
                type="button"
                disabled={busy || !driver}
                onClick={() => onTest(provider.id)}
              >
                Test connection
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => onDelete(provider.id)}
              >
                Delete
              </button>
            </div>

            {checking === provider.id && check ? (
              <p
                className={`identity-check identity-check--${check.ok ? 'ok' : 'failed'}`}
                role="status"
              >
                {check.ok
                  ? `Reached ${check.token_endpoint}${check.has_jwks ? '' : ' (no key set published)'}`
                  : check.error}
              </p>
            ) : null}
          </section>
        );
      })}
    </div>
  );
};

export default ProvidersPanel;
