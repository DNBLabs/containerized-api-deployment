# Production Terraform stack (`infra/envs/prod`)

Main infrastructure for the tracer API in Azure. Uses **remote state** in the storage account created by [`infra/bootstrap`](../../bootstrap/README.md) (ADR 0001).

## Security (v1)

| Control | Setting |
|---------|---------|
| Remote state auth | `use_azuread_auth = true` in `backend.hcl` — **no storage account keys** in repo |
| Provider data plane | `storage_use_azuread = true` (matches bootstrap; required when state SA has keys disabled) |
| Secrets in git | `backend.hcl` and `terraform.tfvars` are **gitignored** — use `.example` templates only |
| State sensitivity | `prod.terraform.tfstate` blob may contain secrets after Task 16+ — never commit `*.tfstate*` |
| Operator RBAC | **Storage Blob Data Contributor** on bootstrap storage account (not subscription Owner for daily use) |
| CI (Task 19) | `id-cad-github-prod` — prod RG scoped; state store needs separate Blob Data Contributor for Terraform |

Run `terraform output security_notes` after apply for a machine-readable checklist.

## Prerequisites

1. Bootstrap applied: `cd ../../bootstrap && terraform apply`
2. `az login` and subscription selected
3. **Storage Blob Data Contributor** on the bootstrap storage account (for backend access)
4. Copy `backend.hcl.example` → `backend.hcl` and set values from bootstrap outputs:

```bash
cd ../../bootstrap
terraform output -json backend_config
```

## Initialize remote backend

**PowerShell (Windows):** Entra ID backend auth requires:

```powershell
cd infra/envs/prod
$env:ARM_USE_AZUREAD = "true"
terraform init -backend-config=backend.hcl -reconfigure
terraform validate
```

**Bash:**

```bash
cd infra/envs/prod
export ARM_USE_AZUREAD=true
terraform init -backend-config=backend.hcl -reconfigure
terraform validate
```

Copy `backend.hcl.example` → `backend.hcl` if missing; values must match `terraform output -json backend_config` from `infra/bootstrap`.

**First-time 403 on init?** Grant yourself **Storage Blob Data Contributor** on the bootstrap storage account (role propagation ~15s), then re-run init:

```powershell
$uid = az ad signed-in-user show --query id -o tsv
$scope = az storage account show -n <storage_account_name> -g rg-cad-tfstate-uksouth --query id -o tsv
az role assignment create --role "Storage Blob Data Contributor" --assignee $uid --scope $scope
```

Re-init after changing `backend.hcl`:

```bash
terraform init -backend-config=backend.hcl -reconfigure
```

## CI / tests without Azure backend

```bash
terraform init -backend=false
terraform validate
```

Covered by `app/tests/test_prod_terraform.py`.

## Variables (CONTEXT)

| Variable | Default | Purpose |
|----------|---------|---------|
| `location` | `uksouth` | Azure region |
| `prefix` | `cad` | Resource name prefix |
| `environment` | `prod` | Environment segment |
| `tags` | see `variables.tf` | Resource tags |

Planned resource group: `rg-cad-prod-uksouth` (created in Task 16).

## Next tasks

- **Task 16:** `azurerm_resource_group`, ACR, Key Vault
- **Task 17–19:** ACA, identities, OIDC
