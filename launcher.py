import os

from dotenv import load_dotenv
load_dotenv(".env")
import info
from app.bot import RematchItaliaBot
from pathlib import Path

print(f"PATH: ", str(Path()))
print(os.environ)

bot = RematchItaliaBot()

if __name__ == "__main__":
    bot.run(info.__version__)
