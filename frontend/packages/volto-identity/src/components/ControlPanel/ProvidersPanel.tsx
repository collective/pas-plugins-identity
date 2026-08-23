/**
 * The provider control panel, without store or routing.
 * @module components/ControlPanel/ProvidersPanel
 */
import React, { useState } from 'react';
import type { ConfiguredProvider, ConnectionCheck, Driver } from '../../types';
import type { PropertyMapRow } from '../../helpers/propertymap';
import { fromRows, toRows } from '../../helpers/propertymap';
import ProviderForm from './ProviderForm';
import PropertyMapField from './PropertyMapField';

interface ProvidersPanelProps {
  providers: ConfiguredProvider[];
  drivers: Driver[];
  loading: boolean;
  busy: boolean;
  check?: ConnectionCheck | null;
  checking?: string | null;
  onCreate: (data: Record<string, unknown>) => void;
  onSave: (providerId: string, values: Record<string, unknown>) => void;
  onDelete: (providerId: string) => void;
  onTest: (providerId: string) => void;
}

/** A new provider's starting state. */
const BLANK = { id: '', driver: '', title: '', enabled: true };

const ProvidersPanel: React.FC<ProvidersPanelProps> = ({
  providers,
  drivers,
  loading,
  busy,
  check,
  checking,
  onCreate,
  onSave,
  onDelete,
  onTest,
}) => {
  const [edits, setEdits] = useState<Record<string, Record<string, unknown>>>(
    {},
  );
  const [draft, setDraft] = useState({ ...BLANK });
  const [draftConfig, setDraftConfig] = useState<Record<string, unknown>>({});
  const [draftMap, setDraftMap] = useState<PropertyMapRow[]>([]);
  // Rows, not the stored map: a row the operator has just added has no
  // claim yet, and converting on every keystroke would drop it.
  const [mapEdits, setMapEdits] = useState<Record<string, PropertyMapRow[]>>(
    {},
  );

  if (loading) {
    return (
      <div className="identity-controlpanel" role="status">
        Loading providers…
      </div>
    );
  }

  const chosen = drivers.find((d) => d.id === draft.driver);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    onCreate({
      id: draft.id.trim(),
      driver: draft.driver,
      title: draft.title.trim(),
      enabled: draft.enabled,
      config: draftConfig,
      propertymap: fromRows(draftMap),
    });
    setDraft({ ...BLANK });
    setDraftConfig({});
    setDraftMap([]);
  };

  return (
    <div className="identity-controlpanel">
      <section className="identity-controlpanel__list">
        <h2>Configured providers</h2>

        {providers.length ? (
          providers.map((provider) => {
            const driver = drivers.find((d) => d.id === provider.driver);
            const edit = edits[provider.id] ?? {};
            const values = { ...provider.config, ...edit };

            return (
              <section
                key={provider['@id']}
                className="identity-controlpanel__provider"
                data-provider={provider.id}
              >
                <h3>{provider.title || provider.id}</h3>

                <div className="identity-field">
                  <label htmlFor={`identity-title-${provider.id}`}>Title</label>
                  <input
                    id={`identity-title-${provider.id}`}
                    type="text"
                    disabled={busy || !driver}
                    value={String(edit.title ?? provider.title ?? '')}
                    onChange={(event) =>
                      setEdits((current) => ({
                        ...current,
                        [provider.id]: {
                          ...(current[provider.id] ?? {}),
                          title: event.target.value,
                        },
                      }))
                    }
                  />
                </div>

                <div className="identity-field">
                  <input
                    id={`identity-enabled-${provider.id}`}
                    type="checkbox"
                    disabled={busy || !driver}
                    checked={Boolean(edit.enabled ?? provider.enabled)}
                    onChange={(event) =>
                      setEdits((current) => ({
                        ...current,
                        [provider.id]: {
                          ...(current[provider.id] ?? {}),
                          enabled: event.target.checked,
                        },
                      }))
                    }
                  />
                  <label htmlFor={`identity-enabled-${provider.id}`}>
                    Enabled
                  </label>
                </div>

                {driver ? (
                  <ProviderForm
                    driver={driver}
                    scope={provider.id}
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
                    The driver <code>{provider.driver}</code> is not installed.
                    This provider cannot be edited or used.
                  </p>
                )}

                {driver ? (
                  <PropertyMapField
                    id={`propertymap-${provider.id}`}
                    rows={mapEdits[provider.id] ?? toRows(provider.propertymap)}
                    disabled={busy}
                    onChange={(rows) =>
                      setMapEdits((current) => ({
                        ...current,
                        [provider.id]: rows,
                      }))
                    }
                  />
                ) : null}

                <div className="identity-controlpanel__actions">
                  <button
                    type="button"
                    disabled={busy || !driver}
                    onClick={() => {
                      // `title` and `enabled` sit beside the config on the
                      // record, not inside it, so they travel separately.
                      const { title, enabled, ...config } = values as Record<
                        string,
                        unknown
                      >;
                      onSave(provider.id, {
                        title: String(edit.title ?? provider.title ?? ''),
                        enabled: Boolean(edit.enabled ?? provider.enabled),
                        config,
                        propertymap: fromRows(
                          mapEdits[provider.id] ?? toRows(provider.propertymap),
                        ),
                      });
                    }}
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
                    data-action="delete"
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
          })
        ) : (
          <p className="identity-controlpanel__empty">
            No providers are configured yet.
          </p>
        )}
      </section>

      <section className="identity-controlpanel__new">
        <h2>Add a provider</h2>

        {drivers.length ? (
          <form onSubmit={submit}>
            <label>
              Provider ID
              <input
                type="text"
                required
                pattern="[A-Za-z0-9_-]+"
                value={draft.id}
                onChange={(event) =>
                  setDraft({ ...draft, id: event.target.value })
                }
              />
              <small>
                Permanent. It is stored on every identity linked through this
                provider, so renaming it later would orphan them all.
              </small>
            </label>

            <label>
              Driver
              <select
                required
                value={draft.driver}
                onChange={(event) => {
                  // The schema changes with the driver, so values typed
                  // against the old one no longer mean anything.
                  setDraft({ ...draft, driver: event.target.value });
                  setDraftConfig({});
                }}
              >
                <option value="">Choose a driver…</option>
                {drivers.map((driver) => (
                  <option key={driver.id} value={driver.id}>
                    {driver.title}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Title
              <input
                type="text"
                value={draft.title}
                onChange={(event) =>
                  setDraft({ ...draft, title: event.target.value })
                }
              />
              <small>What the sign-in button says. Defaults to the ID.</small>
            </label>

            <label>
              <input
                type="checkbox"
                checked={draft.enabled}
                onChange={(event) =>
                  setDraft({ ...draft, enabled: event.target.checked })
                }
              />
              Enabled
              <small>
                A disabled provider is configured but offered to nobody.
              </small>
            </label>

            {chosen ? (
              <>
                <ProviderForm
                  driver={chosen}
                  scope="new"
                  values={draftConfig}
                  disabled={busy}
                  onChange={(name, value) =>
                    setDraftConfig((current) => ({ ...current, [name]: value }))
                  }
                />
                <PropertyMapField
                  id="propertymap-new"
                  rows={draftMap}
                  disabled={busy}
                  onChange={setDraftMap}
                />
              </>
            ) : null}

            <button type="submit" disabled={busy || !chosen}>
              Add provider
            </button>
          </form>
        ) : (
          <p className="identity-controlpanel__empty">
            No drivers are installed, so there is nothing to configure. Install
            an add-on that registers one.
          </p>
        )}
      </section>
    </div>
  );
};

export default ProvidersPanel;
