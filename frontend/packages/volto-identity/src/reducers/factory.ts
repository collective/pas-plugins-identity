/**
 * The request-lifecycle reducer every slice in this package is built from.
 *
 * One factory rather than thirty near-identical reducers: they all track the
 * same lifecycle and differ only in what they keep from the answer.
 * @module reducers/factory
 */

import type { RequestState } from '../types';

/** What Volto's api middleware dispatches. */
export type Action = { type: string; result?: unknown; error?: unknown };

/** Every slice starts here: nothing asked, nothing answered. */
export const initial: RequestState = {
  loading: false,
  loaded: false,
  error: null,
};

/**
 * Build a reducer tracking one request.
 *
 * @param actionType The base action type.
 * @param extract What to keep out of a successful result.
 * @param empty The value of that key before anything has loaded.
 * @param alsoFrom A second action that may carry this same data.
 */
export function requestReducer<T>(
  actionType: string,
  extract: (result: any) => T,
  empty: T,
  alsoFrom?: { actionType: string; extract: (result: any) => T | undefined },
) {
  const initialState = { ...initial, data: empty };
  return function reducer(state = initialState, action: Action = { type: '' }) {
    // A second action may carry this same data as an expanded component. It
    // only ever *fills*: the request it belongs to is somebody else's, so its
    // pending and failure states say nothing about this one, and a response
    // that did not carry the component must leave what is here alone.
    if (alsoFrom && action.type === `${alsoFrom.actionType}_SUCCESS`) {
      const carried = alsoFrom.extract(action.result);
      return carried === undefined
        ? state
        : {
            ...state,
            loading: false,
            loaded: true,
            error: null,
            data: carried,
          };
    }
    switch (action.type) {
      case `${actionType}_PENDING`:
        // The previous answer is cleared here as well as on success: leaving
        // it in place makes a second attempt look like it has already
        // succeeded, which for a redirect action means navigating away with
        // last time's URL.
        return { ...initialState, loading: true };
      case `${actionType}_SUCCESS`:
        return {
          ...state,
          loading: false,
          loaded: true,
          error: null,
          data: extract(action.result),
        };
      case `${actionType}_FAIL`:
        return { ...initialState, error: action.error ?? true };
      default:
        return state;
    }
  };
}
