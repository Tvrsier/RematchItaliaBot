from dotenv import load_dotenv
load_dotenv()
import info
from app.bot import RematchItaliaBot

bot = RematchItaliaBot()

if __name__ == "__main__":
    bot.run(info.__version__)
