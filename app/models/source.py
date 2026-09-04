from enum import Enum


class DataSource(str, Enum):
    UNKNOWN = "UNKNOWN"
    BINANCE_DEMO = "BINANCE_DEMO"
    BINANCE_PROD = "BINANCE_PROD"
