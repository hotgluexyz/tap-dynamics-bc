"""dynamics-bc tap class."""

from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th

from tap_dynamics_bc.streams import (
    AccountsStream,
    CompaniesStream,
    CompanyInformationStream,
    ItemsStream,
    LocationsStream,
    PurchaseInvoicesStream,
    SalesInvoicesStream,
    VendorPurchases,
    VendorsStream,
    SalesOrdersStream,
    GeneralLedgerEntriesStream,
    GLEntriesDimensionsStream,
    DimensionsStream,
    DimensionValuesStream
)

STREAM_TYPES = [
    CompaniesStream,
    CompanyInformationStream,
    ItemsStream,
    VendorsStream,
    VendorPurchases,
    SalesInvoicesStream,
    PurchaseInvoicesStream,
    AccountsStream,
    LocationsStream,
    SalesOrdersStream,
    GeneralLedgerEntriesStream,
    GLEntriesDimensionsStream,
    DimensionsStream,
    DimensionValuesStream
]


class TapdynamicsBc(Tap):
    """dynamics-bc tap class."""

    name = "tap-dynamics-bc"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "client_secret",
            th.StringType,
            required=True,
            description=(
                "The client secret of the application you registered to access "
                "Dynamics Business Central."
            ),
        ),
        th.Property(
            "client_id",
            th.StringType,
            required=True,
            description=(
                "The client id of the application you registered to access Dynamics "
                "Business Central."
            ),
        ),
        th.Property(
            "tenant",
            th.StringType,
            required=True,
            description=(
                "Your Tenant ID (also known as a Directory ID)."
            ),
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            required=True,
            description="The earliest record date to sync",
        ),
        th.Property(
            "environment_name",
            th.StringType,
            required=True,
            default="production",
            description=(
                "The name of the environment you wish to access in Dynamics Business "
                "Central. You can view your environments at "
                "https://businesscentral.dynamics.com/YOUR_TENANT_ID/admin"
            ),
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""

        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


if __name__ == "__main__":
    TapdynamicsBc.cli()
