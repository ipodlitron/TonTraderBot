import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from db import get_wallet, insert_wallet
from ton_client import generate_wallet, send_transaction, get_wallet_balance
from tonsdk.crypto import mnemonic_to_wallet_key

router = Router()

# Основная клавиатура с добавленными кнопками "balance" и "help"
basic_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/wallet"), KeyboardButton(text="/export")],
        [KeyboardButton(text="/swap"), KeyboardButton(text="/send")],
        [KeyboardButton(text="/balance"), KeyboardButton(text="/help")]
    ],
    resize_keyboard=True
)

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    wallet = await get_wallet(user_id)
    if wallet:
        await message.answer("✅ Кошелек уже существует!", reply_markup=basic_keyboard)
        return
    try:
        wallet_address, mnemonic, public_key, private_key = generate_wallet()
        await insert_wallet(user_id, mnemonic, wallet_address, public_key)
        await message.answer(
            f"🔹 Адрес: `{wallet_address}`\n"
            f"📝 Seed Phrase: `{mnemonic}`\n\n"
            "⚠️ **Важно!** Сохраните seed phrase в безопасном месте. Она необходима для восстановления кошелька.",
            reply_markup=basic_keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Start error: {e}", exc_info=True)
        await message.answer("❌ Ошибка создания кошелька")

@router.message(Command("wallet"))
async def cmd_wallet(message: Message):
    user_id = message.from_user.id
    wallet = await get_wallet(user_id)
    if wallet:
        await message.answer(f"💼 Адрес: `{wallet[1]}`", parse_mode="Markdown")
    else:
        await message.answer("❌ Кошелек не найден")

@router.message(Command("export"))
async def cmd_export(message: Message):
    user_id = message.from_user.id
    wallet = await get_wallet(user_id)
    if not wallet:
        await message.answer("❌ Кошелек не найден")
        return
    try:
        await message.answer(
            f"🔑 Seed Phrase:\n`{wallet[0]}`\n\n⚠️ Сохраните её в надежном месте!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Export error: {e}", exc_info=True)
        await message.answer("❌ Ошибка экспорта кошелька")

@router.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    wallet = await get_wallet(user_id)
    if not wallet:
        await message.answer("❌ Кошелек не найден")
        return
    try:
        balances = get_wallet_balance(wallet[1])
        balance_text = "\n".join(f"{token}: {balance:.5f}" for token, balance in balances.items() if balance != 0 or token.upper() == "TON")
        await message.answer(f"💰 Балансы:\n{balance_text}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Balance error: {e}", exc_info=True)
        await message.answer("❌ Ошибка получения баланса")

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🆘 **Список команд бота:**\n\n"
        "/start - Создать новый кошелек\n"
        "/wallet - Показать адрес кошелька\n"
        "/export - Показать seed phrase для восстановления\n"
        "/balance - Показать балансы токенов\n"
        "/swap - Обмен токенов (интерактивно)\n"
        "/send - Отправка токенов (интерактивно)\n"
        "/help - Список команд\n"
    )
    await message.answer(help_text, parse_mode="Markdown")
        
# --- Интерактивная логика для swap ---
class SwapStates(StatesGroup):
    from_token = State()
    to_token = State()
    amount = State()
    confirmation = State()
        
@router.message(Command("swap"))
async def cmd_swap_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    wallet = await get_wallet(user_id)
    if not wallet:
        await message.answer("❌ Кошелек не найден. Создайте кошелек через /start")
        return
    await message.answer("Введите токен, с которого хотите обменять (например, TON)")
    await state.set_state(SwapStates.from_token)
        
@router.message(SwapStates.from_token)
async def swap_from_token(message: Message, state: FSMContext):
    from_token = message.text.strip().upper()
    if from_token != "TON":
        await message.answer("❌ В данный момент поддерживается обмен только токена TON.")
        await state.clear()
        return
    await state.update_data(from_token=from_token)
    await message.answer("Введите токен, на который хотите обменять (например, USDT)")
    await state.set_state(SwapStates.to_token)
        
