/**
 * Why a signed-in user is being held, and the way to finish.
 *
 * The profile gate holds a user whose profile is missing required fields.
 * The Volto add-on sends them straight to the edit form and says why in a
 * toast. A frontend with no toast to say it in sends them here first: this
 * names what is missing and links to the form.
 * @module components/CompleteProfile/CompleteProfileCard
 */
import React from 'react';

import { defineMessages } from '#i18n';

import { useIdentityUI } from '../IdentityUI/IdentityUI';
import LoginCard from '../Login/LoginCard';

import './CompleteProfileCard.css';

const messages = defineMessages({
  title: {
    id: 'Complete your profile',
    defaultMessage: 'Complete your profile',
  },
  body: {
    id: 'Your profile needs a few more details before you can continue.',
    defaultMessage:
      'Your profile needs a few more details before you can continue.',
  },
  bodyWithFields: {
    id: 'Please fill in {fields} before you can continue.',
    defaultMessage: 'Please fill in {fields} before you can continue.',
  },
  edit: { id: 'Edit your profile', defaultMessage: 'Edit your profile' },
  nothing: {
    id: 'complete-profile-nothing',
    defaultMessage: 'Your profile is complete.',
  },
  continue: { id: 'confirm-email-continue', defaultMessage: 'Continue' },
});

export interface CompleteProfileCardProps {
  /**
   * The missing fields, by the labels the form gives them.
   *
   * Empty for a profile that is complete, or one the backend gave no reason
   * for.
   */
  missing: string[];
  /** Whether the profile is still being held. */
  held: boolean;
  /** Where the profile's edit form is. */
  editHref: string | null;
  /** Where to go once the profile is complete. */
  continueHref?: string;
}

const CompleteProfileCard: React.FC<CompleteProfileCardProps> = ({
  missing,
  held,
  editHref,
  continueHref = '/',
}) => {
  const { t, Link } = useIdentityUI();

  return (
    <LoginCard title={t(messages.title)}>
      {held ? (
        <div className="identity-complete-profile">
          <p role="status">
            {missing.length
              ? t(messages.bodyWithFields, { fields: missing.join(', ') })
              : t(messages.body)}
          </p>
          {editHref ? (
            <p>
              <Link
                href={editHref}
                className="identity-button identity-button--primary"
              >
                {t(messages.edit)}
              </Link>
            </p>
          ) : null}
        </div>
      ) : (
        <div className="identity-complete-profile">
          <p role="status">{t(messages.nothing)}</p>
          <p>
            <Link href={continueHref}>{t(messages.continue)}</Link>
          </p>
        </div>
      )}
    </LoginCard>
  );
};

export default CompleteProfileCard;
