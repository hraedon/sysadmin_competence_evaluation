import httpx
import logging
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

    async def create_connection(self, name: str, protocol: str, parameters: Dict[str, str]) -> str:
        """
        Creates a temporary connection in Guacamole.
        Returns the connection ID or URL.
        """
        if not self.token:
            await self._authenticate()

        url = f"{self.base_url}/api/session/data/{self.dataSource}/connections?token={self.token}"
        
        payload = {
            "name": name,
            "protocol": protocol,
            "parameters": parameters,
            "parentIdentifier": "ROOT"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                conn_id = response.json().get("identifier")
                logger.info(f"Created Guacamole connection '{name}' with ID {conn_id}")
                # Construct the client URL
                return f"{self.base_url}/#/client/{conn_id}"
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
