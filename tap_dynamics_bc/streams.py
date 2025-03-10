"""Stream type classes for tap-dynamics-bc."""

from typing import Any, Dict, Optional, cast
from datetime import datetime, timezone
import dateutil.parser
import requests
from singer_sdk import typing as th
from singer_sdk.exceptions import FatalAPIError

from tap_dynamics_bc.client import dynamicsBcStream


class CompaniesStream(dynamicsBcStream):
    """Define custom stream."""

    name = "companies"
    path = "/companies"
    primary_keys = ["id"]
    replication_key = None

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("systemVersion", th.StringType),
        th.Property("name", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("businessProfileId", th.StringType),
        th.Property("systemCreatedAt", th.DateTimeType),
        th.Property("systemCreatedBy", th.StringType),
        th.Property("systemModifiedAt", th.DateTimeType),
        th.Property("systemModifiedBy", th.StringType),
    ).to_dict()

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        decorated_request = self.request_decorator(self._request)

        url = f"{self.url_base}/companies({record['id']})/companyInformation"
        headers = self.http_headers
        headers.update(self.authenticator.auth_headers or {})

        prepared_request = cast(
            requests.PreparedRequest,
            self.requests_session.prepare_request(
                requests.Request(
                    method="GET",
                    url=url,
                    params=self.get_url_params(context, None),
                    headers=headers,
                ),
            ),
        )

        try:
            resp = decorated_request(prepared_request, context)
            return {"company_id": record["id"], "company_name": record["name"]}
        except FatalAPIError:
            self.logger.warning(
                f"Company unacessible: '{record['name']}' ({record['id']})."
            )


class CompanyInformationStream(dynamicsBcStream):
    """Define custom stream."""

    name = "company_information"
    path = "/companies({company_id})/companyInformation"
    primary_keys = ["id"]
    replication_key = None
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("addressLine1", th.StringType),
        th.Property("addressLine2", th.StringType),
        th.Property("city", th.StringType),
        th.Property("state", th.DateTimeType),
        th.Property("country", th.StringType),
        th.Property("postalCode", th.DateTimeType),
        th.Property("phoneNumber", th.StringType),
        th.Property("faxNumber", th.StringType),
        th.Property("email", th.StringType),
        th.Property("website", th.StringType),
        th.Property("taxRegistrationNumber", th.StringType),
        th.Property("currencyCode", th.StringType),
        th.Property("currentFiscalYearStartDate", th.StringType),
        th.Property("industry", th.StringType),
        th.Property("picture@odata.mediaReadLink", th.StringType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}


class ItemsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "items"
    path = "/companies({company_id})/items"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream
    expand = "itemCategory,picture"

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("number", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("type", th.StringType),
        th.Property("itemCategoryId", th.StringType),
        th.Property("itemCategoryCode", th.StringType),
        th.Property("blocked", th.BooleanType),
        th.Property("gtin", th.StringType),
        th.Property("inventory", th.NumberType),
        th.Property("unitPrice", th.NumberType),
        th.Property("priceIncludesTax", th.BooleanType),
        th.Property("unitCost", th.NumberType),
        th.Property("taxGroupId", th.StringType),
        th.Property("taxGroupCode", th.StringType),
        th.Property("baseUnitOfMeasureId", th.StringType),
        th.Property("baseUnitOfMeasureCode", th.StringType),
        th.Property("generalProductPostingGroupId", th.StringType),
        th.Property("generalProductPostingGroupCode", th.StringType),
        th.Property("inventoryPostingGroupId", th.StringType),
        th.Property("inventoryPostingGroupCode", th.StringType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property(
            "picture",
            th.ObjectType(
                th.Property("id", th.StringType),
                th.Property("parentType", th.StringType),
                th.Property("width", th.IntegerType),
                th.Property("height", th.IntegerType),
                th.Property("contentType", th.StringType),
                th.Property("pictureContent@odata.mediaEditLink", th.StringType),
                th.Property("pictureContent@odata.mediaReadLink", th.StringType),
            ),
        ),
        th.Property(
            "itemCategory",
            th.ObjectType(
                th.Property("id", th.StringType),
                th.Property("code", th.StringType),
                th.Property("displayName", th.StringType),
                th.Property("lastModifiedDateTime", th.DateType),
            ),
        ),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}


class SalesInvoicesStream(dynamicsBcStream):
    """Define custom stream."""

    name = "sales_invoices"
    path = "/companies({company_id})/salesInvoices"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream
    expand = "salesInvoiceLines"

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("number", th.StringType),
        th.Property("externalDocumentNumber", th.StringType),
        th.Property("invoiceDate", th.DateType),
        th.Property("postingDate", th.DateType),
        th.Property("dueDate", th.DateType),
        th.Property("customerPurchaseOrderReference", th.StringType),
        th.Property("customerId", th.StringType),
        th.Property("customerNumber", th.StringType),
        th.Property("customerName", th.StringType),
        th.Property("billToName", th.StringType),
        th.Property("billToCustomerId", th.StringType),
        th.Property("billToCustomerNumber", th.StringType),
        th.Property("shipToName", th.StringType),
        th.Property("shipToContact", th.StringType),
        th.Property("sellToAddressLine1", th.StringType),
        th.Property("sellToAddressLine2", th.StringType),
        th.Property("sellToCity", th.StringType),
        th.Property("sellToCountry", th.StringType),
        th.Property("sellToState", th.StringType),
        th.Property("sellToPostCode", th.StringType),
        th.Property("billToAddressLine1", th.StringType),
        th.Property("billToAddressLine2", th.StringType),
        th.Property("billToCity", th.StringType),
        th.Property("billToCountry", th.StringType),
        th.Property("billToState", th.StringType),
        th.Property("billToPostCode", th.StringType),
        th.Property("shipToAddressLine1", th.StringType),
        th.Property("shipToAddressLine2", th.StringType),
        th.Property("shipToCity", th.StringType),
        th.Property("shipToCountry", th.StringType),
        th.Property("shipToState", th.StringType),
        th.Property("shipToPostCode", th.StringType),
        th.Property("currencyId", th.StringType),
        th.Property("shortcutDimension1Code", th.StringType),
        th.Property("shortcutDimension2Code", th.StringType),
        th.Property("currencyCode", th.StringType),
        th.Property("orderId", th.StringType),
        th.Property("orderNumber", th.StringType),
        th.Property("paymentTermsId", th.StringType),
        th.Property("shipmentMethodId", th.StringType),
        th.Property("salesperson", th.StringType),
        th.Property("pricesIncludeTax", th.BooleanType),
        th.Property("remainingAmount", th.NumberType),
        th.Property("discountAmount", th.NumberType),
        th.Property("discountAppliedBeforeTax", th.BooleanType),
        th.Property("totalAmountExcludingTax", th.NumberType),
        th.Property("totalTaxAmount", th.NumberType),
        th.Property("totalAmountIncludingTax", th.NumberType),
        th.Property("status", th.StringType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("phoneNumber", th.StringType),
        th.Property("email", th.StringType),
        th.Property(
            "salesInvoiceLines",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.StringType),
                    th.Property("documentId", th.StringType),
                    th.Property("sequence", th.IntegerType),
                    th.Property("itemId", th.StringType),
                    th.Property("accountId", th.StringType),
                    th.Property("lineType", th.StringType),
                    th.Property("lineObjectNumber", th.StringType),
                    th.Property("description", th.StringType),
                    th.Property("unitOfMeasureId", th.StringType),
                    th.Property("unitOfMeasureCode", th.StringType),
                    th.Property("unitPrice", th.NumberType),
                    th.Property("quantity", th.NumberType),
                    th.Property("discountAmount", th.NumberType),
                    th.Property("discountPercent", th.NumberType),
                    th.Property("discountAppliedBeforeTax", th.BooleanType),
                    th.Property("amountExcludingTax", th.NumberType),
                    th.Property("taxCode", th.StringType),
                    th.Property("taxPercent", th.NumberType),
                    th.Property("totalTaxAmount", th.NumberType),
                    th.Property("amountIncludingTax", th.NumberType),
                    th.Property("invoiceDiscountAllocation", th.NumberType),
                    th.Property("netAmount", th.NumberType),
                    th.Property("netTaxAmount", th.NumberType),
                    th.Property("netAmountIncludingTax", th.NumberType),
                    th.Property("shipmentDate", th.DateType),
                    th.Property("itemVariantId", th.StringType),
                    th.Property("locationId", th.StringType),
                )
            ),
        ),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}


