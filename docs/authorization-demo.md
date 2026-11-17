# Demonstrating centralized authorization

1. Open the frontend as Alice. Customer/order reads work; both order mutations return 403.
2. Sign out and log in as Bob. Update `O100` to `SHIPPED`; it succeeds.
3. Open the Keycloak administrator console in a separate browser profile, select realm `commerce-demo`, then **Clients → order-api → Authorization → Policies → Order managers**.
4. Change the policy's **Logic** from **Positive** to **Negative** and save. This intentionally inverts the role check for this demonstration: Bob is denied; users without `order-manager` now match. Do not leave the policy inverted.
5. In Bob's frontend session, repeat the update using the same login. It should now return 403 without restarting or rebuilding the API. The frontend sends its original access token; the enforcer asks Keycloak for authorization. Resource-path metadata may be cached, but role-policy changes are evaluated on new authorization requests.
6. Restore **Positive**, save, and repeat: Bob is allowed again.

This shows the difference between authorization policy and frontend role labels. The frontend labels are informational. Changing role assignments is a separate exercise: existing JWT role claims remain until token renewal, so sign out/in after changing a user's assigned roles.

For a less disruptive demonstration, use **Authorization → Evaluate** to compare Alice and Bob against the `Orders` resource with `read`, `update` and `delete` scopes before changing anything.

Policy structure:

| Resource server | Resource | Scope | Required role policy |
|---|---|---|---|
| `customer-api` | `Customers` | `read` | `Readers` → `reader` |
| `order-api` | `Orders` | `read` | `Readers` → `reader` |
| `order-api` | `Orders` | `update`, `delete` | `Order managers` → `order-manager` |

The realm intentionally has no broad resource-level allow permission, which could otherwise undermine scope-specific permissions.
