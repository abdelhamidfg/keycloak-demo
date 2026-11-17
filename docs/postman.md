# Postman: test the same OIDC and authorization behavior

1. Import `postman/commerce.postman_collection.json` and `postman/local.postman_environment.json`; select the **Commerce local** environment.
2. For OpenShift, replace `keycloak_url`, `customer_url`, and `order_url` with their HTTPS routes (no trailing slash). Use the generated user passwords from `.runtime/<namespace>/demo-login.json`.
3. Select the collection, then **Authorization → OAuth 2.0 → Get New Access Token**. The collection includes these settings; if your Postman version does not populate them, enter:

   | Setting | Value |
   |---|---|
   | Grant type | Authorization Code (With PKCE) |
   | Callback URL | `https://oauth.pstmn.io/v1/callback` |
   | Authorize using browser | Enabled |
   | Auth URL | `{{keycloak_url}}/realms/commerce-demo/protocol/openid-connect/auth` |
   | Access token URL | `{{keycloak_url}}/realms/commerce-demo/protocol/openid-connect/token` |
   | Client ID | `commerce-postman` |
   | Client secret | Leave empty |
   | Code challenge method | SHA-256 / S256 |
   | Scope | `openid profile email` |
   | Client authentication | Send client credentials in body (client ID only) |

4. Log in as Alice. Copy **Access Token**, not ID Token, into the environment's local `alice_token` value. Mark it sensitive and keep it out of shared/synced values.
5. Log out of the Keycloak browser session, or use a separate browser profile, and repeat for Bob. Store his access token as local `bob_token`. Check the login user carefully; existing SSO sessions can silently reuse Alice.
6. Restart the Order API to reset data, then run the whole collection in order. Requests explicitly select the appropriate token variable; clicking **Use Token** alone does not populate those variables.

The tests cover anonymous 401, both users' reads, Alice's forbidden mutations, Bob's successful update/delete, input validation, and 404 after deletion. Tokens expire in five minutes; obtain fresh tokens if tests return 401. The final requests delete `O200`, so a repeat run requires restarting Order API.

No client secret or Resource Owner Password Credentials grant is needed. Requests can also run in Newman after supplying fresh token variables obtained interactively, but Newman does not perform the interactive browser login itself.

The OpenShift environment file contains example URLs and blank tokens. Replace the URLs locally with your routes before use, and keep tokens out of shared or committed values.
