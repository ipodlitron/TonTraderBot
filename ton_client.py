import os
import logging
import requests
from dotenv import load_dotenv
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.utils import to_nano

# Загружаем переменные окружения из .env
load_dotenv()

TONCENTER_API_URL = os.getenv("TONCENTER_API_URL", "https://toncenter.com/api/v2/jsonRPC")
TON_API_KEY = os.getenv("TON_API_KEY")

logger = logging.getLogger(__name__)

def generate_wallet():
    """
    Генерирует новый кошелек TON с использованием версии v4r2 и workchain=0.
    
    Возвращает:
      wallet_address (str): Адрес кошелька (например, EQ...),
      mnemonic (str): Seed-фраза (кодовые слова) в виде строки, разделенной пробелами,
      public_key (str): Публичный ключ (в hex формате),
      private_key (str): Приватный ключ (в hex формате).
    """
    # Генерация кошелька через tonsdk (версия v4r2, workchain=0)
    mnemonics, pub_k, priv_k, wallet = Wallets.create(WalletVersionEnum.v4r2, workchain=0)
    # Получаем адрес кошелька в строковом формате, с флагами (base64=False, url_safe=True, bounce=False)
    wallet_address = wallet.address.to_string(True, True, False)
    # Объединяем список мнемоник в одну строку с пробелами
    mnemonic_str = " ".join(mnemonics)
    return wallet_address, mnemonic_str, pub_k, priv_k

def send_transaction(sender_private_key, sender_address, to_address, amount_ton, bounce=False, payload=""):
    """
    Отправляет транзакцию с указанного кошелька через TONCENTER API.
    
    Параметры:
      sender_private_key (str): Приватный ключ отправителя (hex-строка),
      sender_address (str): Адрес отправителя (например, EQ...),
      to_address (str): Адрес получателя,
      amount_ton (float): Сумма перевода в TON,
      bounce (bool): Флаг bounce (по умолчанию False),
      payload (str): Дополнительные данные (по умолчанию пустая строка).
    
    Возвращает:
      JSON-ответ от TONCENTER API.
    """
    headers = {
        "Authorization": f"Bearer {TON_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "from": sender_address,
        "to": to_address,
        "value": to_nano(amount_ton, "ton"),
        "private_key": sender_private_key,
        "bounce": bounce,
        "payload": payload
    }
    try:
        response = requests.post(TONCENTER_API_URL + "/sendTransaction", headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка при отправке транзакции: {e}")
        raise

def get_wallet_balance(address: str) -> dict:
    """
    Получает баланс кошелька через TONCENTER API.
    
    Возвращает словарь, где ключ — название токена, а значение — баланс, округленный до 5 знаков после запятой.
    Баланс токена TON возвращается даже если он равен 0.
    """
    headers = {
        "Authorization": f"Bearer {TON_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "raw.getAccountState",
        "params": {"address": address}
    }
    try:
        response = requests.post(TONCENTER_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        if "result" in result and result["result"]:
            balance_nano = int(result["result"].get("balance", 0))
        else:
            balance_nano = 0
        balance_ton = balance_nano / 1e9
        return {"TON": round(balance_ton, 5)}
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        return {"TON": 0.0}
