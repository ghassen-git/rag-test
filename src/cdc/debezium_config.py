
from typing import Dict, Any

import json
import logging
import requests
import time

from src.config import settings
logger = logging.getLogger(__name__)

class DebeziumManager:

    def __init__(self):
        
        self.base_url = settings.debezium_connector_url
        self.postgres_connector = settings.debezium_postgres_connector
        self.mongo_connector = settings.debezium_mongo_connector
    
    def wait_for_debezium(self, max_retries: int = 30, delay: int = 2) -> bool:
        
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/", timeout=5)
                if response.status_code == 200:
                    logger.info("Debezium Connect is ready")
                    return True
            except requests.exceptions.RequestException as e:
                logger.debug(f"Waiting for Debezium (attempt {attempt + 1}/{max_retries}): {e}")
            
            time.sleep(delay)
        
        logger.error("Debezium Connect failed to become ready")
        return False
    
    def create_postgres_connector(self) -> bool:
        
        config = {
            "name": self.postgres_connector,
            "config": {
                "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
                "database.hostname": settings.postgres_host,
                "database.port": str(settings.postgres_port),
                "database.user": settings.postgres_user,
                "database.password": settings.postgres_password,
                "database.dbname": settings.postgres_db,
                "database.server.name": "books",
                "table.include.list": "public.books",
                "plugin.name": "pgoutput",
                "publication.autocreate.mode": "filtered",
                "topic.prefix": "books",
                "slot.name": "debezium_books",
                "key.converter": "org.apache.kafka.connect.json.JsonConverter",
                "value.converter": "org.apache.kafka.connect.json.JsonConverter",
                "key.converter.schemas.enable": "false",
                "value.converter.schemas.enable": "false",
                "transforms": "unwrap",
                "transforms.unwrap.type": (
                    "io.debezium.transforms.ExtractNewRecordState"
                ),
                "transforms.unwrap.drop.tombstones": "false",
                "transforms.unwrap.delete.handling.mode": "rewrite"
            }
        }
        
        return self._create_connector(config)
    
    def create_mongo_connector(self) -> bool:
        
        config = {
            "name": self.mongo_connector,
            "config": {
                "connector.class": "io.debezium.connector.mongodb.MongoDbConnector",
                "mongodb.connection.string": "mongodb://mongo:27017/?replicaSet=rs0",
                "mongodb.name": "reviews",
                "collection.include.list": "books_reviews.reviews",
                "topic.prefix": "reviews",
                "key.converter": "org.apache.kafka.connect.json.JsonConverter",
                "value.converter": "org.apache.kafka.connect.json.JsonConverter",
                "key.converter.schemas.enable": "false",
                "value.converter.schemas.enable": "false",
                "transforms": "unwrap",
                "transforms.unwrap.type": (
                    "io.debezium.connector.mongodb.transforms."
                    "ExtractNewDocumentState"
                ),
                "transforms.unwrap.drop.tombstones": "false",
                "transforms.unwrap.delete.handling.mode": "drop"
            }
        }
        
        return self._create_connector(config)
    
    def _create_connector(self, config: Dict[str, Any]) -> bool:
        
        connector_name = config["name"]
        
        # Check if connector already exists
        try:
            response = requests.get(
                f"{self.base_url}/connectors/{connector_name}",
                timeout=5
            )
            if response.status_code == 200:
                logger.info(f"Connector {connector_name} already exists")
                return True
        except requests.exceptions.RequestException:
            pass
        
        # Create connector
        try:
            response = requests.post(
                f"{self.base_url}/connectors",
                json=config,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Created connector: {connector_name}")
                return True
            else:
                logger.error(f"Failed to create connector {connector_name}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating connector {connector_name}: {e}")
            return False
    
    def get_connector_status(self, connector_name: str) -> Dict[str, Any]:
        
        try:
            response = requests.get(
                f"{self.base_url}/connectors/{connector_name}/status",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting connector status: {e}")
        
        return {}
    
    def delete_connector(self, connector_name: str) -> bool:
        
        try:
            response = requests.delete(
                f"{self.base_url}/connectors/{connector_name}",
                timeout=5
            )
            if response.status_code == 204:
                logger.info(f"Deleted connector: {connector_name}")
                return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting connector: {e}")
        
        return False
    
    def setup_all_connectors(self) -> bool:
        
        if not self.wait_for_debezium():
            return False

        time.sleep(5)
        
        postgres_ok = self.create_postgres_connector()
        mongo_ok = self.create_mongo_connector()
        
        return postgres_ok and mongo_ok

# Global manager instance
debezium_manager = DebeziumManager()
