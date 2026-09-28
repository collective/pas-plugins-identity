/**
 * A titled list of groups, each followed to its own page.
 *
 * A group page names groups twice -- the ones it is nested inside and the ones
 * nested inside it -- and both lists are the same thing with a different
 * heading, so a parent group and a nested one are followed alike.
 *
 * Renders nothing for an empty list: a group with nothing above it has no
 * "Part of" section rather than an empty one.
 * @module components/Views/GroupsView/GroupLinks
 */
import React from 'react';
import { Link } from 'react-router-dom';

import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';

import type { NestedGroup } from '../../../types';

import './GroupLinks.scss';

export interface GroupLinksProps {
  /** The section heading, translated. */
  title: string;
  /** A line under the heading saying what the list means, translated. */
  help?: string;
  groups: NestedGroup[];
  /** An extra class on the section, to tell the two lists apart. */
  className?: string;
}

const GroupLinks: React.FC<GroupLinksProps> = ({
  title,
  help,
  groups,
  className,
}) => {
  if (!groups.length) {
    return null;
  }
  return (
    <section
      className={
        className ? `identity-group-links ${className}` : 'identity-group-links'
      }
    >
      <h2>{title}</h2>
      {help ? <p className="identity-note">{help}</p> : null}
      <ul>
        {groups.map((group) => {
          const label = group.title || group.id;
          return (
            <li key={group.id} data-group={group.id}>
              {/* A stored membership of a group the site holds no entry for
                  has nowhere to send the reader. */}
              {group.group_url ? (
                <Link to={flattenToAppURL(group.group_url)}>{label}</Link>
              ) : (
                <span>{label}</span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
};

export default GroupLinks;
