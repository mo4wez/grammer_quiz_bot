import configparser
import logging
from config import GrammerBotConfig
from pyrogram import Client

bot_config = GrammerBotConfig()

api_id = bot_config.api_id
api_hash = bot_config.api_hash
token = bot_config.token

# configure plugins
plugins = dict(root="plugins")

# read proxy file
proxy_config = configparser.ConfigParser()
proxy_config.read('proxy.ini')

proxy = {
    "scheme": proxy_config.get('proxy', 'scheme'),
    "hostname": proxy_config.get('proxy', 'hostname'),
    "port": proxy_config.getint('proxy', 'port'),
}

# Client instance
bot = Client(
    name="grammer_bot",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=token,
    plugins=plugins,
    proxy=proxy
)

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    bot.run()