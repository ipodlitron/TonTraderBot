import re
import aiohttp
import os

COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

async def get_token_info_by_address(contract_address):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info'
    params = {'address': contract_address}
    headers = {
        'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
        'Accept': 'application/json',
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            return await response.json()

def extract_price_info(description):
    price_pattern = r'is ([\d\.,]+) USD'
    change_pattern = r'(-?[\d\.,]+) over the last 24 hours'
    volume_pattern = r'trading on .*? market\(s\) with \$([\d\.,]+) traded over the last 24 hours'

    price_match = re.search(price_pattern, description)
    change_match = re.search(change_pattern, description)
    volume_match = re.search(volume_pattern, description)

    price = price_match.group(1) if price_match else None
    change = change_match.group(1) if change_match else None
    volume = volume_match.group(1) if volume_match else None

    if price:
        price = float(price.replace(',', ''))
    return price, change, volume

async def get_token_price(contract_address):
    data = await get_token_info_by_address(contract_address)
    if data.get("status", {}).get("error_code") == 0:
        token_info = list(data.get("data", {}).values())[0]
        description = token_info.get("description", "")
        price, change, volume = extract_price_info(description)
        return price
    return None
