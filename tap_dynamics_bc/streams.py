"""Stream type classes for tap-dynamics-bc."""

import json
from typing import Optional, cast, Any, Dict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
import requests
from hotglue_singer_sdk import typing as th
from hotglue_singer_sdk.exceptions import FatalAPIError
import datetime
from tap_dynamics_bc.client import (
    BC_DEFAULT_MODIFIED_SENTINEL,
    dynamicsBcStream,
    DynamicsBCODataStream,
    DynamicsBCAnalyticsStream,
)
from dateutil.relativedelta import relativedelta
import pendulum
import re

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
            decorated_request(prepared_request, context)
            if (
                len(self.config.get("company_ids", [])) > 0 
                and record["id"] not in self.config.get("company_ids") 
                and record['name'] not in self.config.get("company_ids")
            ):
                return None
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
    page_size = 1000

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


class _InvoiceDimensionExpansionMixin:
    """Fallback when $expand=dimensionSetLines fails on invoice document streams."""

    lines_property: str

    _DIMENSION_EXPANSION_ERROR_MARKERS = (
        "Dimension Value does not exist",
        "Parent with ID",
    )

    def _is_dimension_expansion_error(self, error: Exception) -> bool:
        message = str(error)
        return any(marker in message for marker in self._DIMENSION_EXPANSION_ERROR_MARKERS)

    def _call_api(self, url):
        headers = self.http_headers
        if self.authenticator:
            headers.update(self.authenticator.auth_headers or {})

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
        decorated_request = self.request_decorator(self._request)
        return decorated_request(prepared_request, {})

    def _make_request_with_dimension_fallback(self, context, next_page_token):
        try:
            prepared_request = self.prepare_request(
                context, next_page_token=next_page_token
            )
            return self._request(prepared_request, context)
        except FatalAPIError as error:
            if self._is_dimension_expansion_error(error):
                return self._handle_dimension_failure(error, prepared_request)
            raise

    def _handle_dimension_failure(self, error, prepared_request):
        """Handle dimension expansion failure by fetching invoices in batches."""
        self.logger.warning(
            "Dimension expansion failed for %s: %s. "
            "Now trying to fetch records in batches of 200.",
            self.name,
            error,
        )

        base_url = prepared_request.url.split("?")[0]
        ids_resp = self._fetch_record_ids(prepared_request)
        record_ids = [record["id"] for record in ids_resp.json()["value"]]
        enriched_records = self._fetch_records_in_batches(base_url, record_ids)
        return self._create_enriched_response(ids_resp, enriched_records)

    def _fetch_record_ids(self, prepared_request):
        """Fetch only record IDs to minimize data transfer."""
        parsed = urlparse(prepared_request.url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params.pop("$expand", None)
        params["$select"] = ["id"]
        ids_url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
        return self._call_api(ids_url)

    def _fetch_records_in_batches(self, base_url, record_ids, batch_size=200):
        all_records = []

        for index in range(0, len(record_ids), batch_size):
            batch = record_ids[index : index + batch_size]
            batch_records = self._fetch_batch_with_dimensions(
                base_url, batch, index, len(record_ids)
            )
            all_records.extend(batch_records)

        return all_records

    def _fetch_batch_with_dimensions(self, base_url, batch_ids, batch_index, total_ids):
        """Attempt to fetch a batch of invoices with full dimension expansion."""
        filter_clause = " or ".join([f"id eq {record_id}" for record_id in batch_ids])
        batch_url = f"{base_url}?{urlencode({'$filter': filter_clause, '$expand': self.expand})}"

        try:
            batch_resp = self._call_api(batch_url)
            self.logger.info(
                "Batch %s of %s fetched successfully for %s",
                batch_index,
                total_ids,
                self.name,
            )
            return batch_resp.json()["value"]
        except Exception as error:
            self.logger.warning(
                "Failed to fetch batch with dimensions for %s: %s",
                self.name,
                error,
            )
            return self._fetch_batch_without_dimensions(
                base_url, batch_ids, filter_clause, batch_index
            )

    def _lines_with_dimensions_expand(self) -> str:
        return f"{self.lines_property}($expand=dimensionSetLines)"

    def _fetch_batch_without_dimensions(
        self, base_url, batch_ids, filter_clause, batch_index
    ):
        """Fallback: fetch lines with dimensions, then enrich header dimensions."""
        lines_expand = self._lines_with_dimensions_expand()
        try:
            records_resp = self._call_api(
                f"{base_url}?{urlencode({'$filter': filter_clause, '$expand': lines_expand})}"
            )
            records = records_resp.json()["value"]
        except Exception as error:
            self.logger.warning(
                "Failed to fetch batch with lines and dimensions for %s: %s",
                self.name,
                error,
            )
            try:
                records_resp = self._call_api(
                    f"{base_url}?{urlencode({'$filter': filter_clause})}"
                )
                records = records_resp.json()["value"]
                for record in records:
                    record[self.lines_property] = self._fetch_lines(base_url, record["id"])
            except Exception as inner_error:
                self.logger.warning(
                    "Failed to fetch records for batch %s of %s: %s",
                    batch_index,
                    self.name,
                    inner_error,
                )
                return []

        for record in records:
            self._enrich_record_dimensions(base_url, record)

        return records

    def _enrich_record_dimensions(self, base_url, record):
        record["dimensionSetLines"] = self._fetch_header_dimensions(
            base_url, record["id"]
        )

    def _fetch_lines(self, base_url, record_id):
        lines_expand = self._lines_with_dimensions_expand()
        try:
            record_resp = self._call_api(
                f"{base_url}({record_id})?{urlencode({'$expand': lines_expand})}"
            )
            return record_resp.json().get(self.lines_property, [])
        except Exception as error:
            self.logger.warning(
                "Failed to fetch %s with dimensions for %s record %s: %s",
                self.lines_property,
                self.name,
                record_id,
                error,
            )
            try:
                lines_resp = self._call_api(
                    f"{base_url}({record_id})/{self.lines_property}"
                )
                return lines_resp.json()["value"]
            except Exception as fallback_error:
                self.logger.warning(
                    "Failed to fetch %s for %s record %s: %s",
                    self.lines_property,
                    self.name,
                    record_id,
                    fallback_error,
                )
                return []

    def _fetch_header_dimensions(self, base_url, record_id):
        try:
            dimensions_resp = self._call_api(
                f"{base_url}({record_id})/dimensionSetLines"
            )
            return dimensions_resp.json()["value"]
        except Exception as error:
            self.logger.warning(
                "Failed to fetch header dimensions for %s record %s: %s",
                self.name,
                record_id,
                error,
            )
            return []

    def _create_enriched_response(self, original_response, enriched_data):
        data = original_response.json()
        data["value"] = enriched_data
        original_response._content = json.dumps(data).encode()
        return original_response


class SalesInvoicesStream(_InvoiceDimensionExpansionMixin, dynamicsBcStream):
    """Define custom stream."""

    name = "sales_invoices"
    path = "/companies({company_id})/salesInvoices"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream
    expand = "dimensionSetLines, salesInvoiceLines($expand=dimensionSetLines)"
    lines_property = "salesInvoiceLines"
    page_size = 1000
    _default_page_size = 1000

    @property
    def timeout(self) -> int:
        # lower timeout since we have adaptive page size logic below
        return 120

    def make_request(self, context, next_page_token):
        # Reset page size on each company's first page (one stream instance, many companies).
        if next_page_token is None:
            self.page_size = self._default_page_size
        try:
            return self.make_request_with_adaptive_page_size(context, next_page_token)
        except FatalAPIError as error:
            if self._is_dimension_expansion_error(error):
                prepared_request = self.prepare_request(
                    context, next_page_token=next_page_token
                )
                return self._handle_dimension_failure(error, prepared_request)
            raise

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


class SalesCreditStream(dynamicsBcStream):
    """Define custom stream."""

    name = "sales_credit_memos"
    path = "/companies({company_id})/salesCreditMemos"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream
    expand = "dimensionSetLines, salesCreditMemoLines($expand=dimensionSetLines)"

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("number", th.StringType),
        th.Property("externalDocumentNumber", th.StringType),
        th.Property("creditMemoDate", th.DateType),
        th.Property("postingDate", th.DateType),
        th.Property("dueDate", th.DateType),
        th.Property("customerId", th.StringType),
        th.Property("customerNumber", th.StringType),
        th.Property("customerName", th.StringType),
        th.Property("billToName", th.StringType),
        th.Property("billToCustomerId", th.StringType),
        th.Property("billToCustomerNumber", th.StringType),
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
        th.Property("shortcutDimension1Code", th.StringType),
        th.Property("shortcutDimension2Code", th.StringType),
        th.Property("currencyId", th.StringType),
        th.Property("currencyCode", th.StringType),
        th.Property("paymentTermsId", th.StringType),
        th.Property("shipmentMethodId", th.StringType),
        th.Property("salesperson", th.StringType),
        th.Property("pricesIncludeTax", th.BooleanType),
        th.Property("discountAmount", th.NumberType),
        th.Property("discountAppliedBeforeTax", th.BooleanType),
        th.Property("totalAmountExcludingTax", th.NumberType),
        th.Property("totalTaxAmount", th.NumberType),
        th.Property("totalAmountIncludingTax", th.NumberType),
        th.Property("status", th.StringType),
        th.Property("lastModifiedDateTime", th.DateTimeType),
        th.Property("invoiceId", th.StringType),
        th.Property("invoiceNumber", th.StringType),
        th.Property("phoneNumber", th.StringType),
        th.Property("email", th.StringType),
        th.Property("customerReturnReasonId", th.StringType),
        th.Property(
            "salesCreditMemoLines",
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
                    th.Property("description2", th.StringType),
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


class PurchaseInvoicesStream(_InvoiceDimensionExpansionMixin, dynamicsBcStream):
    """Define custom stream."""

    name = "purchase_invoices"
    path = "/companies({company_id})/purchaseInvoices"
    primary_keys = ["id", "lastModifiedDateTime"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream
    expand = "purchaseInvoiceLines, dimensionSetLines, purchaseInvoiceLines($expand=dimensionSetLines)"
    lines_property = "purchaseInvoiceLines"
    page_size = 1000

    def make_request(self, context, next_page_token):
        return self._make_request_with_dimension_fallback(context, next_page_token)

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
    replication_key = "postingDate"
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
    
    def _is_initial_sync(self, context: dict) -> bool:
        bookmark_date = self.get_starting_timestamp(context)
        configured_start = pendulum.parse(self.config.get("start_date"))
        return bookmark_date == configured_start
    
    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        report_periods = self.config.get("report_periods", 3)

        if not self._is_initial_sync(context):
            today = datetime.date.today()
            beginning_of_month = today.replace(day=1)
            beginning_of_month = datetime.datetime.combine(beginning_of_month, datetime.datetime.min.time())
            date = (beginning_of_month - relativedelta(months=report_periods - 1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.logger.info(f"Not initial sync, fetching GL entries for last {report_periods} months, starting from {date}")
            params["$filter"] = f"{self.replication_key} gt {date}"
        else:
            self.logger.info("Initial sync, fetching GL entries for all time")
            start_date = self.get_starting_timestamp(context)
            if start_date:
                date = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                params["$filter"] = f"{self.replication_key} gt {date}"
            
        if self.expand:
            params["$expand"] = self.expand
        if next_page_token:
            params["aid"] = next_page_token.split("aid=")[-1].split("&")[0]
            params["$skiptoken"] = next_page_token.split("$skiptoken=")[-1]
        return params

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


class GeneralLedgerEntriesIncrementalStream(GeneralLedgerEntriesStream):
    name = "general_ledger_entries_incremental"
    path = "/companies({company_id})/generalLedgerEntries"
    primary_keys = ["id"]
    replication_key = "lastModifiedDateTime"
    parent_stream_type = CompaniesStream
    expand = "dimensionSetLines"
    synced_doc_nos = set()

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        params = dynamicsBcStream.get_url_params(self, context, next_page_token)
        if self._is_initial_sync(context or {}):
            start_date = self.get_starting_timestamp(context)
            if start_date:
                date = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                # Unmodified GL entries use BC's sentinel lastModifiedDateTime, which
                # is before start_date and would be excluded by the default gt filter.
                params["$filter"] = (
                    f"(lastModifiedDateTime gt {date}) or "
                    f"(lastModifiedDateTime eq {BC_DEFAULT_MODIFIED_SENTINEL})"
                )
        return params


class _PostingDateWindowMixin:
    """Shared initial-sync vs rolling-window filter for postingDate streams."""

    def _is_initial_sync(self, context: dict) -> bool:
        bookmark_date = self.get_starting_timestamp(context)
        configured_start = pendulum.parse(self.config.get("start_date"))
        return bookmark_date == configured_start

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        report_periods = self.config.get("report_periods", 3)

        if not self._is_initial_sync(context):
            today = datetime.date.today()
            beginning_of_month = today.replace(day=1)
            beginning_of_month = datetime.datetime.combine(
                beginning_of_month, datetime.datetime.min.time()
            )
            date = (
                beginning_of_month - relativedelta(months=report_periods - 1)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.logger.info(
                f"Not initial sync, fetching GL entries for last {report_periods} "
                f"months, starting from {date}"
            )
            params["$filter"] = f"{self.replication_key} gt {date}"
        else:
            self.logger.info("Initial sync, fetching GL entries for all time")
            start_date = self.get_starting_timestamp(context)
            if start_date:
                date = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                params["$filter"] = f"{self.replication_key} gt {date}"

        if getattr(self, "expand", None):
            params["$expand"] = self.expand
        params["$top"] = self.page_size
        if next_page_token:
            params["$skip"] = next_page_token
        return params


class AnalyticsGeneralLedgerEntriesStream(_PostingDateWindowMixin, DynamicsBCAnalyticsStream):
    """Base stream for microsoft/analytics general ledger entry entities."""

    replication_key = "postingDate"
    parent_stream_type = CompaniesStream


class BalanceSheetGeneralLedgerEntriesStream(AnalyticsGeneralLedgerEntriesStream):
    """Balance sheet G/L entries from the Analytics API."""

    name = "balance_sheet_general_ledger_entries"
    path = "/companies({company_id})/balanceSheetGeneralLedgerEntries"
    primary_keys = ["entryNo", "company_id"]

    schema = th.PropertiesList(
        th.Property("incomeBalance", th.StringType),
        th.Property("glAccountNo", th.StringType),
        th.Property("postingDate", th.DateTimeType),
        th.Property("amount", th.NumberType),
        th.Property("dimensionSetID", th.IntegerType),
        th.Property("sourceCode", th.StringType),
        th.Property("entryNo", th.IntegerType),
        th.Property("systemModifiedAt", th.DateTimeType),
        th.Property("description", th.StringType),
        th.Property("sourceType", th.StringType),
        th.Property("sourceNo", th.StringType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()


class IncomeStatementGeneralLedgerEntriesStream(AnalyticsGeneralLedgerEntriesStream):
    """Income statement G/L entries from the Analytics API."""

    name = "income_statement_general_ledger_entries"
    path = "/companies({company_id})/incomeStatementGeneralLedgerEntries"
    primary_keys = ["entryNo", "company_id"]

    schema = th.PropertiesList(
        th.Property("incomeBalance", th.StringType),
        th.Property("accountNo", th.StringType),
        th.Property("postingDate", th.DateTimeType),
        th.Property("amount", th.NumberType),
        th.Property("dimensionSetID", th.IntegerType),
        th.Property("sourceCode", th.StringType),
        th.Property("entryNo", th.IntegerType),
        th.Property("systemModifiedAt", th.DateTimeType),
        th.Property("description", th.StringType),
        th.Property("sourceType", th.StringType),
        th.Property("sourceNo", th.StringType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()


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

class AccountingPeriodsStream(dynamicsBcStream):
    """Define custom stream for accounting periods."""
    name = "accounting_periods"
    path = "/companies({company_id})/accountingPeriods"
    primary_keys = ["id"]
    replication_key = None
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("id", th.StringType),
        th.Property("startingDate", th.DateType),
        th.Property("name", th.StringType),
        th.Property("newFiscalYear", th.BooleanType),
        th.Property("closed", th.BooleanType),
        th.Property("dateLocked", th.BooleanType),
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
    parent_stream_type = GeneralLedgerEntriesIncrementalStream

    def get_url_params(
        self, context: Optional[dict], next_page_token
    ):
        """Return a dictionary of values to be used in URL parameterization."""
        params = super().get_url_params(context, next_page_token)
        # Only replace single quotes that are not already doubled
        escaped_gl_doc_no = re.sub(r"(?<!')'(?!')", "''", context['gl_doc_no'])
        params.update({"$filter": f"Document_No eq '{escaped_gl_doc_no}'"})
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


class ClosingGeneralLedgerEntriesStream(DynamicsBCAnalyticsStream):

    name = "closing_general_ledger_entries"
    path = "/companies({company_id})/closingGeneralLedgerEntries"
    primary_keys = ["entryNo", "glAccountNo", "company_id"]
    replication_key = "systemModifiedAt"
    parent_stream_type = CompaniesStream

    schema = th.PropertiesList(
        th.Property("entryNo", th.IntegerType),
        th.Property("postingDate", th.DateType),
        th.Property("glAccountNo", th.StringType),
        th.Property("description", th.StringType),
        th.Property("amount", th.NumberType),
        th.Property("dimensionSetID", th.IntegerType),
        th.Property("sourceCode", th.StringType),
        th.Property("sourceType", th.StringType),
        th.Property("sourceNo", th.StringType),
        th.Property("incomeBalance", th.StringType),
        th.Property("systemModifiedAt", th.DateTimeType),
        th.Property("company_id", th.StringType),
        th.Property("company_name", th.StringType),
    ).to_dict()
