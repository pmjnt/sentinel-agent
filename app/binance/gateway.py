from decimal import Decimal
import re

from pydantic import TypeAdapter, ValidationError

from app.binance.runner import BinanceCliError, JsonCommandRunner
from app.binance.schemas import (
    DepthPayload,
    PriceTickerPayload,
    SpotAccountPayload,
    Ticker24hPayload,
)
from app.config import BinanceEnvironment
from app.models.market import MarketData, MarketDataError, MarketDataResult, Volatility
from app.models.portfolio import Portfolio, PortfolioAsset
from app.models.source import DataSource
from app.services.portfolio_service import calculate_portfolio


class BinanceDataError(RuntimeError):
    """Raised when Binance data cannot safely produce a domain result."""


_PRICE_TICKERS = TypeAdapter(list[PriceTickerPayload])
_MARKET_SYMBOL = re.compile(r"^[A-Z0-9]{5,20}$")
_REFERENCE_TRADE_USD = Decimal("1000")


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
    """Map fixed read-only Binance CLI responses into Sentinel domain models."""

    def __init__(
        self,
        runner: JsonCommandRunner,
        environment: BinanceEnvironment,
    ) -> None:
        self._runner = runner
        self._data_source = {
            BinanceEnvironment.DEMO: DataSource.BINANCE_DEMO,
            BinanceEnvironment.PROD: DataSource.BINANCE_PROD,
        }[environment]

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

        prices = {ticker.symbol: ticker.price for ticker in ticker_payloads}
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
            ticker_raw = await self._runner.run(
                ["spot", "ticker24hr", "--symbol", normalized_symbol]
            )
            depth_raw = await self._runner.run(
                [
                    "spot",
                    "depth",
                    "--symbol",
                    normalized_symbol,
                    "--limit",
                    "100",
                ]
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
