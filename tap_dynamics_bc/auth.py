"""TapDynamicsFinance Authentication."""


from typing import Optional
from singer import utils
from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta
from singer_sdk.streams import Stream as RESTStreamBase


# The SingletonMeta metaclass makes your streams reuse the same authenticator instance.
# If this behaviour interferes with your use-case, you can remove the metaclass.
class TapDynamicsBCAuth(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for TapDynamicsFinance."""

    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the TapDynamicsFinance API."""
        return {
            "client_id": self.config["client_id"],
            "scope": "https://api.businesscentral.dynamics.com/.default",
            "client_secret": self.config["client_secret"],
            "grant_type": "client_credentials",
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
    def create_for_stream(cls, stream: RESTStreamBase) -> "TapDynamicsBCAuth":
        return cls(
            stream=stream,
            auth_endpoint=f"https://login.microsoftonline.com/{stream.config['tenant']}/oauth2/v2.0/token",
            default_expiration=3600
        )
