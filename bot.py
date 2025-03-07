import os
import logging
import re
import asyncio
import aiohttp
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database import init_db, get_wallet_by_user, add_wallet, add_user_token, get_user_tokens
from encryption import encrypt_text, decrypt_text
from wallet import create_new_wallet, deploy_wallet
from balance import get_all_user_tokens
from cmc import get_token_info_by_address
from swap import swap_ton_to_jetton, swap_jetton_to_ton, swap_jetton_to_jetton

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
GREETING = os.getenv('GREETING', 'Привет!')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для /add
ADD_TOKEN_WAIT_CONTRACT, ADD_TOKEN_CONFIRM, ADD_TOKEN_MANUAL_WAIT_SYMBOL, ADD_TOKEN_MANUAL_WAIT_NAME = range(4)
# Состояния для /send
SEND_SELECT_TOKEN, SEND_ENTER_ADDRESS, SEND_ENTER_AMOUNT, SEND_CONFIRM = range(4)
# Состояния для /swap
SWAP_SELECT_FROM, SWAP_SELECT_TO, SWAP_ENTER_AMOUNT, SWAP_CONFIRM = range(4)

def get_main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("/wallet", callback_data="menu_wallet"),
         InlineKeyboardButton("/export", callback_data="menu_export")],
        [InlineKeyboardButton("/swap", callback_data="menu_swap"),
         InlineKeyboardButton("/send", callback_data="menu_send")],
        [InlineKeyboardButton("/balance", callback_data="menu_balance"),
         InlineKeyboardButton("/help", callback_data="menu_help"),
         InlineKeyboardButton("/add", callback_data="menu_add")]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Команды: start, create wallet, export, wallet info, balance, help ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet_data = get_wallet_by_user(user_id)
    if wallet_data:
        await update.message.reply_text("У вас уже есть кошелек, можете приступить к работе с ботом!", reply_markup=get_main_menu_keyboard())
    else:
        text = f"{GREETING}\nДля работы с ботом необходимо создать новый кошелек Тон. Создать?"
        keyboard = [[InlineKeyboardButton("Да", callback_data="create_wallet_yes"),
                     InlineKeyboardButton("Нет", callback_data="create_wallet_no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)
    
async def create_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "create_wallet_no":
        await query.edit_message_text("Кошелек не создан. Для доступа к функционалу создайте кошелек, нажав /start.")
        return
    elif query.data == "create_wallet_yes":
        await query.edit_message_text("Создание кошелька... Пожалуйста, подождите.")
        try:
            wallet, mnemonic = create_new_wallet()
            wallet_address = wallet.address.to_str()
            logger.info("Создан новый кошелек: %s", wallet_address)
        except Exception as e:
            logger.error("Ошибка при создании кошелька: %s", e)
            await query.message.reply_text("Ошибка при создании кошелька. Попробуйте позже.")
            return
        # Шифруем мнемонику (mnemonic – список слов)
        encrypted_mnemonic = encrypt_text(mnemonic)
        add_wallet(query.from_user.id, wallet_address, encrypted_mnemonic)

        text = ("Ваш кошелек создан и готов к работе, экспортируйте мнемоническую фразу и храните её в надежном месте!\nЭкспортировать?")
        keyboard = [[InlineKeyboardButton("Да", callback_data="export_mnemonic_yes"),
                     InlineKeyboardButton("Нет", callback_data="export_mnemonic_no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(text, reply_markup=reply_markup)
        await query.message.reply_text("Вы можете продолжить работу с ботом.") #, reply_markup=get_main_menu_keyboard())

async def export_mnemonic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "export_mnemonic_no":
        await query.edit_message_text("Экспорт отменен.")
        return
    elif query.data == "export_mnemonic_yes":
        wallet_data = get_wallet_by_user(query.from_user.id)
        if not wallet_data:
            await query.edit_message_text("Сначала создайте кошелек командой /start.")
            return
        encrypted_mnemonic = wallet_data[1]
        try:
            mnemonic_list = decrypt_text(encrypted_mnemonic)
        except Exception as e:
            logger.error("Ошибка дешифрования мнемоники: %s", e)
            await query.edit_message_text("Ошибка при экспорте мнемоники.")
            return
        warning_text = "Внимание! Мнемоническая фраза – это ключ к вашему кошельку. Не передавайте её никому!"
        await query.edit_message_text(f"{warning_text}\n\nМнемоника:\n{' '.join(mnemonic_list)}")

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet_data = get_wallet_by_user(user_id)
    if not wallet_data:
        await update.message.reply_text("Сначала создайте кошелек командой /start.")
        return
    text = ("Экспортировать мнемоническую фразу?\nВнимание! Храните мнемонику в надежном месте!")
    keyboard = [[InlineKeyboardButton("Да", callback_data="export_mnemonic_yes"),
                InlineKeyboardButton("Нет", callback_data="export_mnemonic_no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)
    
async def wallet_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet_data = get_wallet_by_user(user_id)
    if not wallet_data:
        await update.message.reply_text("Сначала создайте кошелек командой /start.")
        return
    wallet_address = wallet_data[0]
    await update.message.reply_text(f"Адрес вашего кошелька: {wallet_address}") #, reply_markup=get_main_menu_keyboard())

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet_data = get_wallet_by_user(user_id)
    if not wallet_data:
        await update.message.reply_text("Сначала создайте кошелек командой /start.")
        return
    await update.message.reply_text("Получение балансов, пожалуйста, подождите...")
    tokens = await get_all_user_tokens(user_id)
    if not tokens:
        await update.message.reply_text("Ошибка получения балансов.")
        return
    response_lines = ["Токен | Количество | Стоимость актива (USDT)"]
    for symbol, token in tokens.items():
        # token: [balance, name, contract, price]
        try:
            amount = float(token[0])
        except Exception:
            amount = 0.0
        price = token[3]
        if isinstance(price, (int, float)):
            value = amount * price
            response_lines.append(f"{symbol} | {amount:.4f} | {value:.2f}")
        else:
            response_lines.append(f"{symbol} | {amount:.4f} | N/A")
    response_text = "\n".join(response_lines)
    await update.message.reply_text(response_text)
        
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/start - Запуск бота и создание кошелька\n"
        "/wallet - Информация о кошельке\n"
        "/export - Экспорт мнемонической фразы\n"
        "/swap - Обмен токенов\n"
        "/send - Отправка токенов\n"
        "/balance - Баланс токенов\n"
        "/add - Добавление пользовательского токена\n"
        "/help - Справка по командам"
    )
    await update.message.reply_text(help_text) #, reply_markup=get_main_menu_keyboard())

# --- Команда /add (ConversationHandler) ---
async def add_token_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet_data = get_wallet_by_user(user_id)
    if not wallet_data:
        await update.message.reply_text("Сначала создайте кошелек командой /start.")
        return ConversationHandler.END
    await update.message.reply_text("Введите контракт токена, который хотите добавить:")
    return ADD_TOKEN_WAIT_CONTRACT

async def add_token_receive_contract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contract = update.message.text.strip()
    context.user_data["new_token_contract"] = contract
    token_data = await get_token_info_by_address(contract)
    if token_data.get("status", {}).get("error_code") == 0:
        token_info = list(token_data.get("data", {}).values())[0]
        token_name = token_info.get("name", "")
        token_symbol = token_info.get("symbol", "")
        context.user_data["api_token_name"] = token_name
        context.user_data["api_token_symbol"] = token_symbol
        keyboard = [[InlineKeyboardButton("Да", callback_data="add_token_confirm_yes"),
                     InlineKeyboardButton("Нет", callback_data="add_token_confirm_no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Найден токен: {token_name} (${token_symbol}). Верно?", reply_markup=reply_markup)
        return ADD_TOKEN_CONFIRM
    else:
        keyboard = [[InlineKeyboardButton("Да", callback_data="add_token_manual_yes"),
                     InlineKeyboardButton("Нет", callback_data="add_token_manual_no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Не удалось найти информацию по токену. Хотите ввести данные вручную?", reply_markup=reply_markup)
        return ADD_TOKEN_CONFIRM

async def add_token_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "add_token_confirm_yes":
        token_symbol = context.user_data.get("api_token_symbol")
        token_name = context.user_data.get("api_token_name")
        contract = context.user_data.get("new_token_contract")
        add_user_token(query.from_user.id, token_symbol, token_name, contract)
        await query.edit_message_text(f"Токен {token_name} (${token_symbol}) добавлен в ваш список.")
        return ConversationHandler.END
    elif query.data == "add_token_confirm_no":
        keyboard = [[InlineKeyboardButton("Да", callback_data="add_token_manual_yes"),
                     InlineKeyboardButton("Нет", callback_data="add_token_manual_no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Хотите ввести данные вручную?", reply_markup=reply_markup)
        return ADD_TOKEN_CONFIRM

async def add_token_manual_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "add_token_manual_yes":
        await query.edit_message_text("Введите тикер токена (например, NOT):")
        return ADD_TOKEN_MANUAL_WAIT_SYMBOL
    elif query.data == "add_token_manual_no":
        await query.edit_message_text("Добавление токена отменено.")
        return ConversationHandler.END

async def add_token_manual_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token_symbol = update.message.text.strip()
    context.user_data["manual_token_symbol"] = token_symbol
    await update.message.reply_text("Введите название токена:")
    return ADD_TOKEN_MANUAL_WAIT_NAME

async def add_token_manual_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token_name = update.message.text.strip()
    token_symbol = context.user_data.get("manual_token_symbol")
    contract = context.user_data.get("new_token_contract")
    add_user_token(update.effective_user.id, token_symbol, token_name, contract)
    await update.message.reply_text(f"Токен {token_name} (${token_symbol}) добавлен в ваш список.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def add_token_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добавление токена отменено.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tokens = await get_all_user_tokens(user_id)
    if tokens is None:
        await update.message.reply_text("Ошибка получения данных кошелька.")
        return ConversationHandler.END
    # Каждый элемент token представляет собой список: [balance, name, contract, price]
    available_tokens = {sym: token for sym, token in tokens.items() if token[0] > 0}
    if not available_tokens:
        await update.message.reply_text("Баланс всех токенов вашего кошелька = 0, вначале пополните кошелек")
        return ConversationHandler.END
    context.user_data["available_tokens"] = available_tokens
    keyboard = []
    for sym, token in available_tokens.items():
        button_text = f"{sym} ({token[1]})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"send_token_{sym}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите токен для отправки:", reply_markup=reply_markup)
    logger.info("User %s инициировал перевод. Доступные токены: %s", user_id, list(available_tokens.keys()))
    return SEND_SELECT_TOKEN
    
async def send_token_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    token_symbol = query.data.split("_")[-1]
    available_tokens = context.user_data.get("available_tokens")
    if not available_tokens or token_symbol not in available_tokens:
        await query.edit_message_text("Ошибка: выбран неверный токен.")
        return ConversationHandler.END
    context.user_data["selected_token"] = available_tokens[token_symbol]
    context.user_data["selected_token_symbol"] = token_symbol
    logger.info("User %s выбрал токен %s для отправки", query.from_user.id, token_symbol)
    # Используем индекс [1] для названия токена
    await query.edit_message_text(f"Вы выбрали {token_symbol} ({available_tokens[token_symbol][1]}).\nВведите адрес получателя:")
    return SEND_ENTER_ADDRESS
    
async def send_enter_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipient_address = update.message.text.strip()
    context.user_data["recipient_address"] = recipient_address
    logger.info("User %s ввёл адрес получателя: %s", update.effective_user.id, recipient_address)
    await update.message.reply_text("Введите количество для отправки:")
    return SEND_ENTER_AMOUNT

async def send_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Неверное значение. Введите число:")
        return SEND_ENTER_AMOUNT
    selected_token = context.user_data.get("selected_token")
    # Элемент 0 – баланс
    if amount > selected_token[0]:
        await update.message.reply_text("Ошибка: указанное количество превышает баланс. Введите корректное значение:")
        return SEND_ENTER_AMOUNT
    context.user_data["send_amount"] = amount
    token_symbol = context.user_data.get("selected_token_symbol")
    # Элемент 1 – название токена
    token_name = selected_token[1]
    # Элемент 2 – адрес контракта
    token_contract = selected_token[2] if selected_token[2] else "TON"
    recipient_address = context.user_data.get("recipient_address")
    confirmation_text = (f"Подтвердите отправку:\n"
                         f"Токен: {token_symbol} ({token_name})\n"
                         f"Контракт: {token_contract}\n"
                         f"Количество: {amount}\n"
                         f"Получатель: {recipient_address}")
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="send_confirm_yes"),
         InlineKeyboardButton("Нет", callback_data="send_confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
    logger.info("User %s запросил отправку %s %s на адрес %s", update.effective_user.id, amount, token_symbol, recipient_address)
    return SEND_CONFIRM
    
async def send_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "send_confirm_no":
        await query.edit_message_text("Отправка отменена.")
        logger.info("User %s отменил отправку токена.", user_id)
        return ConversationHandler.END
    recipient_address = context.user_data.get("recipient_address")
    amount = context.user_data.get("send_amount")
    selected_token = context.user_data.get("selected_token")
    token_symbol = context.user_data.get("selected_token_symbol")
    wallet_data = get_wallet_by_user(user_id)
    if not wallet_data:
        await query.edit_message_text("Сначала создайте кошелек командой /start.")
        return ConversationHandler.END
    from encryption import decrypt_text
    # Получаем список слов (мнемонику)
    mnemonic = decrypt_text(wallet_data[1])
    from tonutils.client import TonapiClient
    from tonutils.wallet import WalletV4R2
    API_KEY = os.getenv("TON_CONSOLE_API_KEY")
    IS_TESTNET = os.getenv("IS_TESTNET") == "True"
    client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
    try:
        wallet, public_key, private_key, _ = WalletV4R2.from_mnemonic(client, mnemonic)
        base_amount = amount
        #base_amount = int(amount * (10 ** 9))
        if token_symbol == "TON":
            tx_hash = await wallet.transfer(
                destination=recipient_address,
                amount=base_amount,
                body="TonTrade",
            )
        else:
            # Элемент 2 – адрес контракта токена
            tx_hash = await wallet.transfer_jetton(
                destination=recipient_address,
                jetton_master_address=selected_token[2],
                jetton_amount=base_amount,
                jetton_decimals=9,
                forward_payload="TonTrade",
            )
        await query.edit_message_text(f"Успешно переведено {amount} {token_symbol}!\nTransaction hash: {tx_hash}")
        logger.info("User %s успешно перевёл %s %s на %s. Tx hash: %s", user_id, amount, token_symbol, recipient_address, tx_hash)
    except Exception as e:
        logger.error("Ошибка при отправке токена для пользователя %s: %s", user_id, e)
        await query.edit_message_text("Ошибка при отправке токенов. Попробуйте позже.")
    return ConversationHandler.END
        
async def send_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отправка отменена.", reply_markup=get_main_menu_keyboard())
    logger.info("User %s отменил выполнение команды /send.", update.effective_user.id)
    return ConversationHandler.END

async def swap_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tokens = await get_all_user_tokens(user_id)
    if not tokens:
        await update.message.reply_text("Ошибка получения данных кошелька.")
        return ConversationHandler.END
    # Используем индекс 0 для баланса
    available_from = {sym: token for sym, token in tokens.items() if token[0] > 0}
    if not available_from:
        await update.message.reply_text("Баланс всех токенов вашего кошелька = 0, вначале пополните баланс")
        return ConversationHandler.END
    context.user_data["available_from"] = available_from
    keyboard = []
    for sym, token in available_from.items():
        # Используем индекс 1 для названия токена
        button_text = f"{sym} ({token[1]})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"swap_from_{sym}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите токен для обмена (отдаете):", reply_markup=reply_markup)
    logger.info("User %s инициировал обмен. Исходные токены: %s", user_id, list(available_from.keys()))
    return SWAP_SELECT_FROM

async def swap_from_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    token_symbol = query.data.split("_")[-1]
    available_from = context.user_data.get("available_from")
    if not available_from or token_symbol not in available_from:
        await query.edit_message_text("Ошибка: выбран неверный токен.")
        return ConversationHandler.END
    context.user_data["swap_from"] = available_from[token_symbol]
    context.user_data["swap_from_symbol"] = token_symbol
    user_id = query.from_user.id
    tokens = await get_all_user_tokens(user_id)
    keyboard = []
    for sym, token in tokens.items():
        if sym == token_symbol:
            continue
        # Используем индекс 1 для названия токена
        button_text = f"{sym} ({token[1]})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"swap_to_{sym}")])
    keyboard.append([InlineKeyboardButton("Другой токен", callback_data="swap_to_other")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("На что хотите обменять? Выберите токен:", reply_markup=reply_markup)
    logger.info("User %s выбрал исходный токен для обмена: %s", user_id, token_symbol)
    return SWAP_SELECT_TO

async def swap_to_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "swap_to_other":
        await query.edit_message_text("Чтобы добавить новый токен, введите команду /add. После добавления повторите выбор токена для обмена.")
        return ConversationHandler.END
    token_symbol = query.data.split("_")[-1]
    user_id = query.from_user.id
    tokens = await get_all_user_tokens(user_id)
    if token_symbol not in tokens:
        await query.edit_message_text("Ошибка: выбран неверный токен для обмена.")
        return ConversationHandler.END
    context.user_data["swap_to"] = tokens[token_symbol]
    context.user_data["swap_to_symbol"] = token_symbol
    await query.edit_message_text(f"Вы выбрали обменять на {token_symbol} ({tokens[token_symbol][1]}).\nВведите количество для обмена:")
    logger.info("User %s выбрал целевой токен для обмена: %s", user_id, token_symbol)
    return SWAP_ENTER_AMOUNT

async def swap_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Неверное значение. Введите число:")
        return SWAP_ENTER_AMOUNT
    swap_from = context.user_data.get("swap_from")
    if amount > swap_from[0]:
        await update.message.reply_text("Ошибка: указанное количество превышает баланс исходного токена. Введите корректное значение:")
        return SWAP_ENTER_AMOUNT
    context.user_data["swap_amount"] = amount
    from_sym = context.user_data.get("swap_from_symbol")
    to_sym = context.user_data.get("swap_to_symbol")
    from_token = swap_from
    to_token = context.user_data.get("swap_to")
    confirmation_text = (f"Подтвердите обмен:\n"
                         f"Отдаете: {amount} {from_sym} ({from_token[1]})\n"
                         f"Получаете: {amount} {to_sym} ({to_token[1]})\n"
                         f"Контракты: {from_token[2] or 'TON'} → {to_token[2] or 'TON'}")
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="swap_confirm_yes"),
         InlineKeyboardButton("Нет", callback_data="swap_confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
    logger.info("User %s запросил обмен %s %s на %s", update.effective_user.id, amount, from_sym, to_sym)
    return SWAP_CONFIRM

async def swap_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "swap_confirm_no":
        await query.edit_message_text("Обмен отменен.")
        logger.info("User %s отменил обмен токенов.", user_id)
        return ConversationHandler.END
    wallet_data = get_wallet_by_user(user_id)
    if not wallet_data:
        await query.edit_message_text("Сначала создайте кошелек командой /start.")
        return ConversationHandler.END
    from encryption import decrypt_text
    mnemonic = decrypt_text(wallet_data[1])  # получаем список слов
    amount = context.user_data.get("swap_amount")
    from_sym = context.user_data.get("swap_from_symbol")
    to_sym = context.user_data.get("swap_to_symbol")
    from_token = context.user_data.get("swap_from")
    to_token = context.user_data.get("swap_to")
    tx_hash = None
    try:
        if from_sym == "TON" and to_sym != "TON":
            logger.info("Выполняется обмен TON -> Jetton")
            tx_hash = await swap_ton_to_jetton(mnemonic, amount, to_token[2])
        elif from_sym != "TON" and to_sym == "TON":
            logger.info("Выполняется обмен Jetton -> TON")
            tx_hash = await swap_jetton_to_ton(mnemonic, amount, from_token[2])
        elif from_sym != "TON" and to_sym != "TON":
            logger.info("Выполняется обмен Jetton -> Jetton")
            tx_hash = await swap_jetton_to_jetton(mnemonic, amount, from_token[2], to_token[2])
        else:
            await query.edit_message_text("Обмен данного типа токенов не поддерживается.")
            return ConversationHandler.END
        await query.edit_message_text(f"Обмен выполнен успешно!\nTransaction hash: {tx_hash}")
        logger.info("User %s успешно обменял %s %s на %s. Tx hash: %s", user_id, amount, from_sym, to_sym, tx_hash)
    except Exception as e:
        logger.error("Ошибка при обмене для пользователя %s: %s", user_id, e)
        await query.edit_message_text("Ошибка при обмене токенов. Попробуйте позже.")
    return ConversationHandler.END
    
async def swap_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Обмен отменен.", reply_markup=get_main_menu_keyboard())
    logger.info("User %s отменил выполнение команды /swap.", update.effective_user.id)
    return ConversationHandler.END
    
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(create_wallet_callback, pattern="^create_wallet_"))
    application.add_handler(CallbackQueryHandler(export_mnemonic_callback, pattern="^export_mnemonic_"))
    application.add_handler(CommandHandler("wallet", wallet_info))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("help", help_command))
    
    add_token_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_token_start)],
        states={
            ADD_TOKEN_WAIT_CONTRACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_token_receive_contract)],
            ADD_TOKEN_CONFIRM: [CallbackQueryHandler(add_token_confirm_callback, pattern="^add_token_confirm_"),
                                CallbackQueryHandler(add_token_manual_callback, pattern="^add_token_manual_")],
            ADD_TOKEN_MANUAL_WAIT_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_token_manual_symbol)],
            ADD_TOKEN_MANUAL_WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_token_manual_name)],
        },
        fallbacks=[CommandHandler("cancel", add_token_cancel)]
    )
    application.add_handler(add_token_conv)
    
    send_conv = ConversationHandler(
        entry_points=[CommandHandler("send", send_command)],
        states={
            SEND_SELECT_TOKEN: [CallbackQueryHandler(send_token_select_callback, pattern="^send_token_")],
            SEND_ENTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_enter_address)],
            SEND_ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_enter_amount)],
            SEND_CONFIRM: [CallbackQueryHandler(send_confirm_callback, pattern="^send_confirm_")],
        },
        fallbacks=[CommandHandler("cancel", send_cancel)]
    )
    application.add_handler(send_conv)
    
    swap_conv = ConversationHandler(
        entry_points=[CommandHandler("swap", swap_start)],
        states={
            SWAP_SELECT_FROM: [CallbackQueryHandler(swap_from_select_callback, pattern="^swap_from_")],
            SWAP_SELECT_TO: [CallbackQueryHandler(swap_to_select_callback, pattern="^swap_to_")],
            SWAP_ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, swap_enter_amount)],
            SWAP_CONFIRM: [CallbackQueryHandler(swap_confirm_callback, pattern="^swap_confirm_")],
        },
        fallbacks=[CommandHandler("cancel", swap_cancel)]
    )
    application.add_handler(swap_conv)

    application.run_polling()

if __name__ == '__main__':
    main()
