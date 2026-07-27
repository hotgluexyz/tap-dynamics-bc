from hotglue_smoke_test.vcr.tap import VCRTapTestRunner


class ConnectorTapTestRunner(VCRTapTestRunner):
    # Preserve fields the tap reads from responses for state / next request.
    PRESERVE_KEYS = {
        "id",
        "name",
        "lastModifiedDateTime",
        "@odata.nextLink",
        # OAuth token response — tap does int(expires_in) on replay
        "expires_in",
    }

    def module(self) -> str:
        return "tap_dynamics_bc"

    def launch(self):
        from tap_dynamics_bc.tap import TapdynamicsBc

        TapdynamicsBc.cli()


if __name__ == "__main__":
    ConnectorTapTestRunner.main()
