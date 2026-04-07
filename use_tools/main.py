from langchain_gigachat.chat_models import GigaChat
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate

import langchain
import uuid
import asyncio
import re
import os

from tools import TOOLS


def clean_surrogates(text):
    """Очистка текста от суррогатных символов"""
    if isinstance(text, str):
        # Удаляем суррогатные пары
        text = re.sub(r'[\ud800-\udfff]', '', text)
        # Альтернативный способ - использовать encode/decode
        text = text.encode('utf-8', 'replace').decode('utf-8')
    return text


# Получаем токен доступа к GigaChat
if os.path.exists("/usr/local/etc/proxy-key"):
    GIGACHAT_ACCESS_TOKEN = open("/usr/local/etc/proxy-key", "r").read().strip()
else:
    sys.exit("Не могу найти токен доступа")

model = GigaChat(
    base_url="https://skilltrack.atdcode.ru/proxy/api/v1/gigachat",
    access_token=GIGACHAT_ACCESS_TOKEN,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-Max",
    verify_ssl_certs=False,
)
sp = """
Ты банковский ассистент. Будь вежлив. 
Всегда спрашивай подтверждение пользователя непосредственно перед тем, как вызвать функцию блокировки карты! 
Узнавай причину блокировки. 
Очень важно: При вызове block_card в качестве номера карты указывай только номер полученный из get_cards непосредственно перед вызовом блокировки.
"""
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", sp),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

agent = create_agent(
    model=model,
    tools=TOOLS,
    system_prompt=sp,
    checkpointer=InMemorySaver(),
)


async def main():
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    chat_history = []

    while (True):
        try:
            user_input = clean_surrogates(input("Вы: "))

            if user_input.strip().lower() in ['выход', 'exit']:
                break

            a = agent.invoke({"messages": [{"role": "user", "content": user_input}]}, config=config)
            print("Агент: ", a['messages'][-1].content)

        except KeyboardInterrupt:
            print("\nПрограмма завершена")
            break
        except Exception as e:
            print(f"Ошибка: {e}")
            print(e)


# Запуск асинхронной функции
if __name__ == "__main__":
    asyncio.run(main())
