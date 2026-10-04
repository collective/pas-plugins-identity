/**
 * Consent container: store, and the navigation back out to the server.
 *
 * The answer is a browser navigation rather than a fetch, and that is the
 * whole shape of this component. `@@oauth-authorize` answers a decision with
 * a 302 to the relying party's redirect URI -- it is the browser that has to
 * arrive there, carrying whatever cookies the relying party set on the way
 * out. An XHR would follow the redirect itself and hand this page a response
 * body nobody can do anything with.
 *
 * So the page reads the request over the API, renders it, and then leaves.
 * @module components/Consent/Consent
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useHistory, useLocation } from 'react-router-dom';
import { defineMessages, useIntl } from 'react-intl';

import { Helmet } from '@plone/volto/helpers/Helmet/Helmet';

import { getConsentRequest } from '../../actions';
import { answerUrl, ConsentPanel, goTo } from '@plone-collective/identity-core';
import VoltoIdentityUI from '../IdentityUI/VoltoIdentityUI';

const messages = defineMessages({
  title: { id: 'Authorize', defaultMessage: 'Authorize' },
});

const Consent: React.FC = () => {
  const intl = useIntl();
  const dispatch = useDispatch();
  const { search } = useLocation();
  const { push } = useHistory();
  // Set when the browser is on its way out. The buttons go dead rather than
  // letting a second click send a second answer to a request that has
  // already been decided.
  const [answering, setAnswering] = useState(false);

  const consent = useSelector((state: any) => state.consentRequest);

  useEffect(() => {
    // The query string is handed on verbatim: an authorization request is
    // compared byte for byte further down the flow.
    dispatch(getConsentRequest(search));
  }, [dispatch, search]);

  const onAnswer = useCallback(
    (allow: boolean) => {
      if (!consent?.data) {
        return;
      }
      setAnswering(true);
      goTo(answerUrl(consent.data, allow), push, { external: true });
    },
    [consent?.data, push],
  );

  return (
    <>
      <Helmet title={intl.formatMessage(messages.title)}>
        {/* This page is one step of somebody's sign-in, reached with their
            authorization request in the URL. It is not a page to index. */}
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <VoltoIdentityUI>
        <ConsentPanel
          request={consent?.data ?? null}
          loading={Boolean(consent?.loading)}
          error={consent?.error}
          answering={answering}
          onAnswer={onAnswer}
        />
      </VoltoIdentityUI>
    </>
  );
};

export default Consent;
