/**
 * One row of the users control panel, rewritten.
 *
 * Takes Volto's place through
 * `customizations/volto/components/manage/Controlpanels/Users/RenderUsers`,
 * which is where the reason for shadowing it is written down.
 *
 * Not a verbatim copy of `@plone/volto/components/manage/Controlpanels/Users/RenderUsers`
 * (Volto 19.3.0) with a patch: it keeps the markup, the class names, the
 * element ids and the behaviour Volto's stylesheet and tests expect, and
 * changes the one thing worth changing. On a Volto upgrade, read upstream's
 * diff for *behavioural* changes and port those.
 *
 * WHAT DIFFERS FROM UPSTREAM, and why:
 *
 * - **Edit goes to the Profile, for a user who has one.** Upstream always
 *   opens a modal bound to `@userschema` — the member-properties form, which
 *   writes through `portal_memberdata`. On a site running the `[content]`
 *   extra that form is the *wrong* form for anyone whose fields live in a
 *   Profile: it shows the subset of fields the schema happens to name,
 *   nothing that type added, and it edits a store which is not where that
 *   user's data is read from. Their Profile has an edit form of its own, with
 *   their actual fields on it, so Edit links there.
 *
 * - **Everyone else is untouched.** The site's `admin`, an account created
 *   before the extra was installed, any user on a site without it: no
 *   `profile_url`, so the modal opens exactly as before. That is the same
 *   condition the user menu keys on — see `helpers/profileSource` — and it is
 *   `profile_url` rather than `source` for the reason written down there:
 *   `source` names the plugin that *authenticated* the account, which is
 *   `source_users` for everybody, so keying on it hides the feature from
 *   every user it is for.
 *
 * - **The link is a `Link`, not a click handler.** It is a navigation, so it
 *   is an anchor: middle-click, open-in-new-tab and a visible target in the
 *   status bar all work, and none of them do for a `div` with an `onClick`.
 *
 * @module components/ControlPanel/RenderUsers
 */
