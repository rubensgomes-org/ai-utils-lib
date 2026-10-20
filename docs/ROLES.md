# Roles

An Entra ID token says who the caller is and which service the token is
for. Permissions are not in the token: Azure RBAC role assignments define
them, and the service checks them on every request.

## Token

| Claim         | Holds                                                    |
| ------------- | -------------------------------------------------------- |
| `aud`         | Audience: the resource the token is for                  |
| `oid`         | Identity, e.g. a user or a managed identity              |
| `scp`/`roles` | Usually only `user_impersonation`; no read/write/delete  |

The OAuth scope requested, e.g. `https://ai.azure.com/.default`, selects
the `aud`. A token has one audience, so each service needs its own token.

| OAuth scope                                    | Used for            |
| ---------------------------------------------- | ------------------- |
| `https://cognitiveservices.azure.com/.default` | Azure OpenAI        |
| `https://ai.azure.com/.default`                | Foundry, Agent APIs |

## Role Assignment

A role and a scope are not the same: a role says what an identity may
do, and a scope says where it may do it. A role assignment combines them
with an identity to grant access:

| Part               | Answers           | Example                          |
| ------------------ | ----------------- | -------------------------------- |
| Security principal | Who?              | The container app's managed ID   |
| Role definition    | What can they do? | Key Vault Secrets User           |
| RBAC scope         | Where?            | The `kv-rgomes-lab` vault        |

A role definition lists `actions` for management operations and
`dataActions` for data operations, e.g.
`Microsoft.KeyVault/vaults/secrets/getSecret/action`.

An RBAC scope is a management group, subscription, resource group, or
resource. Assignments are inherited downward, so the same role grants
different access at different scopes: Key Vault Secrets User on one
vault reads only that vault's secrets, while on a resource group it reads
secrets in every vault in that group.

The OAuth scope and the RBAC scope are unrelated: the first picks the
token's audience, the second is where a role is assigned.

## Request Authorization

1. The service validates the token's signature, expiry, and audience.
2. It finds the role assignments for the token's `oid` on the resource or
   a parent scope.
3. It allows the request only if an assigned role contains the action.

| Status | Meaning                                                      |
| ------ | ------------------------------------------------------------ |
| 401    | Invalid token, often the wrong audience                      |
| 403    | Valid token, but no role grants the action                   |

Role changes apply to existing tokens, but can take minutes to propagate.

## Roles Used by This Library

| Resource          | Role                           | Grants                  |
| ----------------- | ------------------------------ | ----------------------- |
| Key Vault         | Key Vault Secrets User         | Read secret values      |
| App Configuration | App Configuration Data Reader  | Read settings           |
| Azure OpenAI      | Cognitive Services OpenAI User | Call inference APIs     |
| Foundry project   | Azure AI User                  | Use project, Agent APIs |

In Azure Container Apps, these roles are assigned to the shared
user-assigned managed identity.

## Rubens Notes

### UAMI

A shared UAMI (User-Assigned Managed Identity) resource is provisioned by Rubens' Terraform IaC "azure-iac" project, and attached to every Azure Container App resource. Since UAMI is a resource, it has a Client ID, Resource ID, and Principal Object ID.

- The Client ID is used for authentication
- The Resource ID fully qualifies the Azure resource. It is a fully-qualified name separated by "/" that contains the Subscription Id, Resource Group ID, and the Resource ID.
- The Principal ID (Object ID) which is used when assigning an RBAC role to the resource

**Notes**:

1. A UAMI has an independent lifecycle.  You create, manage and delete an UAMI independently of the other resources (e.g., Virtual Machine, ACA, Key Vault).
2. A shared UAMI can be assigned to multiple resources (e.g., Azure Container Apps).  This enables the assignment of the same RBAC roles to a cluster of resources (e.g., all ACAs share the UAMI, and its assigned RBAC roles)

### RBAC Roles

<!-- # How do Azure Container Apps get permission to read the Key Vault secret?
#
# All Azure Container Apps provisioned by Rubens' Terraform azure-iac
# project is assigned a shared UAMI (User-Assigned Managed Identiry),
# also provisioned by the same project.  This UAMI is granted a RBAC role
# permission ("Key Vault Secrets User") to read Key Vault secrets.

# Where the vaulr_url should come from?
#
# KEY_VAULT_URI : environment variable set in every Azure Container App
# by Rubens' Terraform azure-iac project that contains the URI of the
# shared Key Vault store (e.g., https://kv-rgomes-lab.vault.azure.net/) -->


### Tenant, Management Group, Subscription, Resource Group

These are organizational containers that define boundaries in the Azure system.

- Tenant: the top-level identity and security boundary.  It represents a single organization.  It houses users, groups and application registrations
- Management Group: governance container used to efficiently manage access, policies, and compliance across multiple subscriptions at once. If you have 50 subscriptions and want to apply the same Azure Policy or RBAC permissions to all of them, you place those subscriptions inside a Management Group and apply the rule there.
- Subscription: logical billing and management agreement boundary that links your Azure account to your Azure resources.  Every single Azure resource must belong to exactly one subscription. Subscriptions define how you are billed for resource usage and serve as a primary scale limit boundary.
- Resource Group: logical container used to group, deploy, and manage a collection of actual Azure resources.  A Resource Group has its own Azure location (region), but this is strictly used to store the deployment metadata for the items inside it. The actual resources inside that group can reside in entirely different geographic regions.


