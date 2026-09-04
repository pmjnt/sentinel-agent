from decimal import Decimal

from pydantic import TypeAdapter, ValidationError

from app.binance.runner import BinanceCliError, JsonCommandRunner
from app.binance.schemas import PriceTickerPayload, SpotAccountPayload
from app.config import BinanceEnvironment
from app.models.portfolio import Portfolio, PortfolioAsset
from app.models.source import DataSource
from app.services.portfolio_service import calculate_portfolio


class BinanceDataError(RuntimeError):
    """Raised when Binance data cannot safely produce a domain result."""


_PRICE_TICKERS = TypeAdapter(list[PriceTickerPayload])


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
