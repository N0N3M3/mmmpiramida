from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware

TOKEN = '5383063117:AAFHLWuo1Y6UV0T1LwlucIkXZKFYw_RAdI8'
ADMIN_IDS = (5482991191, 2122549702, 725449291)
BOT_USERNAME = 'USBIT_miningbot'
BTC_DEPOSIT_ADDRESS = 'bc1qqx444jytve6u6h8sdchn75sqxhad642cx926n2'
LTC_DEPOSIT_ADDRESS = 'ltc1q2evsmgjs2kalqs30gg4s3r0hafegnhnl32m6nr'
USDT_ETH_DEPOSIT_ADDRESS = '0x41DAec77DeF55Ad3532c134F7922f9897007FD15'
USDT_TRON_DEPOSIT_ADDRESS = 'TWTW3aYQnff4hgkMBHJVzebAK9LAwcbxbK'
bot = Bot(TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())