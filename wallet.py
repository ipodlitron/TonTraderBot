import os
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV4R2

def create_new_wallet():
    API_KEY = os.getenv('API_KEY')
    IS_TESTNET = os.getenv('IS_TESTNET') == 'True'
    client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
    wallet, public_key, private_key, mnemonic = WalletV4R2.create(client)
    # mnemonic возвращается как список слов
    return wallet, mnemonic

import asyncio

async def deploy_wallet(mnemonic):
    API_KEY = os.getenv('API_KEY')
    IS_TESTNET = os.getenv('IS_TESTNET') == 'True'
    client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
    # Функция from_mnemonic ожидает список слов, что и получаем после дешифрования
    wallet, public_key, private_key, mnemonic = WalletV4R2.from_mnemonic(client, mnemonic)
    tx_hash = await wallet.deploy()
    return tx_hash, wallet.address.to_str()
