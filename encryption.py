import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Загружаем переменные из .env до первого обращения к os.getenv
load_dotenv()

ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print("WARNING: ENCRYPTION_KEY not set in .env, using generated key:", ENCRYPTION_KEY)

fernet = Fernet(ENCRYPTION_KEY.encode())

def encrypt_text(text):
    # Если передали список, объединяем его в строку через пробел
    if isinstance(text, list):
        text = " ".join(text)
    return fernet.encrypt(text.encode()).decode()

def decrypt_text(token):
    decrypted = fernet.decrypt(token.encode()).decode()
    # После дешифрования разбиваем строку на отдельные слова
    return decrypted.split()
