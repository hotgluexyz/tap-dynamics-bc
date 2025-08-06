"""Stream type classes for tap-dynamics-bc."""

import json
from typing import Optional, cast, Any, Dict
from urllib.parse import urlencode
import requests
from singer_sdk import typing as th
from singer_sdk.exceptions import FatalAPIError

from tap_dynamics_bc.client import dynamicsBcStream, DynamicsBCODataStream


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

    def _sync_children(self, child_context: dict):
        if child_context is not None:
            super()._sync_children(child_context)

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
        th.Property("state", th.StringType),
        th.Property("country", th.StringType),
        th.Property("postalCode", th.StringType),
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
    expand = "purchaseInvoiceLines, dimensionSetLines, purchaseInvoiceLines($expand=dimensionSetLines)"

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
        th.Property(
            "dimensionSetLines",
            th.ArrayType(
                th.ObjectType(
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
    expand = "defaultDimensions"

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
        th.Property("defaultDimensions", th.ArrayType(
            th.ObjectType(
                th.Property("id", th.StringType),
                th.Property("dimensionId", th.StringType),
                th.Property("dimensionCode", th.StringType),
                th.Property("dimensionValueId", th.StringType),
                th.Property("dimensionValueCode", th.StringType),
                th.Property("lastModifiedDateTime", th.DateTimeType),
                
            )
        )),
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



class VendorPaymentJournalsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "vendor_payment_journals"
    path = "/companies({company_id})/vendorPaymentJournals"
    primary_keys = ["id"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("code", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("balancingAccountId", th.StringType),
        th.Property("balancingAccountNumber", th.StringType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()



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
        th.Property("lastModifiedDateTime", th.DateTimeType),
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
    synced_doc_nos = set()

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

    def _call_api(self, url):
        # Use proper authentication headers
        headers = self.http_headers
        if self.authenticator:
            headers.update(self.authenticator.auth_headers or {})

        # Use prepare_request for consistent authentication and retry logic
        prepared_request = cast(
            requests.PreparedRequest,
            self.requests_session.prepare_request(
                requests.Request(
                    method="GET",
                    url=url,
                    headers=headers,
                ),
            ),
        )
        # Use the SDK's request method with all retry logic
        decorated_request = self.request_decorator(self._request)
        response = decorated_request(prepared_request, {})
        return response

    def make_request(self, context, next_page_token):
        """Make request with fallback logic for dimension expansion failures."""        
        try:
            prepared_request = self.prepare_request(
                context, next_page_token=next_page_token
            )
            resp = self._request(prepared_request, context)
            return resp
        except FatalAPIError as e:
            if "Dimension Value does not exist" in str(e):
                return self._handle_dimension_failure(e, prepared_request)
            else:
                # Re-raise the error if it's not dimension-related
                raise

    def _handle_dimension_failure(self, error, prepared_request):
        """Handle dimension expansion failure by fetching data in batches."""
        self.logger.warning(
            f"Dimension expansion failed for {self.name}: {str(error)}. "
            "Now trying to fetch GL entries in batches of 200."
        )
        
        base_url = prepared_request.url.split('?')[0]
        gl_ids_resp = self._fetch_gl_ids(prepared_request)
        gl_ids = [_gl_id["id"] for _gl_id in gl_ids_resp.json()["value"]]
        
        all_gls = self._fetch_gl_entries_in_batches(base_url, gl_ids)
        return self._create_enriched_response(gl_ids_resp, all_gls)

    def _fetch_gl_ids(self, prepared_request):
        """Fetch only GL entry IDs to minimize data transfer."""
        ids_url = prepared_request.url.replace('expand=dimensionSetLines', 'select=id')
        return self._call_api(ids_url)

    def _fetch_gl_entries_in_batches(self, base_url, gl_ids, batch_size=200):
        """Fetch GL entries with dimensions in batches."""
        all_gls = []
        
        for i in range(0, len(gl_ids), batch_size):
            batch = gl_ids[i:i+batch_size]
            batch_entries = self._fetch_batch_with_dimensions(base_url, batch, i, len(gl_ids))
            all_gls.extend(batch_entries)
            
        return all_gls

    def _fetch_batch_with_dimensions(self, base_url, batch_ids, batch_index, total_ids):
        """Attempt to fetch a batch of GL entries with dimensions."""
        filter_clause = ' or '.join([f"id eq {id}" for id in batch_ids])
        batch_url = f"{base_url}?{urlencode({'$filter': filter_clause, '$expand': 'dimensionSetLines'})}"
        
        try:
            batch_resp = self._call_api(batch_url)
            self.logger.info(f"Batch {batch_index} of {total_ids} fetched successfully")
            return batch_resp.json()["value"]
        except Exception as e:
            self.logger.warning(f"Failed to fetch batch with dimensions: {str(e)}")
            return self._fetch_batch_without_dimensions(base_url, batch_ids, filter_clause, batch_index)

    def _fetch_batch_without_dimensions(self, base_url, batch_ids, filter_clause, batch_index):
        """Fallback: fetch batch without dimensions, then add dimensions individually."""
        try:
            gl_resp = self._call_api(f"{base_url}?{urlencode({'$filter': filter_clause})}")
            gl_entries = gl_resp.json()["value"]
            
            for gl_entry in gl_entries:
                gl_entry["dimensionSetLines"] = self._fetch_individual_dimensions(base_url, gl_entry['id'])
                
            return gl_entries
        except Exception as e:
            self.logger.warning(f"Failed to fetch GL entries for batch {batch_index}: {str(e)}")
            return []

    def _fetch_individual_dimensions(self, base_url, gl_entry_id):
        """Fetch dimensions for a single GL entry."""
        try:
            dimensions_resp = self._call_api(f"{base_url}({gl_entry_id})/dimensionSetLines")
            return dimensions_resp.json()["value"]
        except Exception as e:
            self.logger.warning(f"Failed to fetch dimensions for GL entry {gl_entry_id}: {str(e)}")
            return []

    def _create_enriched_response(self, original_response, enriched_data):
        """Create a response object with enriched GL entries data."""
        data = original_response.json()
        data["value"] = enriched_data
        original_response._content = json.dumps(data).encode()
        return original_response

    def get_child_context(self, record, context):
        return {
            "gl_entry_id": record["id"], 
            "company_id": context["company_id"], 
            "company_name": context["company_name"], 
            "gl_doc_no": record["documentNumber"]
        }

    def _sync_children(self, child_context: dict):
        # Document number is used as the foreign key in the vendorLedgerEntries Stream
        # So we want to make sure we only sync once per document number

        for child_stream in self.child_streams:
            if child_stream.selected or child_stream.has_selected_descendents:
                should_not_sync = child_stream.name == "vendor_ledger_entries" and child_context["gl_doc_no"] in self.synced_doc_nos
                if not should_not_sync:
                    child_stream.sync(context=child_context)
                    self.synced_doc_nos.add(child_context["gl_doc_no"])

class GLEntriesDimensionsStream(dynamicsBcStream):
    """Define custom stream."""

    name = "gl_entries_dimensions"
    path = "/companies({company_id})/generalLedgerEntries({gl_entry_id})/dimensionSetLines"
    primary_keys = ["id", "gl_entry_id"]
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

class CustomersStream(dynamicsBcStream):
    """Define custom stream."""

    name = "customers"
    path = "/companies({company_id})/customers"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("number", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("type", th.StringType),
        th.Property("addressLine1", th.StringType),
        th.Property("addressLine2", th.StringType),
        th.Property("city", th.StringType),
        th.Property("state", th.StringType),
        th.Property("country", th.StringType),
        th.Property("postalCode", th.StringType),
        th.Property("phoneNumber", th.StringType),
        th.Property("email", th.StringType),
        th.Property("website", th.StringType),
        th.Property("salespersonCode", th.StringType),
        th.Property("balanceDue", th.NumberType),
        th.Property("creditLimit", th.NumberType),
        th.Property("taxLiable", th.BooleanType),
        th.Property("taxAreaId", th.StringType),
        th.Property("taxAreaDisplayName", th.StringType),
        th.Property("taxRegistrationNumber", th.StringType),
        th.Property("currencyId", th.StringType),
        th.Property("currencyCode", th.StringType),
        th.Property("paymentTermsId", th.StringType),
        th.Property("shipmentMethodId", th.StringType),
        th.Property("paymentMethodId", th.StringType),
        th.Property("blocked", th.StringType),
        th.Property("balance", th.NumberType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("irs1099Code", th.StringType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}

class CurrenciesStream(dynamicsBcStream):
    """Define custom stream."""

    name = "currencies"
    path = "/companies({company_id})/currencies"
    primary_keys = ["id"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("code", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("symbol", th.StringType),
        th.Property("amountDecimalPlaces", th.StringType),
        th.Property("amountRoundingPrecision", th.NumberType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()

    def get_child_context(self, record, context):
        return {"company_id": context["company_id"], "company_name": context["company_name"]}

class PaymentTermsStream(dynamicsBcStream):
    """Define custom stream for payment terms."""

    name = "payment_terms"
    path = "/companies({company_id})/paymentTerms"
    primary_keys = ["id"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("code", th.StringType),
        th.Property("displayName", th.StringType),
        th.Property("dueDateCalculation", th.StringType),
        th.Property("discountDateCalculation", th.StringType),
        th.Property("discountPercent", th.NumberType),
        th.Property("calculateDiscountOnCreditMemos", th.BooleanType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()


class VendorLedgerEntriesStream(DynamicsBCODataStream):
    """Define custom stream."""

    """Warning:
    This stream requires enabling an API endpoing for Vendor Ledger Entries with path /VendorLedgerEntries
    and objectID = 29
    You can do this in Web Services Modal in Dynamics BC
    """
    
    name = "vendor_ledger_entries"
    path = "/Company('{company_name}')/VendorLedgerEntries"
    primary_keys = ["Document_No", "company_id"]
    parent_stream_type = GeneralLedgerEntriesStream

    def get_url_params(
        self, context: Optional[dict], next_page_token
    ):
        """Return a dictionary of values to be used in URL parameterization."""
        params = super().get_url_params(context, next_page_token)
        params.update({"$filter": f"Document_No eq '{context['gl_doc_no']}'"})
        return params

    schema = th.PropertiesList(
        th.Property("Entry_No", th.IntegerType),
        th.Property("Transaction_No", th.IntegerType),
        th.Property("Vendor_No", th.StringType),
        th.Property("Posting_Date", th.DateType),
        th.Property("Due_Date", th.DateType),
        th.Property("Pmt_Discount_Date", th.DateType),
        th.Property("Document_Date", th.DateType),
        th.Property("Document_Type", th.StringType),
        th.Property("Document_No", th.StringType),
        th.Property("Purchaser_Code", th.StringType),
        th.Property("Source_Code", th.StringType),
        th.Property("Reason_Code", th.StringType),
        th.Property("IC_Partner_Code", th.StringType),
        th.Property("Open", th.BooleanType),
        th.Property("Currency_Code", th.StringType),
        th.Property("Dimension_Set_ID", th.IntegerType),
        th.Property("Amount", th.NumberType),
        th.Property("Debit_Amount", th.NumberType),
        th.Property("Credit_Amount", th.NumberType),
        th.Property("Remaining_Amount", th.NumberType),
        th.Property("Amount_LCY", th.NumberType),
        th.Property("Debit_Amount_LCY", th.NumberType),
        th.Property("Credit_Amount_LCY", th.NumberType),
        th.Property("Remaining_Amt_LCY", th.NumberType),
        th.Property("Original_Amt_LCY", th.NumberType),
        th.Property("Vendor_Name", th.StringType),
        th.Property("AuxiliaryIndex1", th.StringType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType)
    ).to_dict()
