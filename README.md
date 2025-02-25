# TonTraderBot

**This is a concept application and is currently under development.**

TonTraderBot is a Telegram bot designed to help users manage their TON blockchain wallets securely and interactively. This is a proof-of-concept project and is not production-ready.

## Overview

TonTraderBot allows users to:
- Generate a new wallet with a seed phrase (mnemonic) for recovery.
- View their wallet address and export the seed phrase.
- Check wallet balances (with TON balance always shown—even if 0—and other tokens only if nonzero, rounded to 5 decimal places).
- Interactively swap tokens and send transactions.
- Use a simple, intuitive interface via Telegram commands and inline buttons.

## Features

- **Wallet Generation:** Create a new TON wallet using a generated mnemonic and derive keys from it.
- **Wallet Export:** Retrieve your seed phrase for wallet recovery.
- **Balance Inquiry:** Display the balances of tokens on your wallet.
- **Interactive Swap:** Follow an interactive flow to swap tokens with confirmation steps.
- **Interactive Send:** Interactively send tokens with recipient address input and confirmation.
- **Telegram Integration:** Fully controlled via Telegram commands and inline buttons.

## Technologies Used

- **Python 3.8+**
- **aiogram** – Telegram Bot API framework
- **tonsdk** – TON blockchain SDK for Python
- **mnemonic** – For seed phrase generation
- **aiosqlite** – Asynchronous SQLite database management
- **python-dotenv** – Environment variable management
- **requests** – HTTP requests to TONCENTER API

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/ipodlitron/TonTraderBot.git
   cd TonTraderBot

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt

4. **Create a .env file in the root directory with the following content:**

   ```bash
   TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
   TONCENTER_API_URL=https://toncenter.com/api/v2/jsonRPC
   TON_API_KEY=YOUR_TON_API_KEY_HERE
   DATABASE=wallets.db
Replace YOUR_TELEGRAM_BOT_TOKEN_HERE and YOUR_TON_API_KEY_HERE with your actual credentials.

## Usage

Run the bot: 
    
    ```bash
    python main.py

**Interact with the bot on Telegram:**

- /start — Create or load your wallet.
- /wallet — Display your wallet address.
- /export — Show your seed phrase.
- /balance — Check token balances.
- /swap — Initiate an interactive token swap.
- /send — Initiate an interactive token send.
- /help — List all available commands and their descriptions.

## **Project Structure**

TonTraderBot/

├── main.py

├── config.py

├── handlers.py

├── ton_client.py

├── db.py

├── .env

├── requirements.txt

└── README.md


## Contributing

Contributions, bug reports, and feature suggestions are welcome! Please note that this is an early-stage concept application, so use it at your own risk.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Disclaimer

This is a concept application under active development. It is provided for educational purposes and as a proof-of-concept only. Do not use it for storing large amounts of funds until it has been fully tested and audited.

Feel free to open issues or submit pull requests if you have suggestions or encounter any problems. Enjoy exploring TonTraderBot!
