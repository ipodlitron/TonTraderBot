import os
import logging
import requests
from dotenv import load_dotenv
from mnemonic import Mnemonic
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.utils import to_nano

load_dotenv()
TONCENTER_API_URL = os.getenv("TONCENTER_API_URL", "https://toncenter.com/api/v2/jsonRPC")
TON_API_KEY = os.getenv("TON_API_KEY")

logger = logging.getLogger(__name__)

def generate_wallet():
    """
    Генерирует новый TON кошелек на основе seed-фразы.
    Возвращает:
      wallet_address (str): адрес, сформированный как EQ + первые 48 символов hex-публичного ключа
      mnemonic (str): seed-фраза
      public_key (str): публичный ключ (hex)
      private_key (str): приватный ключ (hex)
    """
    mnemo = Mnemonic("english")
    mnemonic_phrase = mnemo.generate(strength=256)
    wallet_keys = mnemonic_to_wallet_key(mnemonic_phrase)
    private_key, public_key = wallet_keys
    wallet_address = f"EQ{public_key.hex()[:48]}"
    return wallet_address, mnemonic_phrase, public_key.hex(), private_key.hex()

def send_transaction(sender_private_key, sender_address, to_address, amount_ton, bounce=False, payload=""):
    """
    Отправляет транзакцию через TONCENTER API.
    Параметры:
      sender_private_key (str): приватный ключ (hex)
      sender_address (str): адрес отправителя (например, EQ...)
      to_address (str): адрес получателя
      amount_ton (float): сумма в TON
      bounce (bool): (по умолчанию False)
      payload (str): дополнительные данные
    Возвращает JSON-ответ от TONCENTER API.
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
        logger.error(f"Error sending transaction: {e}")
        raise

def get_wallet_balance(address: str) -> dict:
    """
    Получает баланс кошелька через TONCENTER API.
    Возвращает словарь, где ключ — имя токена, а значение — баланс с округлением до 5 знаков.
    Для TON баланс возвращается даже если он 0.
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
        # Пока поддерживаем только TON
        return {"TON": round(balance_ton, 5)}
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return {"TON": 0.0}
