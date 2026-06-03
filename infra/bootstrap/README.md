# Terraform bootstrap (Day-0)

Creates Azure Storage for **main-stack** Terraform remote state per [ADR 0001](../../docs/adr/0001-terraform-remote-state-bootstrap.md).

- **State for this module:** local only (`terraform.tfstate` in this directory, gitignored).
- **Region:** `uksouth` (default).
- **Not run from CI** in v1 — operator applies once after `az login`.

## Security (v1)

| Control | Setting |
|---------|---------|
| Transport | HTTPS only, TLS 1.2+ |
| Blob access | Private container; no public nested blobs |
| Account keys | **Disabled** (`shared_access_key_enabled = false`) |
| Backend auth | Azure AD — `use_azuread_auth = true` in main stack (no access keys in repo) |
| Encryption | Infrastructure encryption enabled (platform-managed keys) |
| State sensitivity | Remote state may contain secrets — never commit `*.tfstate*` |
| RBAC | Grant **Storage Blob Data Contributor** on the storage account to your operator identity and `id-cad-github-prod` (Task 19) |

**Network:** v1 keeps the storage public HTTPS endpoint so GitHub OIDC and local Terraform can reach blobs with Entra ID. Anonymous access is off; optional storage firewall / private endpoint is deferred (documented in `terraform output security_notes`).

**Bootstrap apply:** Use `az login` (user/SP with rights to create RGs and storage). Do not put storage keys or SAS tokens in `terraform.tfvars` or git.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- Azure CLI logged in: `az login`
- Subscription set: `az account set --subscription "<subscription-id>"`
- Your identity needs **Storage Blob Data Contributor** (subscription or resource group scope) so Terraform can verify the blob service when account keys are disabled. `Contributor` on a resource group alone is not always enough for data-plane access.

`versions.tf` sets `storage_use_azuread = true` on the provider — required alongside `shared_access_key_enabled = false`.

## Troubleshooting

### `403 KeyBasedAuthenticationNotPermitted` during apply

The storage account was created with keys disabled, but the provider tried key-based auth. Ensure `storage_use_azuread = true` is in the `azurerm` provider block (already in this repo), then re-run:

```bash
terraform apply
```

If the storage account already exists from a failed run, Terraform state should include it; the retry only needs to finish the container.

### `409 StorageAccountAlreadyTaken`

The default name `stcadprodtf` is reserved by another Azure customer. Create `terraform.tfvars` (gitignored):

```hcl
storage_account_name = "stcadprodtf7k2m" # pick your own unique suffix
```

Then `terraform apply`. Update Task 15 backend config with the **actual** name from `terraform output storage_account_name`.

### Partial apply

If apply failed after creating the storage account, run `terraform plan` — you should see only the container (and any missing resources). Do not delete the account manually unless you intend to start over.

## Apply (operator)

```bash
cd infra/bootstrap
terraform init
terraform plan
terraform apply
```

If `storage_account_name` is taken globally, copy `terraform.tfvars.example` to `terraform.tfvars` and set a **unique** name (3–24 lowercase letters/numbers only), e.g. `stcadprodtf7k2m`. Names are unique across all of Azure, not just your subscription.

## Outputs (main stack backend)

After apply:

```bash
terraform output
terraform output -json backend_config
```

Use these values in `infra/envs/prod/backend.hcl` (Task 15 — see [`../envs/prod/README.md`](../envs/prod/README.md)):

| Output | Purpose |
|--------|---------|
| `resource_group_name` | Backend `resource_group_name` |
| `storage_account_name` | Backend `storage_account_name` |
| `container_name` | Backend `container_name` |
| `state_key` | Backend `key` (default `prod.terraform.tfstate`) |
| `backend_config` | Map of all backend fields including `use_azuread_auth` |

Grant the operator and CI identity **Storage Blob Data Contributor** on the storage account (main stack / Task 19).

## Validate (no Azure apply)

```bash
terraform init -backend=false
terraform validate
```

Also covered by `app/tests/test_bootstrap_terraform.py`.

## Teardown

1. Destroy the **main** stack first (`infra/envs/prod`) so state blobs are not needed.
2. Then destroy bootstrap: `terraform destroy` in this directory.

Keep a backup copy of `terraform.tfstate` if you may need to destroy bootstrap resources later (ADR 0001).

## Resources created

| Resource | Default name |
|----------|----------------|
| Resource group | `rg-cad-tfstate-uksouth` |
| Storage account | `stcadprodtf` |
| Blob container | `tfstate` |