class PurchaseInvoicesStream(dynamicsBcStream):
    """Define custom stream."""

    name = "purchase_invoices"
    path = "/companies({company_id})/purchaseInvoices"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream
    expand = "purchaseInvoiceLines"

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("number", th.StringType),
        th.Property("invoiceDate", th.DateType),
        th.Property("postingDate", th.DateType),
        th.Property("dueDate", th.DateType),
        th.Property("vendorInvoiceNumber", th.StringType),
        th.Property("vendorId", th.StringType),
        th.Property("vendorNumber", th.StringType),
        th.Property("vendorName", th.StringType),
        th.Property("payToName", th.StringType),
        th.Property("payToContact", th.StringType),
        th.Property("payToVendorId", th.StringType),
        th.Property("payToVendorNumber", th.StringType),
        th.Property("shipToName", th.StringType),
        th.Property("shipToContact", th.StringType),
        th.Property("buyFromAddressLine1", th.StringType),
        th.Property("buyFromAddressLine2", th.StringType),
        th.Property("buyFromCity", th.StringType),
        th.Property("buyFromCountry", th.StringType),
        th.Property("buyFromState", th.StringType),
        th.Property("buyFromPostCode", th.StringType),
        th.Property("shipToAddressLine1", th.StringType),
        th.Property("shipToAddressLine2", th.StringType),
        th.Property("shipToCity", th.StringType),
        th.Property("shipToCountry", th.StringType),
        th.Property("shipToState", th.StringType),
        th.Property("shipToPostCode", th.StringType),
        th.Property("payToAddressLine1", th.StringType),
        th.Property("payToAddressLine2", th.StringType),
        th.Property("payToCity", th.StringType),
        th.Property("payToCountry", th.StringType),
        th.Property("payToState", th.StringType),
        th.Property("payToPostCode", th.StringType),
        th.Property("shortcutDimension1Code", th.StringType),
        th.Property("shortcutDimension2Code", th.StringType),
        th.Property("currencyId", th.StringType),
        th.Property("currencyCode", th.StringType),
        th.Property("orderId", th.StringType),
        th.Property("orderNumber", th.StringType),
        th.Property("pricesIncludeTax", th.BooleanType),
        th.Property("discountAmount", th.NumberType),
        th.Property("discountAppliedBeforeTax", th.BooleanType),
        th.Property("totalAmountExcludingTax", th.NumberType),
        th.Property("totalTaxAmount", th.NumberType),
        th.Property("totalAmountIncludingTax", th.NumberType),
        th.Property("status", th.StringType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property(
            "purchaseInvoiceLines",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.StringType),
                    th.Property("documentId", th.StringType),
                    th.Property("sequence", th.IntegerType),
                    th.Property("itemId", th.StringType),
                    th.Property("accountId", th.StringType),
                    th.Property("lineType", th.StringType),
                    th.Property("lineObjectNumber", th.StringType),
                    th.Property("description", th.StringType),
                    th.Property("unitOfMeasureId", th.StringType),
                    th.Property("unitOfMeasureCode", th.StringType),
                    th.Property("unitCost", th.NumberType),
                    th.Property("quantity", th.NumberType),
                    th.Property("discountAmount", th.NumberType),
                    th.Property("discountPercent", th.NumberType),
                    th.Property("discountAppliedBeforeTax", th.BooleanType),
                    th.Property("amountExcludingTax", th.NumberType),
                    th.Property("taxCode", th.StringType),
                    th.Property("taxPercent", th.NumberType),
                    th.Property("totalTaxAmount", th.NumberType),
                    th.Property("amountIncludingTax", th.NumberType),
                    th.Property("invoiceDiscountAllocation", th.NumberType),
                    th.Property("netAmount", th.NumberType),
                    th.Property("netTaxAmount", th.NumberType),
                    th.Property("netAmountIncludingTax", th.NumberType),
                    th.Property("expectedReceiptDate", th.DateType),
                    th.Property("itemVariantId", th.StringType),
                    th.Property("locationId", th.StringType),
                )
            ),
        ),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}


class VendorsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "vendors"
    path = "/companies({company_id})/vendors"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("number", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("addressLine1", th.StringType),
        th.Property("addressLine2", th.StringType),
        th.Property("city", th.StringType),
        th.Property("state", th.StringType),
        th.Property("country", th.StringType),
        th.Property("postalCode", th.StringType),
        th.Property("phoneNumber", th.StringType),
        th.Property("email", th.StringType),
        th.Property("website", th.StringType),
        th.Property("taxRegistrationNumber", th.StringType),
        th.Property("currencyId", th.StringType),
        th.Property("currencyCode", th.StringType),
        th.Property("irs1099Code", th.StringType),
        th.Property("paymentTermsId", th.StringType),
        th.Property("paymentMethodId", th.StringType),
        th.Property("taxLiable", th.BooleanType),
        th.Property("blocked", th.StringType),
        th.Property("balance", th.NumberType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}


class VendorPurchases(dynamicsBcStream):
    """Define custom stream."""

    name = "vendor_purchases"
    path = "/companies({company_id})/vendorPurchases"
    primary_keys = ["vendorId"]
    replication_key = None
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("vendorId", th.StringType),
        th.Property("vendorNumber", th.StringType),
        th.Property("name", th.StringType),
        th.Property("totalPurchaseAmount", th.NumberType),
        th.Property("dateFilter_FilterOnly", th.StringType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}


class AccountsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "accounts"
    path = "/companies({company_id})/accounts"
    primary_keys = ["id"]
    # replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("number", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("category", th.StringType),
        th.Property("subCategory", th.StringType),
        th.Property("blocked", th.BooleanType),
        th.Property("accountType", th.StringType),
        th.Property("directPosting", th.BooleanType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}


class LocationsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "locations"
    path = "/companies({company_id})/locations"
    primary_keys = ["id"]
    replication_key = None
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("code", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("contact", th.StringType),
        th.Property("addressLine1", th.StringType),
        th.Property("addressLine2", th.StringType),
        th.Property("city", th.StringType),
        th.Property("state", th.StringType),
        th.Property("country", th.StringType),
        th.Property("postalCode", th.StringType),
        th.Property("phoneNumber", th.StringType),
        th.Property("email", th.StringType),
        th.Property("website", th.StringType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}

class SalesOrdersStream(dynamicsBcStream):
    """Define custom stream."""

    name = "sales_orders"
    path = "/companies({company_id})/salesOrders"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream
    expand = "salesOrderLines"

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("number", th.StringType),
        th.Property("externalDocumentNumber", th.StringType),
        th.Property("orderDate", th.DateType),
        th.Property("postingDate", th.DateType),
        th.Property("customerId", th.StringType),
        th.Property("customerNumber", th.StringType),
        th.Property("customerName", th.StringType),
        th.Property("billToName", th.StringType),
        th.Property("billToCustomerId", th.StringType),
        th.Property("billToCustomerNumber", th.StringType),
        th.Property("shipToName", th.StringType),
        th.Property("shipToContact", th.StringType),
        th.Property("sellToAddressLine1", th.StringType),
        th.Property("sellToAddressLine2", th.StringType),
        th.Property("sellToCity", th.StringType),
        th.Property("sellToCountry", th.StringType),
        th.Property("sellToState", th.StringType),
        th.Property("sellToPostCode", th.StringType),
        th.Property("billToAddressLine1", th.StringType),
        th.Property("billToAddressLine2", th.StringType),
        th.Property("billToCity", th.StringType),
        th.Property("billToCountry", th.StringType),
        th.Property("billToState", th.StringType),
        th.Property("billToPostCode", th.StringType),
        th.Property("shipToAddressLine1", th.StringType),
        th.Property("shipToAddressLine2", th.StringType),
        th.Property("shipToCity", th.StringType),
        th.Property("shipToCountry", th.StringType),
        th.Property("shipToState", th.StringType),
        th.Property("shipToPostCode", th.StringType),
        th.Property("shortcutDimension1Code", th.StringType),
        th.Property("shortcutDimension2Code", th.StringType),
        th.Property("currencyId", th.StringType),
        th.Property("currencyCode", th.StringType),
        th.Property("pricesIncludeTax", th.BooleanType),
        th.Property("paymentTermsId", th.StringType),
        th.Property("shipmentMethodId", th.StringType),
        th.Property("salesperson", th.StringType),
        th.Property("partialShipping", th.BooleanType),
        th.Property("requestedDeliveryDate", th.DateType),
        th.Property("discountAmount", th.NumberType),
        th.Property("discountAppliedBeforeTax", th.BooleanType),
        th.Property("totalAmountExcludingTax", th.NumberType),
        th.Property("totalTaxAmount", th.NumberType),
        th.Property("totalAmountIncludingTax", th.NumberType),
        th.Property("fullyShipped", th.BooleanType),
        th.Property("status", th.CustomType({"type": ["object", "string"]})),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("phoneNumber", th.StringType),
        th.Property("email", th.StringType),
        th.Property(
            "salesOrderLines",
            th.ArrayType(
                th.ObjectType(
                    th.Property("id", th.StringType),
                    th.Property("documentId", th.StringType),
                    th.Property("sequence", th.IntegerType),
                    th.Property("itemId", th.StringType),
                    th.Property("accountId", th.StringType),
                    th.Property("lineType", th.StringType),
                    th.Property("lineObjectNumber", th.StringType),
                    th.Property("description", th.StringType),
                    th.Property("unitOfMeasureId", th.StringType),
                    th.Property("unitOfMeasureCode", th.StringType),
                    th.Property("unitPrice", th.NumberType),
                    th.Property("quantity", th.NumberType),
                    th.Property("discountAmount", th.NumberType),
                    th.Property("discountPercent", th.NumberType),
                    th.Property("discountAppliedBeforeTax", th.BooleanType),
                    th.Property("amountExcludingTax", th.NumberType),
                    th.Property("taxCode", th.StringType),
                    th.Property("taxPercent", th.NumberType),
                    th.Property("totalTaxAmount", th.NumberType),
                    th.Property("amountIncludingTax", th.NumberType),
                    th.Property("invoiceDiscountAllocation", th.NumberType),
                    th.Property("netAmount", th.NumberType),
                    th.Property("netTaxAmount", th.NumberType),
                    th.Property("netAmountIncludingTax", th.NumberType),
                    th.Property("shipmentDate", th.DateType),
                    th.Property("itemVariantId", th.StringType),
                    th.Property("locationId", th.StringType),
                )
            ),
        ),        
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
   
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}


class GeneralLedgerEntriesStream(dynamicsBcStream):
    """Define custom stream."""

    name = "general_ledger_entries"
    path = "/companies({company_id})/generalLedgerEntries"
    primary_keys = ["id"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream
    expand = "dimensionSetLines"

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("entryNumber", th.IntegerType),
        th.Property("postingDate", th.DateTimeType),
        th.Property("documentNumber", th.StringType),
        th.Property("documentType", th.StringType),
        th.Property("accountId", th.StringType),
        th.Property("accountNumber", th.StringType),
        th.Property("description", th.StringType),
        th.Property("debitAmount", th.NumberType),
        th.Property("creditAmount", th.NumberType),
        th.Property("additionalCurrencyDebitAmount", th.NumberType),
        th.Property("additionalCurrencyCreditAmount", th.NumberType),
        th.Property("lastModifiedDateTime", th.DateTimeType),        
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
        th.Property("dimensionSetLines", th.ArrayType(
            th.ObjectType(
                th.Property("@odata.etag", th.StringType),
                th.Property("id", th.StringType),
                th.Property("code", th.StringType),
                th.Property("consolidationCode", th.StringType),
                th.Property("parentId", th.StringType),
                th.Property("parentType", th.StringType),
                th.Property("displayName", th.StringType),
                th.Property("valueId", th.StringType),
                th.Property("valueCode", th.StringType),
                th.Property("valueConsolidationCode", th.StringType),
                th.Property("valueDisplayName", th.StringType),
            )
        )),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"gl_entry_id": record["id"], "company_id": context["company_id"], "company_name": context["company_name"]}


class GLEntriesDimensionsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "gl_entries_dimensions"
    path = "/companies({company_id})/generalLedgerEntries({gl_entry_id})/dimensionSetLines"
    primary_keys = ["id"]
    parent_stream_type = GeneralLedgerEntriesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("code", th.StringType),
        th.Property("consolidationCode", th.StringType),
        th.Property("parentId", th.StringType),
        th.Property("parentType", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("valueId", th.StringType),
        th.Property("valueCode", th.StringType),
        th.Property("valueConsolidationCode", th.StringType),
        th.Property("valueDisplayName", th.StringType),
        th.Property("gl_entry_id", th.StringType),
    ).to_dict()

    def validate_response(self, response: requests.Response) -> None:
        if response.status_code == 404:
            self.logger.info(f"Not able to fetch dimensions for url: '{response.url}'. Error: {response.json().get('error', {}).get('message')}")
        else:
            super().validate_response(response)

class DimensionsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "dimensions"
    path = "/companies({company_id})/dimensions"
    primary_keys = ["id"]
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("code", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("lastModifiedDateTime", th.DateTimeType),        
        th.Property("company_id", th.StringType),        
        th.Property("company_name", th.StringType),
    ).to_dict()


    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}

