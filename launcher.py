from dotenv import load_dotenv
import info

from lib.bot import RematchItaliaBot

load_dotenv()

bot = RematchItaliaBot()


if __name__ == "__main__":
    bot.run(info.__version__)