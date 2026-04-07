from typing import Any, Callable, List, Optional, cast

from dotenv import find_dotenv, load_dotenv
from gigachat import GigaChat
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from typing_extensions import Annotated
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model, Field
import json

from model_builder import create_model_from_function_json

cards_db = {
    "2202208XXXX11824": {"type": "МИР", "block": False},
    "4508103XXXX14732": {"type": "VISA", "block": False},
}
s_line = "\n"+("-"*50)+"\n"

@tool
def get_cards(
    *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> Optional[list[dict[str, Any]]]:
    """Возвращает состояние банковских карт пользователя в виде dict, где ключем является id карты"""
    return cast(dict[str, Any], cards_db)

def block_card (cardNumber, initiator, reason) -> str:
    print(f"{s_line}Функция блокировки карты вызвана с параметрами:\ncardNumber: {cardNumber}\ninitiator: {initiator}\nreason: {reason}{s_line}")
    if cardNumber in cards_db:
        cards_db[cardNumber]["block"] = True
        return True
    else:
        print(f"Карта с номером {cardNumber} не найдена\n")
        return False

card_block_schema = json.load(open("function.json"))

CardBlockInput = create_model_from_function_json(card_block_schema)


block_card_tool = StructuredTool.from_function(
    func = block_card,
    name = card_block_schema["name"],
    description = card_block_schema["description"],
    args_schema = CardBlockInput
)

TOOLS: List[Callable[..., Any]] = [get_cards, block_card_tool]