@router.message(SwapStates.to_token)
async def swap_to_token(message: Message, state: FSMContext):
    to_token = message.text.strip().upper()
    if to_token not in ["TON", "USDT"]:
        await message.answer("❌ Поддерживаются только TON и USDT.")
        await state.clear()
        return
    await state.update_data(to_token=to_token)
    await message.answer("Введите количество для обмена (например, 1.23456)")
    await state.set_state(SwapStates.amount)
        
@router.message(SwapStates.amount)
async def swap_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное положительное число.")
        return
    await state.update_data(amount=amount)
    # Предпросмотр: комиссия не вычитается вручную, комиссия блокчейна рассчитывается автоматически
    preview = (
        f"Обмен: {amount:.5f} { (await state.get_data())['from_token'] } на { (await state.get_data())['to_token'] }\n"
        "Подтверждаете обмен? (Введите 'да' для подтверждения)"
    )
    await message.answer(preview)
    await state.set_state(SwapStates.confirmation)
        
@router.message(SwapStates.confirmation)
async def swap_confirmation(message: Message, state: FSMContext):
    confirmation = message.text.strip().lower()
    if confirmation != "да":
        await message.answer("Обмен отменен.")
        await state.clear()
        return
    data = await state.get_data()
    # Здесь симулируем обмен через вызов транзакции на фиксированный exchange-адрес
    exchange_address = "EQEXCHANGEADDRESS00000000000000000000000000000000"
    sender_mnemonic = (await get_wallet(message.from_user.id))[0]
    wallet_keys = mnemonic_to_wallet_key(sender_mnemonic)
    sender_private_key, _ = wallet_keys
    sender_address = (await get_wallet(message.from_user.id))[1]
    try:
        tx_result = send_transaction(sender_private_key, sender_address, exchange_address, data["amount"])
        await message.answer(f"✅ Обмен проведен!\nResponse: {tx_result}")
    except Exception as e:
        await message.answer(f"❌ Ошибка обмена: {e}")
    await state.clear()
        
# --- Интерактивная логика для send ---
class SendStates(StatesGroup):
    token = State()
    recipient = State()
    amount = State()
    confirmation = State()
            
@router.message(Command("send"))
async def cmd_send_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    wallet = await get_wallet(user_id)
    if not wallet:
        await message.answer("❌ Кошелек не найден. Создайте его через /start")
        return
    await message.answer("Введите токен для отправки (например, TON)")
    await state.set_state(SendStates.token)
            
@router.message(SendStates.token)
async def send_token(message: Message, state: FSMContext):
    token = message.text.strip().upper()
    if token != "TON":
        await message.answer("❌ Поддерживается отправка только TON.")
        await state.clear()
        return
    await state.update_data(token=token)
    await message.answer("Введите адрес получателя:")
    await state.set_state(SendStates.recipient)
            
@router.message(SendStates.recipient)
async def send_recipient(message: Message, state: FSMContext):
    recipient = message.text.strip()
    await state.update_data(recipient=recipient)
    await message.answer("Введите сумму для отправки (например, 1.23456)")
    await state.set_state(SendStates.amount)
            
@router.message(SendStates.amount)
async def send_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное положительное число.")
        return
    await state.update_data(amount=amount)
    preview = (
        f"Отправка: {amount:.5f} { (await state.get_data())['token'] }\n"
        "Подтверждаете отправку? (Введите 'да' для подтверждения)"
    )
    await message.answer(preview)
    await state.set_state(SendStates.confirmation)
            
@router.message(SendStates.confirmation)
async def send_confirmation(message: Message, state: FSMContext):
    confirmation = message.text.strip().lower()
    if confirmation != "да":
        await message.answer("Отправка отменена.")
        await state.clear()
        return
    data = await state.get_data()
    sender_mnemonic = (await get_wallet(message.from_user.id))[0]
    wallet_keys = mnemonic_to_wallet_key(sender_mnemonic)
    sender_private_key, _ = wallet_keys
    sender_address = (await get_wallet(message.from_user.id))[1]
    try:
        tx_result = send_transaction(sender_private_key, sender_address, data["recipient"], data["amount"])
        await message.answer(f"✅ Транзакция отправлена!\nResponse: {tx_result}")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
    await state.clear()
            
