"""TapDynamicsFinance Authentication."""


from singer import utils
import json
import requests
from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta
from singer_sdk.helpers._util import utc_now
from singer_sdk.streams import Stream as RESTStreamBase
from typing import Optional

# The SingletonMeta metaclass makes your streams reuse the same authenticator instance.
# If this behaviour interferes with your use-case, you can remove the metaclass.
class TapDynamicsBCAuth(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for TapDynamicsFinance."""

    def __init__(
        self,
        stream: RESTStreamBase,
        auth_endpoint: Optional[str] = None,
        oauth_scopes: Optional[str] = None
    ) -> None:
        super().__init__(stream=stream, auth_endpoint=auth_endpoint, oauth_scopes=oauth_scopes)
        self._tap = stream._tap

    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the TapDynamicsFinance API."""
        # TODO: Define the request body needed for the API.
        return {
            # 'resource': 'https://login.microsoftonline.com/common/oauth2/token',
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "redirect_uri": self.config["redirect_uri"],
            "refresh_token": self.config["refresh_token"],
            "grant_type": "refresh_token",
        }

    def is_token_valid(self) -> bool:
        """Check if token is valid.

        Returns:
            True if the token is valid (fresh).
        """
        if self.expires_in is not None:
            self.expires_in = int(self.expires_in)
        if self.last_refreshed is None:
            return False
        if not self.expires_in:
            return True
        if self.expires_in > (utils.now() - self.last_refreshed).total_seconds():
            return True
        return False

    @classmethod
    def create_for_stream(cls, stream) -> "TapDynamicsBCAuth":
        return cls(
            stream=stream,
            auth_endpoint="https://login.microsoftonline.com/common/oauth2/token",
        )

    # Authentication and refresh
    def update_access_token(self) -> None:
        """Update `access_token` along with: `last_refreshed` and `expires_in`.

        Raises:
            RuntimeError: When OAuth login fails.
        """
        request_time = utc_now()
        auth_request_payload = self.oauth_request_payload
        token_response = requests.post(self.auth_endpoint, data=auth_request_payload)
        try:
            token_response.raise_for_status()
            self.logger.info("OAuth authorization attempt was successful.")
        except Exception as ex:
            raise RuntimeError(
                f"Failed OAuth login, response was '{token_response.json()}'. {ex}"
            )
        token_json = token_response.json()
        self.access_token = token_json["access_token"]
        self.expires_in = token_json.get("expires_in", 10)
        if self.expires_in is None:
            self.logger.debug(
                "No expires_in receied in OAuth response and no "
                "default_expiration set. Token will be treated as if it never "
                "expires."
            )
        self.last_refreshed = request_time

        # store access_token in config file
        self._tap._config["access_token"] = token_json["access_token"]
        self._tap._config["refresh_token"] = token_json["refresh_token"]

        with open(self._tap.config_file, "w") as outfile:
            json.dump(self._tap._config, outfile, indent=4)