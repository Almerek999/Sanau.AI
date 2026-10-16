from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel

class ConnectorResult(BaseModel):
    connector_name: str
    target: str
    success: bool
    status_code: int = 200
    message: str
    records_synced: int = 0
    raw_response: Dict[str, Any] = {}

class BaseConnector(ABC):
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    @abstractmethod
    def test_connection(self) -> ConnectorResult:
        """Проверка доступности сервиса"""
        pass

    @abstractmethod
    def sync_invoice(self, invoice_data: Dict[str, Any]) -> ConnectorResult:
        """Передача данных накладной во внешний сервис"""
        pass
