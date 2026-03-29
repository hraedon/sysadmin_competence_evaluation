import httpx
import logging
import base64
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class GuacamoleClient:
    def __init__(self, base_url: str, username: str, password: str, dataSource: str = "postgresql"):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.dataSource = dataSource
        self.token: Optional[str] = None

    async def _authenticate(self):
        """Authenticates with Guacamole and retrieves an auth token."""
        url = f"{self.base_url}/api/tokens"
        data = {
            "username": self.username,
            "password": self.password
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            if response.status_code == 200:
                self.token = response.json().get("authToken")
                logger.info("Successfully authenticated with Guacamole")
            else:
                logger.error(f"Failed to authenticate with Guacamole: {response.text}")
                self.token = None # Clear token if auth fails
                raise Exception("Guacamole authentication failed")

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Helper to make authenticated requests with automatic retry on 401."""
        if not self.token:
            await self._authenticate()

        url = f"{self.base_url}{path}"
        if "?" in url:
            url += f"&token={self.token}"
        else:
            url += f"?token={self.token}"

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            
            # If 401, token might be expired or Guacamole might have restarted
            if response.status_code == 401:
                logger.warning("Guacamole request returned 401. Retrying with fresh token.")
                await self._authenticate()
                # Re-build URL with new token
                url = f"{self.base_url}{path}"
                if "?" in url:
                    url += f"&token={self.token}"
                else:
                    url += f"?token={self.token}"
                response = await client.request(method, url, **kwargs)

            return response

    def _client_url(self, connection_id: str) -> str:
        """Returns the Guacamole web client URL for a given connection ID, including auth token."""
        client_identifier = base64.b64encode(
            f"{connection_id}\x00c\x00{self.dataSource}".encode()
        ).decode()
        
        url = self.base_url
        if not url.endswith('/'):
            url += '/'
            
        if self.token:
            url += f"?token={self.token}"
            
        url += f"#/client/{client_identifier}"
        return url

    async def create_connection(self, name: str, protocol: str, parameters: Dict[str, str]) -> tuple[str, str]:
        """
        Creates a connection in Guacamole and returns (identifier, web_client_url).
        """
        path = f"/api/session/data/{self.dataSource}/connections"
        payload = {
            "name": name,
            "protocol": protocol,
            "parameters": parameters,
            "parentIdentifier": "ROOT",
            "attributes": {},
        }

        response = await self._request("POST", path, json=payload)
        if response.status_code == 200:
            conn_id = response.json().get("identifier")
            logger.info(f"Created Guacamole connection '{name}' with ID {conn_id}")
            return conn_id, self._client_url(conn_id)
        else:
            logger.error(f"Failed to create Guacamole connection: {response.text}")
            raise Exception("Guacamole connection creation failed")

    async def delete_connection(self, identifier: str):
        """Deletes a connection from Guacamole."""
        path = f"/api/session/data/{self.dataSource}/connections/{identifier}"

        response = await self._request("DELETE", path)
        if response.status_code == 204:
            logger.info(f"Deleted Guacamole connection {identifier}")
        else:
            logger.error(f"Failed to delete Guacamole connection: {response.text}")
            # Consider raising here so teardown marks the environment faulted if connection leak occurs
            raise Exception(f"Failed to delete Guacamole connection {identifier}")

    # ------------------------------------------------------------------
    # SEC-07: Per-session restricted users
    # ------------------------------------------------------------------

    async def create_session_user(self, session_id: str, connection_id: str) -> tuple[str, str]:
        """Create a temporary Guacamole user restricted to a single connection.

        Returns (username, password) for the session user.
        """
        import secrets
        username = f"session-{session_id[:12]}"
        password = secrets.token_urlsafe(24)

        # Create user
        user_path = f"/api/session/data/{self.dataSource}/users"
        user_payload = {
            "username": username,
            "password": password,
            "attributes": {
                "disabled": "",
                "expired": "",
                "access-window-start": "",
                "access-window-end": "",
                "valid-from": "",
                "valid-until": "",
            }
        }
        response = await self._request("POST", user_path, json=user_payload)
        if response.status_code != 200:
            logger.error(f"Failed to create Guacamole session user: {response.text}")
            raise Exception(f"Failed to create Guacamole session user '{username}'")

        # Grant read permission on the connection
        perm_path = f"/api/session/data/{self.dataSource}/users/{username}/permissions"
        perm_payload = [
            {
                "op": "add",
                "path": f"/connectionPermissions/{connection_id}",
                "value": "READ",
            }
        ]
        response = await self._request("PATCH", perm_path, json=perm_payload)
        if response.status_code != 204:
            logger.warning(f"Failed to grant connection permission to session user: {response.text}")
            # Clean up the user we just created
            await self.delete_session_user(username)
            raise Exception(f"Failed to grant permissions to session user '{username}'")

        logger.info(f"Created session user '{username}' with access to connection {connection_id}")
        return username, password

    async def delete_session_user(self, username: str):
        """Delete a temporary session user from Guacamole."""
        path = f"/api/session/data/{self.dataSource}/users/{username}"
        response = await self._request("DELETE", path)
        if response.status_code == 204:
            logger.info(f"Deleted Guacamole session user '{username}'")
        else:
            logger.warning(f"Failed to delete Guacamole session user '{username}': {response.text}")

    def _session_client_url(self, connection_id: str, token: str) -> str:
        """Returns the Guacamole web client URL using a session-specific token."""
        client_identifier = base64.b64encode(
            f"{connection_id}\x00c\x00{self.dataSource}".encode()
        ).decode()

        url = self.base_url
        if not url.endswith('/'):
            url += '/'
        url += f"?token={token}#/client/{client_identifier}"
        return url

    async def authenticate_session_user(self, username: str, password: str) -> str:
        """Authenticate a session user and return the auth token.

        The token is scoped to the session user's permissions — no admin access.
        Caller is responsible for building the client URL via _session_client_url().
        """
        url = f"{self.base_url}/api/tokens"
        data = {"username": username, "password": password}
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
        if response.status_code != 200:
            raise Exception(f"Session user auth failed for '{username}'")

        token = response.json().get("authToken")
        # We don't know connection_id here — caller must build the URL
        return token
