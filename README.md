# tap-dynamics-bc

`tap-dynamics-bc` is a Singer tap for dynamics-bc.

Built with the [Meltano Tap SDK](https://sdk.meltano.com) for Singer Taps.

## Installation

- [ ] `Developer TODO:` Update the below as needed to correctly describe the install procedure. For instance, if you do not have a PyPi repo, or if you want users to directly install from your git repo, you can modify this step as appropriate.

```bash
pipx install tap-dynamics-bc
```

## Configuration

### Accepted Config Options

| Setting             | Required | Default | Description |
|:--------------------|:--------:|:-------:|:------------|
| client_secret       | True     | None    | The client secret of the application you registered to access Dynamics Business Central. |
| client_id           | True     | None    | The client id of the application you registered to access Dynamics Business Central. |
| tenant              | True     | None    | Your Tenant ID (also known as a Directory ID). |
| start_date          | True     | None    | The earliest record date to sync |
| environment_name    | True     | production | The name of the environment you wish to access in Dynamics Business Central. You can view your environments at https://businesscentral.dynamics.com/YOUR_TENANT_ID/admin |
| stream_maps         | False    | None    | Config object for stream maps capability. |
| stream_map_config   | False    | None    | User-defined config values to be used within map expressions. |
| flattening_enabled  | False    | None    | 'True' to enable schema flattening and automatically expand nested properties. |
| flattening_max_depth| False    | None    | The max depth to flatten schemas. |

A full list of supported settings and capabilities for this
tap is available by running:

```bash
tap-dynamics-bc --about
```

### Source Authentication and Authorization

#### Setting Up OAuth 2.0

To use tap-dynamics-bc with OAuth, complete the following steps:
1. Go to https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade and click "New Registration".
1. Enter a name of your choice, select "Single tenant", and enter a "Web" redirect URI of `https://businesscentral.dynamics.com/OAuthLanding.htm`. Click "Register". 
1. You will be taken to an Overview page for your new application. Note the Client ID and Tenant ID you are presented with. These are supplied to the tap through the `client_id` and `tenant` configuration options.
1. In the left menu, select "API Permissions". Click "Add a Permission", then "Dynamics 365 Business Central", then "Application permissions".
1. Select the "API.ReadWrite.All" permission and click "Add permissions".
1. Click the "Grant admin consent button". If prompted, confirm your grant of admin consent.
1. In the left menu, select "Certificates & Secrets". If the "Client secrets" tab is not selected, select it.
1. Click "New client secret". Enter a name and expiry date of your choice, then click "Add".
1. Note down the string of text provided in the "Value" column for your new secret. This is your Client Secret, and is supplied to the tap through the `client_secret` configuration option. You will not be able to view this value again once you navigate away from this page, so be sure you have it stored securly before moving on.
1. Go to https://businesscentral.dynamics.com/ and click on the search icon in the upper right. Search for "Entra" and select "Microsoft Entra Applications".
1. Click "New", then paste in your Client ID and a description of your choice. Switch "State" to Enabled.
1. Add a new permission and select "D365 READ".
1. In the upper left, click "Grant Consent" and follow the prompts in the pop-up window to grant consent to the application you created earlier.
1. You're done! Make sure that you have provided the tap with an appropriate `client_id`, `tenant`, and `client_secret`, then run the tap.


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
