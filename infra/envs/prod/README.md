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

Production resource group: `rg-cad-prod-uksouth` (Task 16).

## Core resources (Task 16)

| Resource | Name | Notes |
|----------|------|--------|
| Resource group | `rg-cad-prod-uksouth` | `azurerm_resource_group.prod` |
| Container registry | `acrcadprod` | `admin_enabled = false` — AcrPull via MI (Task 18) |
| Key Vault | `kv-cad-prod-uks` | RBAC; no secrets in TF; unused KV integrations off; optional IP deny via `key_vault_allowed_ip_ranges` |

After apply, set the upstream weather API key manually (not in git or TF):

```bash
az keyvault secret set --vault-name kv-cad-prod-uks --name OPENWEATHERMAP_API_KEY --value "<your-key>"
```

Verify plan (requires bootstrap + `backend.hcl` + `ARM_USE_AZUREAD=true`):

```powershell
$env:ARM_USE_AZUREAD = "true"
terraform plan
```

Outputs: `terraform output acr_name`, `key_vault_name`, `acr_login_server`, `container_app_fqdn`, `security_notes`.

### Task 16 security (v1)

| Control | Setting |
|---------|---------|
| ACR admin user | `admin_enabled = false` (AcrPull via MI in Task 18) |
| ACR network | Basic SKU — public endpoint for CI push; private link deferred |
| KV auth | `rbac_authorization_enabled = true` (no access policies) |
| KV secrets in TF | None — manual `OPENWEATHERMAP_API_KEY` only |
| KV integrations | Deployment/template/disk encryption disabled |
| KV network | `Allow` + RBAC by default; set `key_vault_allowed_ip_ranges` in `terraform.tfvars` for Deny-by-default |
| KV purge protection | Off (easier teardown); enable for long-lived prod if needed |

## Core resources (Task 17)

| Resource | Name | Notes |
|----------|------|--------|
| Container Apps environment | `cae-cad-prod-uksouth` | Consumption profile (default) |
| Container app | `ca-weather-api-prod` | Public HTTPS ingress; `min_replicas=1`, `max_replicas=3` |
| Health probes | `/health/live`, `/health/ready` | Port **8000** (matches uvicorn bind) |
| Ingress | HTTPS only | `allow_insecure_connections = false` |
| HSTS | `ENABLE_HSTS=true` | App emits Strict-Transport-Security behind ACA TLS |
| Image | `container_image` var | Default MCR quickstart placeholder until CI deploy (Tasks 21–22); validated at TF boundary |

Task 18 adds system-assigned MI, AcrPull, `WEATHER_PROVIDER=openweathermap`, and Key Vault secret ref.

## Next tasks

- **Task 18–19:** Runtime MI + secrets, GitHub OIDC
