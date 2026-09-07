from decimal import Decimal
from datetime import UTC, datetime
import json
import logging
import re
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.binance.runner import BinanceCliError, JsonCommandRunner
from app.binance.schemas import (
    BulkTicker24hPayload,
    DepthPayload,
    ExchangeInfoPayload,
    KlinePayload,
    PriceTickerPayload,
    SpotAccountPayload,
    SpotOrderPayload,
    Ticker24hPayload,
)
from app.config import BinanceEnvironment
from app.models.market import MarketData, MarketDataError, MarketDataResult, Volatility
from app.models.portfolio import Portfolio, PortfolioAsset
from app.models.source import DataSource
from app.models.execution import OrderExecutionResult
from app.models.trade import TradeSide
from app.models.symbol import (
    TradingSymbolInfo,
    TradingSymbolInfoError,
    TradingSymbolInfoResult,
)
from app.models.research import MarketCandle, MarketTicker, ResearchTimeframe
from app.services.portfolio_service import calculate_portfolio
from app.services.trade_universe_service import (
    TradeUniverseError,
    require_trade_eligibility,
)


class BinanceDataError(RuntimeError):
    """Raised when Binance data cannot safely produce a domain result."""


_PRICE_TICKERS = TypeAdapter(list[PriceTickerPayload])
_BULK_TICKERS = TypeAdapter(list[BulkTicker24hPayload])
_KLINES = TypeAdapter(list[KlinePayload])
_MARKET_SYMBOL = re.compile(r"^[A-Z0-9]{5,20}$")
_REFERENCE_TRADE_USD = Decimal("1000")
LOGGER = logging.getLogger(__name__)


class InsufficientDepthError(ValueError):
    pass


def classify_volatility(change_percent: Decimal) -> Volatility:
    absolute_change = abs(change_percent)
    if absolute_change >= Decimal("4"):
        return Volatility.HIGH
    if absolute_change >= Decimal("2"):
        return Volatility.MEDIUM
    return Volatility.LOW


def estimate_sell_slippage(
    bids: list[tuple[Decimal, Decimal]],
    reference_price: Decimal,
    reference_usd: Decimal = _REFERENCE_TRADE_USD,
) -> Decimal:
    target_quantity = reference_usd / reference_price
    remaining = target_quantity
    proceeds = Decimal("0")

    for bid_price, bid_quantity in bids:
        if bid_price <= 0 or bid_quantity <= 0:
            continue
        filled = min(remaining, bid_quantity)
        proceeds += filled * bid_price
        remaining -= filled
        if remaining == 0:
            break

    if remaining > 0:
        raise InsufficientDepthError("Insufficient bid depth.")

    average_price = proceeds / target_quantity
    return max(
        (reference_price - average_price) / reference_price * Decimal("100"),
        Decimal("0"),
    )


