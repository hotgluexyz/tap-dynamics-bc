"""Stream type classes for tap-dynamics-bc."""

from typing import Optional, cast, Iterable, Any

import requests
from singer_sdk import typing as th
from singer_sdk.exceptions import FatalAPIError

from tap_dynamics_bc.client import dynamicsBcStream
from requests_ntlm import HttpNtlmAuth
from singer_sdk.helpers.jsonpath import extract_jsonpath
import xmltodict
import os

class MetadataStream(dynamicsBcStream):
    """Define custom stream."""

    name = "metadata"
    path = "/$metadata"
    replication_key = None
    records_jsonpath = "$.value[*]"

    schema = th.PropertiesList(
        th.Property("Name", th.StringType),
        th.Property("Kind", th.StringType),
        th.Property("Key", th.ArrayType(th.CustomType({"type": ["object", "string"]}))),
        th.Property("Properties", th.CustomType({"type": ["object", "string"]})),
    ).to_dict()

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
        return None

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        content_type = response.headers.get("Content-Type")
        if "xml" in content_type:
            type = "xml"
        elif "json" in content_type:
            type = "json"
        
        #output metadata file
        job_id = os.environ.get("JOB_ID")
        self.logger.info("Writing metadata file")
        xml_file = open(f"/home/hotglue/{job_id}/sync-output/metadata.{type}", "w")
        n = xml_file.write(response.text)
        xml_file.close()
        return []

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
        headers = None
        auth = None
        if self.config.get("client_id") and self.authenticator:
            headers = self.http_headers
            headers.update(self.authenticator.auth_headers or {})
        elif self.config.get("username"):
            if self.config.get("basic_auth"):
                self.logger.info("using basic auth")
                auth = (self.config.get("username"), self.config.get("password"))
            else:
                self.logger.info("using Ntlm auth")
                auth = HttpNtlmAuth(self.config.get("username"), self.config.get("password"))


        prepared_request = cast(
            requests.PreparedRequest,
            self.requests_session.prepare_request(
                requests.Request(
                    method="GET",
                    url=url,
                    params=self.get_url_params(context, None),
                    headers=headers,
                    auth=auth
                ),
            ),
        )

        try:
            resp = decorated_request(prepared_request, context)
            context = {"company_id": record["id"]}
        except FatalAPIError:
            self.logger.warning(
                f"Company unacessible: '{record['name']}' ({record['id']})."
            )
            context = None
        return context
    
    def _sync_children(self, child_context: dict) -> None:
        for child_stream in self.child_streams:
            if child_stream.selected or child_stream.has_selected_descendents:
                if child_context is not None:
                    child_stream.sync(context=child_context)


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
    ).to_dict()


class ItemsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "items"
    path = "/companies({company_id})/items"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream

    @property
    def expand(self):
        if self.auth_type == "OAuth":
            return "itemCategory,picture"

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
    ).to_dict()


class DimensionsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "dimensions"
    path = "/companies({company_id})/dimensions"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream

    @property
    def expand(self):
        return "dimensionValues"
    
    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("code", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("dimensionValues", th.ArrayType(
            th.ObjectType(
                th.Property("id", th.StringType),
                th.Property("code", th.StringType),
                th.Property("dimensionId", th.StringType),
                th.Property("displayName", th.StringType), 
                th.Property("lastModifiedDateTime", th.DateTimeType), 
            )
        )),
        th.Property("company_id", th.StringType),
    ).to_dict()


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
                    th.Property("quantity", th.IntegerType),
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
    ).to_dict()


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
                    th.Property("quantity", th.IntegerType),
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
    ).to_dict()


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
    ).to_dict()


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
    ).to_dict()


class AccountsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "accounts"
    path = "/companies({company_id})/accounts"
    primary_keys = ["id"]
    replication_key = "lastModifiedDateTime"
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
    ).to_dict()


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
    ).to_dict()

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
                    th.Property("quantity", th.IntegerType),
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
    ).to_dict()

class PurchaseOrdersStream(dynamicsBcStream):
    """Define custom stream."""

    name = "purchase_orders"
    path = "/companies({company_id})/wsiPurchaseOrders"
    primary_keys = ["Id"]
    replication_key = None
    parent_stream_type = CompaniesStream
    expand = "wsiPurchaseOrderLines"

    schema = th.PropertiesList(
        th.Property("Id", th.StringType),
        th.Property("Document_Type", th.StringType),
        th.Property("No", th.StringType),
        th.Property("Buy_from_Vendor_No", th.DateType),
        th.Property("Your_Reference", th.DateType),
        th.Property("Vendor_Invoice_No", th.StringType),
        th.Property("Vendor_Order_No", th.StringType),
        th.Property("Expected_Receipt_Date", th.StringType),
        th.Property("No_Series", th.StringType),
        th.Property("wsiPurchaseOrderLines", th.ArrayType(
            th.ObjectType(
                th.Property("Document_Type", th.StringType),
                th.Property("Document_No", th.StringType),
                th.Property("LineNo", th.StringType),
                th.Property("Type", th.StringType),
                th.Property("No", th.StringType),
                th.Property("Quantity", th.StringType),
                th.Property("Direct_Unit_Cost", th.StringType),
                th.Property("Document_NoLink", th.StringType),
            )
        )),
        th.Property("Buy_from_Vendor_NoLink", th.CustomType({"type": ["object", "string"]})),
        th.Property("company_id", th.StringType),
    ).to_dict()


class UnitsOfMeasureStream(dynamicsBcStream):
    """Define custom stream."""

    name = "unit_of_measure"
    path = "/companies({company_id})/unitsOfMeasure"
    primary_keys = ["id"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("code", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("internationalStandardCode", th.StringType),
        th.Property("symbol", th.StringType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
    ).to_dict()
