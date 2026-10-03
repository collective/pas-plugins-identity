import { describe, expect, it } from 'vitest';
import React from 'react';
import { render } from '../../testing';

import LoginCard from './LoginCard';

describe('LoginCard', () => {
  it('heads the card with its title', () => {
    render(
      <LoginCard title="Log in">
        <p>The options</p>
      </LoginCard>,
    );

    expect(
      document.querySelector('.identity-login-card .title')?.textContent,
    ).toBe('Log in');
  });

  it('puts what it is given in the body', () => {
    render(
      <LoginCard title="Log in">
        <p>The options</p>
      </LoginCard>,
    );

    expect(
      document.querySelector('.identity-login-card .form')?.textContent,
    ).toBe('The options');
  });

  it('draws the description strip when there is something to say', () => {
    render(
      <LoginCard
        title="Log in"
        description="Choose how you would like to sign in."
      >
        <p>The options</p>
      </LoginCard>,
    );

    expect(
      document.querySelector('.identity-login-card .description')?.textContent,
    ).toBe('Choose how you would like to sign in.');
  });

  it('leaves the strip out when there is not', () => {
    // An empty strip is still a coloured band with padding.
    render(
      <LoginCard title="Log in">
        <p>The options</p>
      </LoginCard>,
    );

    expect(document.querySelector('.description')).toBeNull();
  });

  it('claims no page of its own', () => {
    // The sign-in block puts it on somebody else's page, whose id is not the
    // card's to take.
    render(
      <LoginCard title="Log in">
        <p>The options</p>
      </LoginCard>,
    );

    expect(document.querySelector('#page-login')).toBeNull();
  });
});
