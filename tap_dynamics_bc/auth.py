"""TapDynamicsFinance Authentication."""


from singer import utils
from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta


# The SingletonMeta metaclass makes your streams reuse the same authenticator instance.
# If this behaviour interferes with your use-case, you can remove the metaclass.
class TapDynamicsBCAuth(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for TapDynamicsFinance."""

    @property
    def auth_headers(self) -> dict:
        if self.config.get("client_id"):
            if not self.is_token_valid():
                self.update_access_token()
            result = super().auth_headers
            result["Authorization"] = f"Bearer {self.access_token}"  
            return result
    
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
