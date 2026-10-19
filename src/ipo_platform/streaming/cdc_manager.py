"""
Debezium Connector Management Client.
Interacts with the Kafka Connect REST API to register, monitor, and manage the CDC pipeline.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class DebeziumManagerError(Exception):
    """Raised when connector registration or health check fails."""
    pass


class DebeziumConnectorManager:
    """Manages Kafka Connect Debezium connector registration and health verification."""

    def __init__(self, connect_url: str = "http://localhost:8083") -> None:
        self.connect_url = connect_url.rstrip("/")

    @staticmethod
    def load_connector_config(config_path: str) -> Dict[str, Any]:
        """Loads and validates a connector JSON configuration file."""
        p = Path(config_path)
        if not p.exists():
            raise FileNotFoundError(f"Debezium connector config file not found: {config_path}")

        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as err:
                raise ValueError(f"Invalid JSON in connector configuration: {err}") from err

        if "name" not in data or "config" not in data:
            raise ValueError("Connector configuration must contain 'name' and 'config' keys")

        cfg = data["config"]
        required_keys = ["connector.class", "database.hostname", "topic.prefix"]
        for k in required_keys:
            if k not in cfg:
                raise ValueError(f"Missing required Debezium configuration key: '{k}'")

        return data

    def check_health(self) -> Dict[str, Any]:
        """Checks if Kafka Connect REST endpoint is responding."""
        url = f"{self.connect_url}/connectors"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                status_code = response.getcode()
                body = json.loads(response.read().decode("utf-8"))
                return {
                    "status": "HEALTHY" if status_code == 200 else "UNHEALTHY",
                    "connectors": body,
                }
        except Exception as err:
            logger.warning(f"Kafka Connect health probe failed at {url}: {err}")
            return {
                "status": "UNHEALTHY",
                "error": str(err),
            }

    def register_connector(self, connector_config: Dict[str, Any]) -> Dict[str, Any]:
        """Registers or updates a connector with the Kafka Connect cluster."""
        name = connector_config["name"]
        url = f"{self.connect_url}/connectors"

        # Check if already exists
        check_url = f"{url}/{name}"
        req_check = urllib.request.Request(check_url, method="GET")
        exists = False
        try:
            with urllib.request.urlopen(req_check, timeout=5) as resp:
                if resp.getcode() == 200:
                    exists = True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                exists = False
            else:
                raise DebeziumManagerError(f"Error checking connector existence: {e}") from e
        except Exception as err:
            raise DebeziumManagerError(f"Kafka Connect cluster unreachable: {err}") from err

        if exists:
            # Update existing configuration
            config_url = f"{check_url}/config"
            data_bytes = json.dumps(connector_config["config"]).encode("utf-8")
            req = urllib.request.Request(
                config_url,
                data=data_bytes,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="PUT",
            )
        else:
            # Create new connector
            data_bytes = json.dumps(connector_config).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                return res_body
        except Exception as err:
            raise DebeziumManagerError(f"Failed to register connector '{name}': {err}") from err
