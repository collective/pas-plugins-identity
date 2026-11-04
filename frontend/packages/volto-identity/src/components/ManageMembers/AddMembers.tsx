/**
 * Find people and groups, pick several, and add them in one go.
 *
 * The search is plone.restapi's own: `@users?search=` for people and
 * `@groups?query=` for groups, sent by the page that owns this form. What is
 * picked survives the next search, so somebody can look for three people by
 * three names and add all of them with one request.
 *
 * Given the candidates rather than reading them from the store, so every
 * state is a set of props.
 * @module components/ManageMembers/AddMembers
 */
import React, { useEffect, useState } from 'react';
import { defineMessages, useIntl } from 'react-intl';
import { SearchField } from '@plone/components';
import { Button, Label } from 'semantic-ui-react';

import '@plone/components/src/styles/basic/SearchField.css';

import './AddMembers.scss';

/** How long typing has to pause before the search is sent. */
export const CANDIDATE_SEARCH_DELAY = 300;

/** Somebody, or some group, who could be added. */
export interface Candidate {
  id: string;
  /** The person's name or the group's title. */
  title: string;
  type: 'user' | 'group';
  /** A login or an email, to tell two people of one name apart. */
  detail?: string;
}

const messages = defineMessages({
  heading: { id: 'manage-members-add', defaultMessage: 'Add members' },
  search: {
    id: 'manage-members-add-search',
    defaultMessage: 'Find people or groups',
  },
  placeholder: {
    id: 'manage-members-add-placeholder',
    defaultMessage: 'Name, login or group',
  },
  searching: { id: 'group-view-searching', defaultMessage: 'Searching…' },
  nothing: {
    id: 'manage-members-add-nothing',
    defaultMessage: 'Nobody matches “{query}”.',
  },
  group: { id: 'manage-members-group', defaultMessage: 'Group' },
  selected: {
    id: 'manage-members-add-selected',
    defaultMessage: 'To add',
  },
  unselect: {
    id: 'manage-members-add-unselect',
    defaultMessage: 'Do not add {name}',
  },
  add: {
    id: 'manage-members-add-button',
    defaultMessage:
      '{count, plural, =0 {Add} one {Add # member} other {Add # members}}',
  },
});

export interface AddMembersProps {
  /** What was searched for. */
  query: string;
  /** Called, after a pause in typing, with what is in the box. */
  onQuery: (query: string) => void;
  /** What the search found. */
  candidates: Candidate[];
  /** Whether a search is on its way. */
  searching: boolean;
  /** Whether a change of members is being saved. */
  busy: boolean;
  /** Called with everybody picked; the selection is cleared. */
  onAdd: (selected: Candidate[]) => void;
}

const AddMembers: React.FC<AddMembersProps> = ({
  query,
  onQuery,
  candidates,
  searching,
  busy,
  onAdd,
}) => {
  const intl = useIntl();
  const [text, setText] = useState(query);
  const [selected, setSelected] = useState<Candidate[]>([]);

  useEffect(() => {
    const next = text.trim();
    if (next === query) {
      return undefined;
    }
    const timer = setTimeout(() => onQuery(next), CANDIDATE_SEARCH_DELAY);
    return () => clearTimeout(timer);
  }, [text, query, onQuery]);

  const isSelected = (candidate: Candidate) =>
    selected.some((s) => s.id === candidate.id);

  const toggle = (candidate: Candidate) =>
    setSelected((current) =>
      current.some((s) => s.id === candidate.id)
        ? current.filter((s) => s.id !== candidate.id)
        : [...current, candidate],
    );

  const add = () => {
    onAdd(selected);
    setSelected([]);
  };

  let found: React.ReactNode = null;
  if (query && searching) {
    found = (
      <p className="identity-note" role="status">
        {intl.formatMessage(messages.searching)}
      </p>
    );
  } else if (query && !candidates.length) {
    found = (
      <p className="identity-note">
        {intl.formatMessage(messages.nothing, { query })}
      </p>
    );
  } else if (query) {
    found = (
      <ul className="identity-add-members__candidates">
        {candidates.map((candidate) => (
          <li key={`${candidate.type}:${candidate.id}`}>
            <label>
              <input
                type="checkbox"
                checked={isSelected(candidate)}
                disabled={busy}
                onChange={() => toggle(candidate)}
              />
              <span>{candidate.title}</span>
              {candidate.type === 'group' ? (
                <Label size="mini">{intl.formatMessage(messages.group)}</Label>
              ) : null}
              {candidate.detail ? (
                <span className="identity-note">{candidate.detail}</span>
              ) : null}
            </label>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <section className="identity-add-members">
      <h2>{intl.formatMessage(messages.heading)}</h2>
      <SearchField
        label={intl.formatMessage(messages.search)}
        placeholder={intl.formatMessage(messages.placeholder)}
        value={text}
        onChange={setText}
      />
      {found}
      {selected.length ? (
        <div className="identity-add-members__selected">
          <span>{intl.formatMessage(messages.selected)}:</span>
          {selected.map((candidate) => (
            <Label key={`${candidate.type}:${candidate.id}`}>
              {candidate.title}
              <button
                type="button"
                className="identity-add-members__unselect"
                aria-label={intl.formatMessage(messages.unselect, {
                  name: candidate.title,
                })}
                disabled={busy}
                onClick={() => toggle(candidate)}
              >
                ×
              </button>
            </Label>
          ))}
        </div>
      ) : null}
      <Button
        primary
        type="button"
        disabled={busy || !selected.length}
        loading={busy}
        onClick={add}
      >
        {intl.formatMessage(messages.add, { count: selected.length })}
      </Button>
    </section>
  );
};

export default AddMembers;
