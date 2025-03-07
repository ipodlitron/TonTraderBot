import os
import re
import logging
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV4R2
from tonutils.jetton import JettonMaster, JettonWallet  # Рабочий импорт для jetton
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем функции для работы с базой данных
from database import get_wallet_by_user, get_user_tokens
from cmc import get_token_price

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def to_amount(value, decimals=9):
    return value / (10 ** decimals)

async def get_all_user_tokens(user_id: int) -> dict:
    """
    Возвращает словарь, где ключ — символ токена, а значение — список:
      [баланс (округленный до 4 знаков), название, адрес контракта, цена в USDT].
    """
    list_tokens = {}
    try:
        # Получаем данные кошелька из базы данных
        wallet_data = get_wallet_by_user(user_id)
        if not wallet_data:
            logger.error("Нет данных кошелька для user_id: %s", user_id)
            return {}
        # Дешифруем мнемонику; функция decrypt_text возвращает список слов
        from encryption import decrypt_text
        mnemonic = decrypt_text(wallet_data[1])
        
        API_KEY = os.getenv("TON_CONSOLE_API_KEY")
        IS_TESTNET = os.getenv("IS_TESTNET") == "True"
        client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
        
        # Восстанавливаем кошелек из мнемоники (функция from_mnemonic ожидает список слов)
        wallet, public_key, private_key, mnemonic = WalletV4R2.from_mnemonic(client, mnemonic)
        
        # Получаем баланс TON
        try:
            ton_balance = await wallet.balance()
            balance_value = round(to_amount(ton_balance), 4)
            price = await get_token_price("TON")
            list_tokens["TON"] = [balance_value, "Toncoin", None, price]
        except Exception as e:
            logger.error(f"Ошибка получения баланса TON: {e}")
            list_tokens["TON"] = [0, "Toncoin", None, "N/A"]
        
        # Чтение дефолтного файла токенов
        TOKEN_FILE = os.getenv("TOKEN_FILE", "tokens.txt")
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as file:
                for line in file:
                    pattern = r'([^|]+) \(\$([^\)]+)\) \| ([^\s]+)'
                    match = re.match(pattern, line.strip())
                    if match:
                        name = match.group(1).strip()
                        symbol = match.group(2).strip()
                        jetton_master_address = match.group(3).strip()
                        try:
                            jetton_wallet_address = await JettonMaster.get_wallet_address(
                                client=client,
                                owner_address=wallet.address.to_str(),
                                jetton_master_address=jetton_master_address,
                            )
                            jetton_wallet_data = await JettonWallet.get_wallet_data(
                                client=client,
                                jetton_wallet_address=jetton_wallet_address,
                            )
                            token_balance = round(to_amount(jetton_wallet_data.balance, 9), 4)
                        except Exception as inner_e:
                            logger.error(f"Ошибка получения данных для токена {symbol}: {inner_e}")
                            token_balance = 0
                        token_price = await get_token_price(symbol)
                        list_tokens[symbol] = [token_balance, name, jetton_master_address, token_price]
        except Exception as e:
            logger.error(f"Ошибка чтения файла токенов {TOKEN_FILE}: {e}")
        
        # Обработка личных токенов пользователя (если есть)
        user_tokens = get_user_tokens(user_id)
        for token in user_tokens:
            token_symbol, token_name, token_address = token
            try:
                jetton_wallet_address = await JettonMaster.get_wallet_address(
                    client=client,
                    owner_address=wallet.address.to_str(),
                    jetton_master_address=token_address,
                )
                jetton_wallet_data = await JettonWallet.get_wallet_data(
                    client=client,
                    jetton_wallet_address=jetton_wallet_address,
                )
                token_balance = round(to_amount(jetton_wallet_data.balance, 9), 4)
            except Exception as inner_e:
                logger.error(f"Ошибка получения данных для личного токена {token_name}: {inner_e}")
                token_balance = 0
            token_price = await get_token_price(token_symbol)
            list_tokens[token_symbol] = [token_balance, token_name, token_address, token_price]
    except Exception as e:
        logger.error(f"Ошибка при восстановлении кошелька: {e}")
        return {}
    return list_tokens
