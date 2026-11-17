const definitions = [
  ['access', 'Access token', 'token', 'tokenParsed', 'Sent to the Customer and Order APIs. Inspect aud, realm_access.roles, scope and exp.'],
  ['id', 'ID token', 'idToken', 'idTokenParsed', 'Describes the signed-in user and the client that authenticated them. It is not an API credential.'],
  ['refresh', 'Refresh token', 'refreshToken', 'refreshTokenParsed', 'Used by the adapter to obtain fresh tokens. It is not sent to the application APIs.'],
];

export function mountTokenInspector(keycloak, root) {
  const cards = definitions.map(([id, title, tokenKey, parsedKey, description]) => {
    const card = document.createElement('article');
    card.className = 'token-card';
    card.innerHTML = `<h3>${title}</h3><p>${description}</p>
      <p class="token-expiry" id="${id}-expiry"></p>
      <details><summary>Decoded claims</summary><pre id="${id}-claims"></pre></details>
      <button type="button" id="${id}-reveal" aria-controls="${id}-raw" aria-expanded="false">Reveal ${title.toLowerCase()}</button>
      <pre id="${id}-raw" class="raw-token" hidden></pre>`;
    root.querySelector('.token-grid').append(card);
    const raw = card.querySelector('.raw-token');
    const reveal = card.querySelector('button');
    const state = { card, raw, reveal, tokenKey, parsedKey, title, lastToken: undefined, shown: false };
    reveal.onclick = () => {
      state.shown = !state.shown;
      reveal.setAttribute('aria-expanded', String(state.shown));
      reveal.textContent = `${state.shown ? 'Hide' : 'Reveal'} ${title.toLowerCase()}`;
      raw.hidden = !state.shown;
      raw.textContent = state.shown ? keycloak[tokenKey] || '' : '';
    };
    return state;
  });
  const status = root.querySelector('#token-refresh-status');
  const refresh = root.querySelector('#refresh-tokens');
  let refreshing = false;
  function sync(forceMask = false) {
    for (const state of cards) {
      const token = keycloak[state.tokenKey];
      const claims = keycloak[state.parsedKey];
      if (token !== state.lastToken || forceMask) {
        state.lastToken = token;
        state.shown = false;
        state.raw.textContent = '';
        state.raw.hidden = true;
        state.reveal.setAttribute('aria-expanded', 'false');
        state.reveal.textContent = `Reveal ${state.title.toLowerCase()}`;
        state.card.querySelector('details pre').textContent = claims
          ? JSON.stringify(claims, null, 2)
          : token ? 'This token has no decoded JWT claims available.' : 'No token available.';
      }
      state.reveal.disabled = !token;
      const expiry = state.card.querySelector('.token-expiry');
      if (typeof claims?.exp === 'number') {
        const seconds = Math.ceil(claims.exp - Date.now() / 1000 + (keycloak.timeSkew || 0));
        expiry.textContent = `${seconds > 0 ? `Expires in ${Math.floor(seconds / 60)}m ${seconds % 60}s` : 'Expired'} · ${new Date(claims.exp * 1000).toLocaleString()}`;
        expiry.className = `token-expiry ${seconds > 0 ? 'allowed' : 'denied'}`;
      } else {
        expiry.textContent = token ? 'Expiry is not available in this token.' : 'No token available.';
        expiry.className = 'token-expiry';
      }
    }
    refresh.disabled = refreshing || !keycloak.refreshToken;
  }
  keycloak.onAuthRefreshSuccess = () => {
    sync(true);
    status.textContent = `Tokens refreshed at ${new Date().toLocaleTimeString()}. Raw values have been hidden again.`;
  };
  keycloak.onAuthLogout = () => {
    sync();
    status.textContent = 'Session ended. Sign in again to inspect tokens.';
  };
  refresh.onclick = async () => {
    refreshing = true;
    refresh.disabled = true;
    status.textContent = 'Refreshing tokens…';
    try {
      await keycloak.updateToken(-1);
    } catch {
      status.textContent = 'Unable to refresh the session. Sign out and sign in again.';
    } finally {
      refreshing = false;
      sync();
    }
  };
  sync();
  const timer = setInterval(sync, 1000);
  window.addEventListener('pagehide', () => clearInterval(timer), { once: true });
}
