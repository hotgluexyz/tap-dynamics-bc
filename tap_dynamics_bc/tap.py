"""dynamics-bc tap class."""

from typing import List

from hotglue_singer_sdk import Stream, Tap
from hotglue_singer_sdk import typing as th

from tap_dynamics_bc.auth import TapDynamicsBCAuth
from tap_dynamics_bc.discover import discover_dynamic_streams

from tap_dynamics_bc.streams import (
    AccountsStream,
    CompaniesStream,
    CompanyInformationStream,
    ItemsStream,
    LocationsStream,
    PurchaseInvoicesStream,
    SalesInvoicesStream,
    SalesCreditStream,
    VendorPurchases,
    VendorsStream,
    SalesOrdersStream,
    GeneralLedgerEntriesStream,
    GeneralLedgerEntriesIncrementalStream,
    GLEntriesDimensionsStream,
    DimensionsStream,
    DimensionValuesStream,
    CustomersStream,
    CurrenciesStream,
    VendorPaymentJournalsStream,
    PaymentTermsStream,
    VendorLedgerEntriesStream
)

STREAM_TYPES = [
    CompaniesStream,
    CompanyInformationStream,
    ItemsStream,
    VendorsStream,
    VendorPurchases,
    SalesInvoicesStream,
    SalesCreditStream,
    PurchaseInvoicesStream,
    AccountsStream,
    LocationsStream,
    SalesOrdersStream,
    GeneralLedgerEntriesStream,
    GeneralLedgerEntriesIncrementalStream,
    GLEntriesDimensionsStream,
    DimensionsStream,
    DimensionValuesStream,
    CustomersStream,
    CurrenciesStream,
    VendorPaymentJournalsStream,
    PaymentTermsStream,
    VendorLedgerEntriesStream
]


class TapdynamicsBc(Tap):
    """dynamics-bc tap class."""

    def __init__(
        self,
        config=None,
        catalog=None,
        state=None,
        parse_env_config=False,
        validate_config=True,
    ) -> None:
        self.config_file = config[0]
        super().__init__(config, catalog, state, parse_env_config, validate_config)

    name = "tap-dynamics-bc"

    @classmethod
    def access_token_support(cls, connector=None):
        """Return authenticator class and auth endpoint for token refresh."""
        authenticator = TapDynamicsBCAuth
        auth_endpoint = "https://login.microsoftonline.com/common/oauth2/token"
        return authenticator, auth_endpoint

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
            required=True,
        ),
        th.Property(
            "client_secret",
            th.StringType,
            required=True,
        ),
        th.Property(
            "client_id",
            th.StringType,
            required=True,
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
        ),
        th.Property(
            "company_ids",
            th.ArrayType(th.StringType),
            required=False,
        ),
        th.Property(
            "enable_odata_discovery",
            th.BooleanType,
            required=False,
            default=False,
            description=(
                "When true, fetch the BC OData V4 $metadata document and "
                "append a stream per entity set to the discovered catalog."
            ),
        ),
        th.Property(
            "odata_discovery_include_prefixes",
            th.ArrayType(th.StringType),
            required=False,
            description=(
                "If set, only OData entity sets whose name starts with one "
                "of these prefixes are added (e.g. ['AGBI'])."
            ),
        ),
        th.Property(
            "odata_discovery_exclude_prefixes",
            th.ArrayType(th.StringType),
            required=False,
            description=(
                "OData entity sets whose name starts with one of these "
                "prefixes are skipped. E.g. ['Power_BI_', 'ExcelTemplate', "
                "'Accountant', 'workflow']."
            ),
        ),
    ).to_dict()

    # OData entity-set names already covered by the hand-written REST streams
    # in STREAM_TYPES. Skipped during dynamic discovery so the catalog doesn't
    # ship two streams for the same logical entity.
    #   companies               <-> Company
    #   sales_orders            <-> SalesOrder
    #   general_ledger_entries  <-> G_LEntries
    #   accounts                <-> Chart_of_Accounts
    #   vendor_ledger_entries   <-> VendorLedgerEntries (same OData endpoint)
    STATIC_STREAM_ODATA_NAMES = frozenset({
        "Company",
        "SalesOrder",
        "G_LEntries",
        "Chart_of_Accounts",
        "VendorLedgerEntries",
    })

    def discover_streams(self) -> List[Stream]:
        """Return the static stream list, optionally extended via OData discovery."""
        streams: List[Stream] = [stream_class(tap=self) for stream_class in STREAM_TYPES]

        if not self.config.get("enable_odata_discovery", False):
            return streams

        include_prefixes = self.config.get("odata_discovery_include_prefixes")
        exclude_prefixes = self.config.get("odata_discovery_exclude_prefixes")

        # Skip both the curated OData equivalents and the raw static stream names.
        # The latter is a safeguard so we don't ship two streams with the same name.
        static_names = {
            cls.name for cls in STREAM_TYPES if getattr(cls, "name", None)
        }
        skip_names = self.STATIC_STREAM_ODATA_NAMES | static_names

        dynamic_streams = discover_dynamic_streams(
            self,
            parent_stream_type=CompaniesStream,
            include_prefixes=include_prefixes,
            exclude_prefixes=exclude_prefixes,
            skip_names=skip_names,
        )
        return streams + dynamic_streams


if __name__ == "__main__":
    TapdynamicsBc.cli()