class DimensionValuesStream(dynamicsBcStream):
    """Define custom stream."""

    name = "dimension_values"
    path = "/companies({company_id})/dimensionValues"
    primary_keys = ["id"]
    parent_stream_type = CompaniesStream

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        url_template = "https://api.businesscentral.dynamics.com/v2.0/{}/api/microsoft/reportsFinance/beta"
        env_name = self.config.get("environment_name", "production")
        if "?" in env_name:
            env_name = env_name.split("?")
            if isinstance(env_name, list):
                env_name = env_name[0]
        self.validate_env(env_name)
        return url_template.format(env_name)

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("dimensionCode", th.StringType),
        th.Property("dimensionValueCode", th.StringType),
        th.Property("dimensionValueName", th.StringType),
        th.Property("dimensionValueId", th.IntegerType),
        th.Property("dimensionValueType", th.StringType),
        th.Property("blocked", th.BooleanType),
        th.Property("indentation", th.IntegerType),
        th.Property("consolidationCode", th.StringType),
        th.Property("globalDimensionNumber", th.IntegerType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("company_id", th.StringType),        
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}

class TrialBalanceStream(dynamicsBcStream):
    """Define custom stream."""

    name = "trial_balance"
    path = "/companies({company_id})/trialBalances"
    replication_key = "dateFilter"
    primary_keys = ["id"]
    parent_stream_type = CompaniesStream
    
    schema = th.PropertiesList(
        th.Property("number", th.StringType),
        th.Property("display", th.StringType),
        th.Property("totalDebit", th.StringType),
        th.Property("totalCredit", th.StringType),
        th.Property("balanceAtDateDebit", th.StringType),
        th.Property("balanceAtDateCredit", th.StringType),
        th.Property("dateFilter", th.DateType),
        th.Property("company_id", th.StringType),        
        th.Property("company_name", th.StringType),
    ).to_dict()

    """Overriding due to complex nature of calculating start and end of the year"""
    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""

        params: Dict[str, Any] = {}

        start_date_str = self.config.get("start_date", "2025-01-01T00:00:00.000Z")

        # Convert start_date to a proper datetime object
        start_date = dateutil.parser.parse(start_date_str).date()
        current_date = datetime.now(timezone.utc).date()

        # Determine the year range dynamically
        year = context.get("year", start_date.year)

        start_of_year = f"{year}-01-01"
        if year == current_date.year:
            end_of_year = current_date.strftime("%Y-%m-%dT23:59:59.999Z")
        else:
            end_of_year = f"{year}-12-31"

        params["$filter"] = f"dateFilter ge {start_of_year} and dateFilter le {end_of_year}"

        if self.expand:
            params["$expand"] = self.expand

        if next_page_token:
            params["aid"] = next_page_token.split("aid=")[-1].split("&")[0]
            params["$skiptoken"] = next_page_token.split("$skiptoken=")[-1]

        return params

    """Overriding to iterate over all the years from the given start_date in config"""
    def request_records(self, context: Optional[dict]):
        """Request trial balance data year by year from start_date to the current year."""
        start_date_str = "2010-01-01T00:00:00.000Z"

        # Convert ISO 8601 format to date object
        start_date = dateutil.parser.parse(start_date_str).date()
        current_date = datetime.now(timezone.utc).date()

        year = start_date.year
        while year <= current_date.year:
            context["year"] = year
            next_page_token = None
            finished = False
            decorated_request = self.request_decorator(self.make_request)

            while not finished:
                resp = decorated_request(context, next_page_token)
                for row in self.parse_response(resp):
                    yield row
                
                previous_token = next_page_token
                next_page_token = self.get_next_page_token(resp, previous_token)
                if next_page_token and next_page_token == previous_token:
                    raise RuntimeError(
                        f"Loop detected in pagination. "
                        f"Pagination token {next_page_token} is identical to prior token."
                    )
                finished = not next_page_token

            # Move to next year
            year += 1

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}
