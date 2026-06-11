import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import servers.satumimpi.config as config
from core.bot import BaseBot

bot = BaseBot(config)

if __name__ == "__main__":
    bot.run(config.TOKEN_DISCORD)
