# tap-dynamics-bc

`tap-dynamics-bc` is a Singer tap for dynamics-bc.

Built with the [Meltano Tap SDK](https://sdk.meltano.com) for Singer Taps.

## Installation

- [ ] `Developer TODO:` Update the below as needed to correctly describe the install procedure. For instance, if you do not have a PyPi repo, or if you want users to directly install from your git repo, you can modify this step as appropriate.

```bash
pipx install tap-dynamics-bc
```

## Configuration

The tap authenticates with Dynamics 365 Business Central via Microsoft OAuth 2.0 using a refresh token. The following config options are supported:

| Name | Required | Description | Example |
|------|----------|-------------|---------|
| `client_id` | Yes | Azure AD application (client) ID for the OAuth app registered against Business Central. | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `client_secret` | Yes | Client secret for the Azure AD application. | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `refresh_token` | Yes | OAuth refresh token obtained for the user. The tap exchanges it for an access token on each run and rewrites the new refresh token back into the config file. | `1.AQ...xxxxxxxxxxxxxxxxxxxxxxxx` |
| `start_date` | Yes | Earliest record date to sync, in ISO 8601 format. Used to filter incremental streams on first sync. | `2024-01-01T00:00:00.000Z` |
| `environment_name` | Yes | Business Central environment name (case-insensitive). The tap looks this up against the tenant's environment list and rejects unknown values. | `Production` |
| `access_token` | No | Cached OAuth access token. Usually written by the tap after a refresh; you do not need to set it manually. | `eyJ0eXAiOi...` |
| `redirect_uri` | No | OAuth redirect URI used during the original consent. Required only if your Azure AD app enforces a specific value at refresh time. | `https://hotglue.xyz/callback` |
| `company_ids` | No | Restrict the sync to a subset of BC companies, matched by company `id` or `name`. When omitted, all companies the user has access to are synced. | `["Example Company A", "Example Company B"]` |
| `enable_odata_discovery` | No | When `true`, fetch the BC OData V4 `$metadata` document and append a stream per entity set to the discovered catalog. Defaults to `false` (catalog contains only the hand-written REST streams). See [Dynamic OData Discovery](#dynamic-odata-discovery). | `true` |
| `odata_discovery_include_prefixes` | No | If set, only OData entity sets whose name starts with one of these prefixes are surfaced. Useful to scope the catalog to a specific extension. | `["AGBI"]` |
| `odata_discovery_exclude_prefixes` | No | OData entity sets whose name starts with one of these prefixes are skipped. Empty by default — see the [recommended exclusions](#recommended-exclusions) below for a curated list of noisy built-in surfaces. | `["Power_BI_", "ExcelTemplate"]` |

### Notes

- `start_date` only affects streams that have a valid timestamp replication key (`SystemModifiedAt` or `lastModifiedDateTime`). Streams without one fall back to full-table replication.
- Token refresh persists the new `refresh_token` and `access_token` back to the config file, so subsequent runs re-use them without prompting.

### Example config

```json
{
  "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "refresh_token": "1.AQ...xxxxxxxxxxxxxxxxxxxxxxxx",
  "start_date": "2024-01-01T00:00:00.000Z",
  "environment_name": "Production",
  "enable_odata_discovery": true,
  "odata_discovery_include_prefixes": ["AGBI"]
}
```

## Dynamic OData Discovery

By default, the tap exposes a fixed set of streams built on the Business Central **REST API** (`/api/v2.0/`). When `enable_odata_discovery` is `true`, the tap additionally fetches the tenant's **OData V4** `$metadata` document (`/ODataV4/$metadata`) and appends one stream per entity set declared there. This surfaces tables published as Web Services in BC — including standard ledgers, Power BI views, custom extension tables (e.g. `AGBI*`), and any custom-published page exposed via OData.

### How it works

1. At discover time the tap fetches `$metadata` once using the same OAuth token used by the rest of the tap.
2. The EDMX is parsed: every `<EntitySet>` becomes a stream, with primary keys pulled from `<Key>`, JSON Schema generated from each `<Property>`'s `Type`, and `parent_stream_type` set to `CompaniesStream` so the stream is fetched once per company.
3. A replication key is auto-detected: if the entity has a property named `SystemModifiedAt` or `lastModifiedDateTime` typed as `Edm.DateTime` / `Edm.DateTimeOffset`, the stream is `INCREMENTAL`; otherwise `FULL_TABLE`.
4. The discovered streams are filtered:
   - Streams whose name matches a hand-written stream are skipped (no duplicates / no shadowing of curated logic).
   - `odata_discovery_include_prefixes`, when set, restricts the result to matching names.
   - `odata_discovery_exclude_prefixes`, when set, removes streams whose name starts with one of those prefixes.

### Recommended exclusions

By default the tap surfaces every entity set the BC tenant publishes. That can include several built-in groups that are rarely useful for ETL. Most users will want to set `odata_discovery_exclude_prefixes` to skip them:

```json
"odata_discovery_exclude_prefixes": ["Power_BI_", "ExcelTemplate", "Accountant", "workflow"]
```

What each prefix covers:

- `Power_BI_*` — denormalized views used by the BC Power BI content packs.
- `ExcelTemplate*` — backing data for the BC "Edit in Excel" report templates.
- `Accountant*` — UI cues for the Accountant Hub role center.
- `workflow*` — approval-workflow projections that duplicate standard entities (and sometimes lack incremental-friendly timestamps).

These are intentionally **not** excluded by default — `enable_odata_discovery: true` is an explicit opt-in, so the tap surfaces everything the tenant publishes and lets the integrator decide what to drop.

## Usage

You can easily run `tap-dynamics-bc` by itself or in a pipeline using [Meltano](https://meltano.com/).

### Executing the Tap Directly

```bash
tap-dynamics-bc --version
tap-dynamics-bc --help
tap-dynamics-bc --config CONFIG --discover > ./catalog.json
```

## Developer Resources

- [ ] `Developer TODO:` As a first step, scan the entire project for the text "`TODO:`" and complete any recommended steps, deleting the "TODO" references once completed.

### Initialize your Development Environment

```bash
pipx install poetry
poetry install
```

### Create and Run Tests

Create tests within the `tap_dynamics_bc/tests` subfolder and
  then run:

```bash
poetry run pytest
```

You can also test the `tap-dynamics-bc` CLI interface directly using `poetry run`:

```bash
poetry run tap-dynamics-bc --help
```

### Testing with [Meltano](https://www.meltano.com)

_**Note:** This tap will work in any Singer environment and does not require Meltano.
Examples here are for convenience and to streamline end-to-end orchestration scenarios._

Your project comes with a custom `meltano.yml` project file already created. Open the `meltano.yml` and follow any _"TODO"_ items listed in
the file.

Next, install Meltano (if you haven't already) and any needed plugins:

```bash
# Install meltano
pipx install meltano
# Initialize meltano within this directory
cd tap-dynamics-bc
meltano install
```

Now you can test and orchestrate using Meltano:

```bash
# Test invocation:
meltano invoke tap-dynamics-bc --version
# OR run a test `elt` pipeline:
meltano elt tap-dynamics-bc target-jsonl
```

### SDK Dev Guide

See the [dev guide](https://sdk.meltano.com/en/latest/dev_guide.html) for more instructions on how to use the SDK to 
develop your own taps and targets.
