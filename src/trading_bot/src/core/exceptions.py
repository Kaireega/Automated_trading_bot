"""
Custom exception hierarchy for the trading bot.

This module defines specific exceptions for different types of errors that can occur
in the trading bot, allowing for more precise error handling and better debugging.
"""


class TradingBotError(Exception):
    """Base exception for all trading bot errors."""
    pass


class DataError(TradingBotError):
    """Base exception for data-related errors."""
    pass


class DataCollectionError(DataError):
    """Raised when data collection fails."""
    pass


class DataValidationError(DataError):
    """Raised when data validation fails."""
    pass


class DataProcessingError(DataError):
    """Raised when data processing fails."""
    pass


class ScrapingError(DataError):
    """Raised when web scraping fails."""
    pass


class APIError(TradingBotError):
    """Base exception for API-related errors."""
    pass


class OANDAAPIError(APIError):
    """Raised when OANDA API calls fail."""
    pass


class NetworkError(APIError):
    """Raised when network operations fail."""
    pass


class AnalysisError(TradingBotError):
    """Base exception for analysis-related errors."""
    pass


class TechnicalAnalysisError(AnalysisError):
    """Raised when technical analysis fails."""
    pass


class RiskManagementError(TradingBotError):
    """Raised when risk management operations fail."""
    pass


class PositionSizingError(RiskManagementError):
    """Raised when position sizing calculations fail."""
    pass


class ConfigurationError(TradingBotError):
    """Raised when configuration operations fail."""
    pass


class ValidationError(TradingBotError):
    """Raised when input validation fails."""
    pass


class MarketDataError(DataError):
    """Raised when market data operations fail."""
    pass


class CacheError(DataError):
    """Raised when cache operations fail."""
    pass


class CalculationError(TradingBotError):
    """Raised when mathematical calculations fail."""
    pass


class InsufficientDataError(DataError):
    """Raised when there's insufficient data for an operation."""
    pass


class TimeoutError(TradingBotError):
    """Raised when operations timeout."""
    pass


class CircuitBreakerError(TradingBotError):
    """Raised when circuit breaker is triggered."""
    pass
