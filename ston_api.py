import aiohttp
import logging
from config import (
    ASSETS_ENDPOINT,
    SWAP_SIMULATE_ENDPOINT,
    JETTON_ADDRESS_ENDPOINT,
    TON_WALLET_ADDRESS
)

logger = logging.getLogger(__name__)
TIMEOUT = aiohttp.ClientTimeout(total=10)

async def fetch_json(url: str, **kwargs) -> dict:
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        try:
            async with session.get(url, **kwargs) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            logger.error(f"API error: {e}")
            raise

async def get_wallet_balances(wallet_address: str) -> dict:
    url = ASSETS_ENDPOINT.format(wallet_address=wallet_address)
    data = await fetch_json(url)
    return {asset["symbol"]: asset["balance"] for asset in data.get("asset_list", [])}

async def get_swap_quote(from_token: str, to_token: str, amount: int, user_address: str) -> dict:
    params = {
        "offer_address": TON_WALLET_ADDRESS if from_token == "TON" else await _get_jetton_address(from_token, user_address),
        "ask_address": TON_WALLET_ADDRESS if to_token == "TON" else await _get_jetton_address(to_token, user_address),
        "units": str(amount),
        "slippage_tolerance": "0.01"
    }
    return await fetch_json(SWAP_SIMULATE_ENDPOINT, params=params)

async def _get_jetton_address(token: str, owner: str) -> str:
    search_url = ASSETS_SEARCH_ENDPOINT + f"?search_string={token.upper()}"
    data = await fetch_json(search_url)
    contract = data["asset_list"][0]["contract_address"]
    jetton_url = JETTON_ADDRESS_ENDPOINT.format(contract_address=contract)
    return (await fetch_json(jetton_url, params={"owner_address": owner}))["address"]