import React, { useState } from 'react';
import { FormattedMessage, useIntl } from 'react-intl';
import { useDispatch, useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { Dropdown, Table, Checkbox } from 'semantic-ui-react';

import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toast from '@plone/volto/components/manage/Toast/Toast';
import { ModalForm } from '@plone/volto/components/manage/Form';
import { updateUser } from '@plone/volto/actions/users/users';
import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';
import { messages } from '@plone/volto/helpers/MessageLabels/MessageLabels';
import { canAssignRole } from '@plone/volto/helpers/User/User';
import editSVG from '@plone/volto/icons/editing.svg';
import ploneSVG from '@plone/volto/icons/plone.svg';
import trashSVG from '@plone/volto/icons/delete.svg';
import { toast } from 'react-toastify';

import type { UserProfile } from '../../types';

/** A role as the control panel lists them. */
interface Role {
  id: string;
}

interface RenderUsersProps {
  /** The user this row is about, as `@users` serializes them. */
  user: UserProfile & { roles: string[] };
  /** Every role the site has, in column order. */
  roles: Role[];
  onDelete: (event: React.MouseEvent, data: { value: string }) => void;
  isUserManager: boolean;
  listUsers?: () => void;
  updateUser: (userId: string, role: string) => void;
  /** Roles this user holds through a group rather than directly. */
  inheritedRole?: string[];
  userschema?: { loaded: boolean; userschema: object };
}

/**
 * Where the Edit action should lead for one user.
 *
 * @param profileUrl The user's `profile_url`, when they have a Profile.
 * @returns The app-relative edit URL, or `null` for a user whose fields are
 *   not in a Profile — for whom the member-properties modal is still right.
 */
export function profileEditUrl(
  profileUrl: string | null | undefined,
): string | null {
  if (!profileUrl) {
    return null;
  }
  // The payload carries an absolute URL on the backend's own host; a router
  // link needs the path this site serves it at.
  return `${flattenToAppURL(profileUrl)}/edit`;
}

const RenderUsers: React.FC<RenderUsersProps> = (props) => {
  const [user, setUser] = useState<Record<string, any>>({});

  const intl = useIntl();
  const dispatch = useDispatch();
  const updateRequest = useSelector((state: any) => state.users?.update);

  const {
    user: propsUser,
    listUsers,
    updateUser: updateUserRole,
    isUserManager,
    roles,
    inheritedRole,
    userschema,
    onDelete,
  } = props;

  const editUrl = profileEditUrl(propsUser.profile_url);

  const updateUserData = (userId: string, userData: object) => {
    (dispatch as any)(updateUser(userId, userData))
      .then(() => {
        setUser({});
        if (listUsers) {
          listUsers();
        }
        toast.success(
          <Toast
            success
            title={intl.formatMessage(messages.success)}
            content={intl.formatMessage(messages.updateUserSuccess)}
          />,
        );
      })
      .catch(() => {
        toast.error(
          <Toast
            error
            title={intl.formatMessage(messages.error)}
            content={intl.formatMessage(messages.thereWereSomeErrors)}
          />,
        );
      });
  };

  const onChange = (_event: unknown, { value }: { value: string }) => {
    const [userId, role] = value.split('&role=');
    updateUserRole(userId, role);
  };

  const onEditUserSubmit = (data: Record<string, any>) => {
    // Roles and groups are edited in their own columns, not in this form.
    delete data.groups;
    delete data.roles;
    updateUserData(data.id, data);
  };

  const canDeleteUser = () => {
    if (isUserManager) return true;
    return !propsUser.roles.includes('Manager');
  };

  return (
    <Table.Row key={propsUser.username ?? propsUser.id}>
      <Table.Cell className="fullname">
        {propsUser.fullname ? propsUser.fullname : propsUser.username} (
        {propsUser.username})
      </Table.Cell>
      {roles.map((role) => (
        <Table.Cell key={role.id}>
          {inheritedRole && inheritedRole.includes(role.id) ? (
            <Icon
              name={ploneSVG}
              size="20px"
              color="#007EB1"
              title={'plone-svg'}
            />
          ) : (
            <Checkbox
              checked={propsUser.roles.includes(role.id)}
              onChange={onChange as any}
              value={`${propsUser.id}&role=${role.id}`}
              disabled={!canAssignRole(isUserManager, role)}
            />
          )}
        </Table.Cell>
      ))}
      <Table.Cell textAlign="right">
        {canDeleteUser() && (
          <Dropdown icon="ellipsis horizontal">
            <Dropdown.Menu className="left">
              {editUrl ? (
                <Dropdown.Item
                  as={Link}
                  to={editUrl}
                  id="edit-user-button"
                  value={propsUser['@id']}
                >
                  <Icon name={editSVG} size="15px" />
                  <FormattedMessage id="Edit" defaultMessage="Edit" />
                </Dropdown.Item>
              ) : (
                userschema && (
                  <Dropdown.Item
                    id="edit-user-button"
                    onClick={() => {
                      setUser({ ...propsUser });
                    }}
                    value={propsUser['@id']}
                  >
                    <Icon name={editSVG} size="15px" />
                    <FormattedMessage id="Edit" defaultMessage="Edit" />
                  </Dropdown.Item>
                )
              )}
              <Dropdown.Item
                id="delete-user-button"
                onClick={onDelete as any}
                value={propsUser['@id']}
              >
                <Icon name={trashSVG} size="15px" />
                <FormattedMessage id="Delete" defaultMessage="Delete" />
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        )}
      </Table.Cell>
      {Object.keys(user).length > 0 && userschema?.loaded && (
        <ModalForm
          className="modal"
          onSubmit={onEditUserSubmit}
          submitError={user.editUserError}
          formData={user}
          onCancel={() => setUser({})}
          title={intl.formatMessage(messages.updateUserFormTitle)}
          loading={updateRequest.loading}
          schema={userschema.userschema}
        />
      )}
    </Table.Row>
  );
};

export default RenderUsers;
