/**
 * Actions for the drivers a provider can be configured against.
 * @module actions/drivers
 */

import { LIST_DRIVERS } from '../constants/ActionTypes';
import { endpoints } from '@plone-collective/identity-core';

/**
 * List the drivers, with the schema the control-panel form renders from.
 */
export function listDrivers() {
  return {
    type: LIST_DRIVERS,
    request: { op: 'get', path: endpoints.drivers() },
  };
}
