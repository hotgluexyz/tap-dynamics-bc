"""REST client handling, including dynamics-bcStream base class."""

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import requests
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream

from tap_dynamics_bc.auth import TapDynamicsBCAuth
from backports.cached_property import cached_property
import copy
from singer_sdk.exceptions import FatalAPIError, RetriableAPIError
import singer
from singer import StateMessage


class dynamicsBcStream(RESTStream):
    """dynamics-bc stream class."""
    envs_list = None

    @cached_property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        url_template = "https://api.businesscentral.dynamics.com/v2.0/{}/api/v2.0"
        env_name = self.config.get("environment_name", "production")
        if "?" in env_name:
            env_name = env_name.split("?")
            if isinstance(env_name,list):
                env_name = env_name[0]
        self.validate_env(env_name)        
        return url_template.format(env_name)

    records_jsonpath = "$.value[*]"
    next_page_token_jsonpath = "$.['@odata.nextLink']"
    expand = None

    def get_environments_list(self):
        if self.envs_list:
            return self.envs_list
        headers = {}
        authenticator = self.authenticator
        if authenticator:
            headers.update(authenticator.auth_headers or {})
        envs_list = requests.get(url="https://api.businesscentral.dynamics.com/environments/v1.1",headers=headers)
        self.validate_response(envs_list)
        envs_list = envs_list.json()
        self.envs_list = envs_list
        return self.envs_list
        

    def validate_env(self,env_name):
        env_name = env_name.lower()
        envs_list = self.get_environments_list()
        if "value" in envs_list:
            for env in envs_list['value']:
                #Check for valid environment name is provided. Tenant ID is optional for requesting companies etc.
                if env['name'].lower() in env_name:
                    return True
                    
        raise Exception("Invalid environment name provided.")    
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
            next_page_link = first_match

            # Parse the URL
            parsed_url = urlparse(next_page_link)
            # Extract the query parameters
            query_params = parse_qs(parsed_url.query)
            aid_value = query_params.get('aid')
            skiptoken_value = query_params.get('$skiptoken')
            # If $skiptoken exists, get its first value (as it can be a list)
            if aid_value and skiptoken_value:
                if type(aid_value) == list:
                    aid_value = aid_value[0]
                if type(skiptoken_value) == list:
                    skiptoken_value = skiptoken_value[0]
                return "&aid=" + aid_value + "&$skiptoken=" + skiptoken_value

        return None

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        if self.replication_key:
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

    def make_request(self, context, next_page_token):
        prepared_request = self.prepare_request(
            context, next_page_token=next_page_token
        )
        resp = self._request(prepared_request, context)
        return resp
    
    def request_records(self, context: Optional[dict]):
        next_page_token: Any = None
        finished = False
        decorated_request = self.request_decorator(self.make_request)

        while not finished:
            resp = decorated_request(context, next_page_token)
            for row in self.parse_response(resp):
                yield row
            previous_token = copy.deepcopy(next_page_token)
            next_page_token = self.get_next_page_token(
                response=resp, previous_token=previous_token
            )
            if next_page_token and next_page_token == previous_token:
                raise RuntimeError(
                    f"Loop detected in pagination. "
                    f"Pagination token {next_page_token} is identical to prior token."
                )
            # Cycle until get_next_page_token() no longer returns a value
            finished = not next_page_token

    def validate_response(self, response: requests.Response) -> None:
        if response.status_code in [401]:
            msg = (
                f"{response.status_code} Server Error: "
                f"{response.reason} for path: {self.path} with response {response.text}"
            )
            raise RetriableAPIError(msg)
        elif response.status_code == 400 and "Please try again later." in response.text:
            msg = (
                f"{response.status_code} Server Error: "
                f"{response.reason} for path: {self.path} with response {response.text}"
            )
            raise RetriableAPIError(msg)
        elif 400 <= response.status_code < 500:
            msg = (
                f"{response.status_code} Client Error: "
                f"{response.reason} for path: {self.path} with response {response.text}"
            )
            raise FatalAPIError(msg)
        elif 500 <= response.status_code < 600 or response.status_code in [401]:
            msg = (
                f"{response.status_code} Server Error: "
                f"{response.reason} for path: {self.path} with response {response.text}"
            )
            raise RetriableAPIError(msg)
    
    def _write_state_message(self) -> None:
        """Write out a STATE message with the latest state."""
        tap_state = self.tap_state

        if tap_state and tap_state.get("bookmarks"):
            for stream_name in tap_state.get("bookmarks").keys():
                if stream_name in [
                    "gl_entries_dimensions",
                ] and tap_state["bookmarks"][stream_name].get("partitions"):
                    tap_state["bookmarks"][stream_name] = {"partitions": []}

        singer.write_message(StateMessage(value=tap_state))
