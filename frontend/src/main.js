import Keycloak from 'keycloak-js';
import './style.css';
import { mountTokenInspector } from './token-inspector.js';
const config = window.APP_CONFIG;
const keycloak = new Keycloak({ url: config.keycloakUrl, realm: config.realm, clientId: config.clientId });
const $ = (id) => document.getElementById(id);
async function callApi(base, path, method = 'GET', body) {
  try {
    await keycloak.updateToken(30);
    const response = await fetch(`${base}${path}`, {
      method,
      headers: { Authorization: `Bearer ${keycloak.token}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const raw = await response.text();
    let display = raw || '(empty response)';
    try { display = JSON.stringify(JSON.parse(raw), null, 2); } catch { /* An error can have an empty/plain text body. */ }
    $('response-status').textContent = `${method} ${path} → ${response.status} ${response.status === 403 ? 'Forbidden — Keycloak denied this permission' : response.statusText}`;
    $('response-status').className = response.ok ? 'allowed' : 'denied';
    $('response-body').textContent = display;
    if (method === 'GET') $(base === config.customerApiUrl ? 'customer-result' : 'order-result').textContent = display;
  } catch (error) {
    $('response-status').textContent = `Request failed: ${error.message || 'session expired; sign out and sign in again'}`;
    $('response-status').className = 'denied';
  }
}
try {
  await keycloak.init({ onLoad: 'login-required', pkceMethod: 'S256', flow: 'standard', checkLoginIframe: false, redirectUri: `${location.origin}/` });
  $('session').textContent = `Signed in as ${keycloak.tokenParsed.preferred_username} · Roles: ${(keycloak.realmAccess?.roles || []).filter(r => ['reader', 'order-manager'].includes(r)).join(', ')}`;
  mountTokenInspector(keycloak, $('token-inspector'));
  $('token-inspector').hidden = false;
  $('logout').hidden = false;
  $('logout').onclick = () => keycloak.logout({ redirectUri: `${location.origin}/` });
  $('customers').onclick = () => callApi(config.customerApiUrl, '/api/customers');
  $('orders').onclick = () => callApi(config.orderApiUrl, '/api/orders');
  $('update').onclick = () => callApi(config.orderApiUrl, `/api/orders/${encodeURIComponent($('order-id').value.trim())}`, 'PUT', { status: $('status').value });
  $('delete').onclick = () => {
    const id = $('order-id').value.trim();
    if (confirm(`Delete demo order ${id}? Restart the Order API to restore it.`)) callApi(config.orderApiUrl, `/api/orders/${encodeURIComponent(id)}`, 'DELETE');
  };
} catch (error) {
  $('session').textContent = `Login failed: ${error.message || 'Check Keycloak availability and client redirect URI.'}`;
}