class BinanceCliGateway:
    """Map fixed Binance Demo CLI capabilities into Sentinel domain models."""

    def __init__(
        self,
        runner: JsonCommandRunner,
        environment: BinanceEnvironment,
    ) -> None:
        self._runner = runner
        if environment is not BinanceEnvironment.DEMO:
            raise ValueError("Sentinel currently supports Binance Demo only.")
        self._data_source = DataSource.BINANCE_DEMO

    async def get_portfolio(self) -> Portfolio:
        try:
            account_payload = SpotAccountPayload.model_validate(
                await self._runner.run(
                    ["spot", "get-account", "--omit-zero-balances", "true"],
                    authenticated=True,
                )
            )
        except ValidationError as error:
            raise BinanceDataError("Binance returned invalid account data.") from error
        except (BinanceCliError, ValueError) as error:
            raise BinanceDataError("Binance account data could not be retrieved.") from error

        try:
            ticker_payloads = _PRICE_TICKERS.validate_python(
                await self._runner.run(["spot", "ticker-price"])
            )
        except (ValidationError, BinanceCliError) as error:
            raise BinanceDataError("Binance returned invalid price data.") from error

        prices = {
            ticker.symbol: ticker.price
            for ticker in ticker_payloads
            if ticker.price > 0
        }
        assets: list[PortfolioAsset] = []
        for balance in account_payload.balances:
            amount = balance.free + balance.locked
            if amount == 0:
                continue

            if balance.asset == "USDT":
                price = Decimal("1")
            else:
                price = prices.get(f"{balance.asset}USDT")
                if price is None:
                    raise BinanceDataError(
                        f"Asset {balance.asset} could not be valued in USDT."
                    )

            assets.append(
                PortfolioAsset(
                    symbol=balance.asset,
                    amount=amount,
                    usd_value=amount * price,
                )
            )

        try:
            return calculate_portfolio(assets, data_source=self._data_source)
        except ValueError as error:
            raise BinanceDataError(
                "Binance portfolio contains no valued assets."
            ) from error

    async def get_market_data(self, symbol: str) -> MarketDataResult:
        normalized_symbol = symbol.strip().upper()
        error_symbol = normalized_symbol or "UNKNOWN"
        if _MARKET_SYMBOL.fullmatch(normalized_symbol) is None:
            return MarketDataError(
                symbol=error_symbol,
                error=f"Invalid market symbol: {error_symbol}",
            )

        try:
            ticker_raw = await self._run_public_market_read(
                ["spot", "ticker24hr", "--symbol", normalized_symbol],
                normalized_symbol,
            )
            depth_raw = await self._run_public_market_read(
                [
                    "spot",
                    "depth",
                    "--symbol",
                    normalized_symbol,
                    "--limit",
                    "100",
                ],
                normalized_symbol,
            )
        except BinanceCliError:
            return MarketDataError(
                symbol=normalized_symbol,
                error="Binance market data could not be retrieved.",
            )

        try:
            ticker = Ticker24hPayload.model_validate(ticker_raw)
            depth = DepthPayload.model_validate(depth_raw)
            if ticker.symbol != normalized_symbol:
                raise ValueError("Ticker symbol did not match the request.")
            slippage = estimate_sell_slippage(depth.bids, ticker.last_price)
        except InsufficientDepthError:
            return MarketDataError(
                symbol=normalized_symbol,
                error="Binance order book depth is insufficient.",
            )
        except (ValidationError, ValueError):
            return MarketDataError(
                symbol=normalized_symbol,
                error="Binance returned invalid market data.",
            )

        return MarketData(
            symbol=ticker.symbol,
            price=ticker.last_price,
            change_24h_percent=ticker.price_change_percent,
            volatility=classify_volatility(ticker.price_change_percent),
            estimated_slippage_percent=slippage,
            data_source=self._data_source,
        )

    async def get_symbol_info(self, symbol: str) -> TradingSymbolInfoResult:
        normalized_symbol = symbol.strip().upper()
        error_symbol = normalized_symbol or "UNKNOWN"
        if _MARKET_SYMBOL.fullmatch(normalized_symbol) is None:
            return TradingSymbolInfoError(
                symbol=error_symbol,
                error=f"Invalid market symbol: {error_symbol}",
            )

        try:
            raw = await self._runner.run(
                [
                    "spot",
                    "exchange-info",
                    "--symbol",
                    normalized_symbol,
                    "--show-permission-sets",
                    "false",
                ]
            )
            payload = ExchangeInfoPayload.model_validate(raw)
            if len(payload.symbols) != 1:
                raise ValueError("Binance did not return exactly one symbol.")
            info = payload.symbols[0]
            if info.symbol.strip().upper() != normalized_symbol:
                raise ValueError("Binance symbol did not match the request.")
        except (BinanceCliError, ValidationError, ValueError):
            return TradingSymbolInfoError(
                symbol=normalized_symbol,
                error="Binance symbol information could not be verified.",
            )

        return TradingSymbolInfo(
            symbol=info.symbol,
            status=info.status,
            base_asset=info.base_asset,
            quote_asset=info.quote_asset,
            order_types=info.order_types,
            is_spot_trading_allowed=info.is_spot_trading_allowed,
            quote_order_qty_market_allowed=info.quote_order_qty_market_allowed,
        )

    async def get_market_universe(self) -> tuple[MarketTicker, ...]:
        try:
            exchange_raw = await self._run_public_market_read(
                [
                    "spot",
                    "exchange-info",
                    "--symbol-status",
                    "TRADING",
                    "--show-permission-sets",
                    "false",
                ],
                "MARKET_UNIVERSE",
            )
            exchange = ExchangeInfoPayload.model_validate(exchange_raw)
            symbols = sorted(
                info.symbol
                for info in exchange.symbols
                if _is_eligible_spot_usdt_symbol(info)
            )
            if not symbols:
                raise ValueError("Binance returned no eligible Spot USDT symbols.")

            tickers: list[MarketTicker] = []
            for start in range(0, len(symbols), 100):
                batch = symbols[start:start + 100]
                ticker_raw = await self._run_public_market_read(
                    [
                        "spot",
                        "ticker24hr",
                        "--symbols",
                        json.dumps(batch, separators=(",", ":")),
                        "--type",
                        "FULL",
                    ],
                    "MARKET_UNIVERSE",
                )
                payloads = _BULK_TICKERS.validate_python(ticker_raw)
                if {payload.symbol for payload in payloads} != set(batch):
                    raise ValueError("Binance ticker batch did not match the request.")
                tickers.extend(
                    MarketTicker(
                        symbol=payload.symbol,
                        price=payload.last_price,
                        change_24h_percent=payload.price_change_percent,
                        quote_volume=payload.quote_volume,
                        observed_at=datetime.fromtimestamp(
                            payload.close_time / 1000,
                            tz=UTC,
                        ),
                    )
                    for payload in payloads
                )
            return tuple(tickers)
        except (BinanceCliError, ValidationError, ValueError) as error:
            raise BinanceDataError(
                "Binance market universe could not be verified."
            ) from error

    async def get_market_candles(
        self,
        symbol: str,
        timeframe: ResearchTimeframe,
        limit: int,
    ) -> tuple[MarketCandle, ...]:
        normalized = symbol.strip().upper()
        if _MARKET_SYMBOL.fullmatch(normalized) is None:
            raise BinanceDataError("Market candle symbol format is invalid.")
        if not isinstance(timeframe, ResearchTimeframe):
            raise BinanceDataError("Market candle timeframe is invalid.")
        if limit < 1 or limit > 1000:
            raise BinanceDataError("Market candle limit must be between 1 and 1,000.")

        try:
            raw = await self._run_public_market_read(
                [
                    "spot",
                    "klines",
                    "--symbol",
                    normalized,
                    "--interval",
                    timeframe.value,
                    "--limit",
                    str(limit),
                ],
                normalized,
            )
            payloads = _KLINES.validate_python(raw)
            if not payloads:
                raise ValueError("Binance returned no market candles.")
            return tuple(_market_candle(payload) for payload in payloads)
        except (BinanceCliError, ValidationError, ValueError) as error:
            raise BinanceDataError(
                f"Binance market candles could not be verified for {normalized}."
            ) from error

    async def _run_public_market_read(
        self,
        arguments: list[str],
        symbol: str,
    ) -> Any:
        for attempt in range(2):
            try:
                return await self._runner.run(arguments)
            except BinanceCliError:
                if attempt == 1:
                    LOGGER.warning(
                        "Binance Demo %s failed after one retry for %s.",
                        arguments[1],
                        symbol,
                    )
                    raise
        raise AssertionError("Unreachable market retry state.")

    async def submit_market_order(
        self,
        *,
        symbol: str,
        side: TradeSide,
        quote_usd: Decimal,
        client_order_id: str,
    ) -> OrderExecutionResult:
        normalized = await self._require_executable_symbol(symbol)
        arguments = [
            "spot",
            "new-order",
            "--symbol",
            normalized,
            "--side",
            side.value,
            "--type",
            "MARKET",
            "--quote-order-qty",
            format(quote_usd, "f"),
            "--new-client-order-id",
            client_order_id,
            "--new-order-resp-type",
            "RESULT",
        ]
        try:
            raw = await self._runner.run(arguments, authenticated=True)
            payload = SpotOrderPayload.model_validate(raw)
            _require_order_identity(payload, normalized, client_order_id)
        except ValidationError as error:
            raise BinanceDataError("Binance returned invalid order data.") from error
        except (BinanceCliError, ValueError) as error:
            raise BinanceDataError("Binance Demo order could not be submitted.") from error
        return _execution_result(payload)

    async def get_order(
        self,
        symbol: str,
        client_order_id: str,
    ) -> OrderExecutionResult:
        normalized = symbol.strip().upper()
        if _MARKET_SYMBOL.fullmatch(normalized) is None:
            raise BinanceDataError("Trading symbol format is invalid.")
        try:
            raw = await self._runner.run(
                [
                    "spot",
                    "get-order",
                    "--symbol",
                    normalized,
                    "--orig-client-order-id",
                    client_order_id,
                ],
                authenticated=True,
            )
            payload = SpotOrderPayload.model_validate(raw)
            _require_order_identity(payload, normalized, client_order_id)
        except ValidationError as error:
            raise BinanceDataError("Binance returned invalid order data.") from error
        except (BinanceCliError, ValueError) as error:
            raise BinanceDataError("Binance Demo order could not be verified.") from error
        return _execution_result(payload)

    async def _require_executable_symbol(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if _MARKET_SYMBOL.fullmatch(normalized) is None:
            raise BinanceDataError("Trading symbol format is invalid.")

        result = await self.get_symbol_info(normalized)
        if isinstance(result, TradingSymbolInfoError):
            raise BinanceDataError("Trading eligibility could not be verified.")
        try:
            require_trade_eligibility(result)
        except TradeUniverseError as error:
            raise BinanceDataError(str(error)) from error
        return normalized


def _execution_result(payload: SpotOrderPayload) -> OrderExecutionResult:
    return OrderExecutionResult(
        order_id=payload.order_id,
        client_order_id=payload.client_order_id,
        symbol=payload.symbol,
        status=payload.status,
    )


def _is_eligible_spot_usdt_symbol(info: Any) -> bool:
    try:
        require_trade_eligibility(
            TradingSymbolInfo(
                symbol=info.symbol,
                status=info.status,
                base_asset=info.base_asset,
                quote_asset=info.quote_asset,
                order_types=info.order_types,
                is_spot_trading_allowed=info.is_spot_trading_allowed,
                quote_order_qty_market_allowed=info.quote_order_qty_market_allowed,
            )
        )
    except (TradeUniverseError, ValidationError):
        return False
    return True


def _market_candle(payload: KlinePayload) -> MarketCandle:
    (
        open_time,
        open_price,
        high,
        low,
        close,
        volume,
        close_time,
        quote_volume,
        _trade_count,
        _taker_buy_volume,
        _taker_buy_quote_volume,
        _unused,
    ) = payload.root
    return MarketCandle(
        open_time=datetime.fromtimestamp(open_time / 1000, tz=UTC),
        close_time=datetime.fromtimestamp(close_time / 1000, tz=UTC),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        quote_volume=quote_volume,
    )


def _require_order_identity(
    payload: SpotOrderPayload,
    symbol: str,
    client_order_id: str,
) -> None:
    if payload.symbol != symbol or payload.client_order_id != client_order_id:
        raise BinanceDataError("Binance order identity did not match the request.")
