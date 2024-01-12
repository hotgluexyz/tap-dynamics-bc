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
    PurchaseOrdersStream,
    MetadataStream,
    DimensionsStream,
    UnitsOfMeasureStream
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
    PurchaseOrdersStream,
    MetadataStream,
    DimensionsStream,
    UnitsOfMeasureStream
]


class TapdynamicsBc(Tap):
    """dynamics-bc tap class."""

    name = "tap-dynamics-bc"

    # TODO: Update this section with the actual config values you expect:
    config_jsonschema = th.PropertiesList(
        th.Property(
            "access_token",
            th.StringType,
            required=False,
        ),
        th.Property(
            "refresh_token",
            th.StringType,
            required=False,
        ),
        th.Property(
            "client_secret",
            th.StringType,
            required=False,
        ),
        th.Property(
            "client_id",
            th.StringType,
            required=False,
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            required=False,
            description="The earliest record date to sync",
        ),
        th.Property(
            "environment_name",
            th.StringType,
            required=False,
        ),
        th.Property(
            "username",
            th.StringType,
            required=False,
        ),
        th.Property(
            "password",
            th.StringType,
            required=False,
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""

        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


if __name__ == "__main__":
    TapdynamicsBc.cli()
