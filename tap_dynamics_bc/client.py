"""REST client handling, including dynamics-bcStream base class."""

from typing import Any, Dict, Optional, cast

import requests
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream
from requests_ntlm import HttpNtlmAuth

from tap_dynamics_bc.auth import TapDynamicsBCAuth


class dynamicsBcStream(RESTStream):
    """dynamics-bc stream class."""

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        url_template = "https://api.businesscentral.dynamics.com/v2.0/{}/api/v2.0"
        return url_template.format(self.config.get("environment_name", "production"))

    records_jsonpath = "$.value[*]"
    next_page_token_jsonpath = "$.next_page"
    expand = None

    @property
    def authenticator(self) -> TapDynamicsBCAuth:
        """Return a new authenticator object."""
        return TapDynamicsBCAuth.create_for_stream(self)

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        return headers

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
        if self.next_page_token_jsonpath:
            all_matches = extract_jsonpath(
                self.next_page_token_jsonpath, response.json()
            )
            first_match = next(iter(all_matches), None)
            next_page_token = first_match
        else:
            next_page_token = response.headers.get("X-Next-Page", None)

        return next_page_token

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        if next_page_token:
            params["page"] = next_page_token
        if self.replication_key:
            start_date = self.get_starting_timestamp(context)
            date = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["$filter"] = f"{self.replication_key} gt {date}"
        if self.expand:
            params["$expand"] = self.expand
        return params


    def prepare_request(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> requests.PreparedRequest:
        http_method = self.rest_method
        url: str = self.get_url(context)
        params: dict = self.get_url_params(context, next_page_token)
        request_data = self.prepare_request_payload(context, next_page_token)
        headers = self.http_headers

        authenticator = self.authenticator
        auth = None

        if self.config.get("client_id") and authenticator:
            headers.update(authenticator.auth_headers or {})
            params.update(authenticator.auth_params or {})
        
        elif self.config.get("username"):
            auth = HttpNtlmAuth(self.config.get("username"), self.config.get("password"))

        request = cast(
            requests.PreparedRequest,
            self.requests_session.prepare_request(
                requests.Request(
                    method=http_method,
                    url=url,
                    params=params,
                    headers=headers,
                    json=request_data,
                    auth=auth
                ),
            ),
        )
        return request


