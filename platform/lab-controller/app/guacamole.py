import httpx
import logging
import base64
from typing import Optional, Dict, Any
from pydantic import BaseModel

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
                raise Exception("Guacamole authentication failed")

    def _client_url(self, connection_id: str) -> str:
        """Returns the Guacamole web client URL for a given connection ID, including auth token."""
        client_identifier = base64.b64encode(
            f"{connection_id}\x00c\x00{self.dataSource}".encode()
        ).decode()
        url = f"{self.base_url}/#/client/{client_identifier}"
        if self.token:
            url += f"?token={self.token}"
        return url

    async def create_connection(self, name: str, protocol: str, parameters: Dict[str, str]) -> tuple[str, str]:
        """
        Creates a connection in Guacamole and returns (identifier, web_client_url).
        """
        if not self.token:
            await self._authenticate()

        url = f"{self.base_url}/api/session/data/{self.dataSource}/connections?token={self.token}"

        payload = {
            "name": name,
            "protocol": protocol,
            "parameters": parameters,
            "parentIdentifier": "ROOT",
            "attributes": {},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                conn_id = response.json().get("identifier")
                logger.info(f"Created Guacamole connection '{name}' with ID {conn_id}")
                return conn_id, self._client_url(conn_id)
            else:
                logger.error(f"Failed to create Guacamole connection: {response.text}")
                raise Exception("Guacamole connection creation failed")

    async def delete_connection(self, identifier: str):
        """Deletes a connection from Guacamole."""
        if not self.token:
            await self._authenticate()

        url = f"{self.base_url}/api/session/data/{self.dataSource}/connections/{identifier}?token={self.token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(url)
            if response.status_code == 204:
                logger.info(f"Deleted Guacamole connection {identifier}")
            else:
                logger.error(f"Failed to delete Guacamole connection: {response.text}")
