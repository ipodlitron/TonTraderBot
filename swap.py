import os
import aiohttp
from pytoniq_core import Address
from tonutils.client import TonapiClient
from tonutils.jetton.dex.stonfi import StonfiRouterV2
from tonutils.jetton.dex.stonfi.v2.pton.constants import PTONAddresses
from tonutils.utils import to_nano, to_amount
from tonutils.wallet import WalletV4R2

JETTON_DECIMALS = 9
API_KEY = os.getenv("API_KEY")
IS_TESTNET = os.getenv("IS_TESTNET") == "True"

async def get_router_address_ton_to_jetton(target_token_contract: str, amount: float) -> str:
    url = "https://api.ston.fi/v1/swap/simulate"
    headers = {"Accept": "application/json"}
    params = {
        "offer_address": PTONAddresses.TESTNET if IS_TESTNET else PTONAddresses.MAINNET,
        "ask_address": target_token_contract,
        "units": to_nano(amount),
        "slippage_tolerance": 1,
        "dex_v2": "true",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, headers=headers) as response:
            if response.status == 200:
                content = await response.json()
                return content.get("router_address")
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get router address: {response.status}: {error_text}")

async def swap_ton_to_jetton(mnemonic: list, amount: float, target_token_contract: str) -> str:
    client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
    wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic)
    router_address = await get_router_address_ton_to_jetton(target_token_contract, amount)
    stonfi_router = StonfiRouterV2(client, router_address=Address(router_address))
    to, value, body = await stonfi_router.get_swap_ton_to_jetton_tx_params(
        user_wallet_address=wallet.address,
        receiver_address=wallet.address,
        offer_jetton_address=Address(target_token_contract),
        offer_amount=to_nano(amount),
        min_ask_amount=0,
        refund_address=wallet.address,
    )
    tx_hash = await wallet.transfer(
        destination=to,
        amount=to_amount(value),
        body=body,
    )
    return tx_hash

async def get_router_address_jetton_to_ton(source_token_contract: str, amount: float) -> str:
    url = "https://api.ston.fi/v1/swap/simulate"
    headers = {"Accept": "application/json"}
    params = {
        "offer_address": source_token_contract,
        "ask_address": PTONAddresses.TESTNET if IS_TESTNET else PTONAddresses.MAINNET,
        "units": to_nano(amount, JETTON_DECIMALS),
        "slippage_tolerance": 1,
        "dex_v2": "true",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, headers=headers) as response:
            if response.status == 200:
                content = await response.json()
                return content.get("router_address")
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get router address: {response.status}: {error_text}")

async def swap_jetton_to_ton(mnemonic: list, amount: float, source_token_contract: str) -> str:
    client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
    wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic)
    router_address = await get_router_address_jetton_to_ton(source_token_contract, amount)
    stonfi_router = StonfiRouterV2(client, router_address=Address(router_address))
    to, value, body = await stonfi_router.get_swap_jetton_to_ton_tx_params(
        offer_jetton_address=Address(source_token_contract),
        receiver_address=wallet.address,
        user_wallet_address=wallet.address,
        offer_amount=to_nano(amount, JETTON_DECIMALS),
        min_ask_amount=0,
        refund_address=wallet.address,
    )
    tx_hash = await wallet.transfer(
        destination=to,
        amount=to_amount(value),
        body=body,
    )
    return tx_hash

async def get_router_address_jetton_to_jetton(source_token_contract: str, target_token_contract: str, amount: float) -> str:
    url = "https://api.ston.fi/v1/swap/simulate"
    headers = {"Accept": "application/json"}
    params = {
        "offer_address": source_token_contract,
        "ask_address": target_token_contract,
        "units": to_nano(amount, JETTON_DECIMALS),
        "slippage_tolerance": 1,
        "dex_v2": "true",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, headers=headers) as response:
            if response.status == 200:
                content = await response.json()
                return content.get("router_address")
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get router address: {response.status}: {error_text}")

async def swap_jetton_to_jetton(mnemonic: list, amount: float, source_token_contract: str, target_token_contract: str) -> str:
    client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
    wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic)
    router_address = await get_router_address_jetton_to_jetton(source_token_contract, target_token_contract, amount)
    stonfi_router = StonfiRouterV2(client, router_address=Address(router_address))
    to, value, body = await stonfi_router.get_swap_jetton_to_jetton_tx_params(
        user_wallet_address=wallet.address,
        receiver_address=wallet.address,
        refund_address=wallet.address,
        offer_jetton_address=Address(source_token_contract),
        ask_jetton_address=Address(target_token_contract),
        offer_amount=to_nano(amount, JETTON_DECIMALS),
        min_ask_amount=0,
    )
    tx_hash = await wallet.transfer(
        destination=to,
        amount=to_amount(value),
        body=body,
    )
    return tx_hash
