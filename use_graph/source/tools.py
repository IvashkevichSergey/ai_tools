# LangChain Tool для получения цифрового двойника клиента.
# В графе его вызывает узел get_digital_twin_node через .invoke().
# В упражнении tool читает учебные данные из отдельного модуля data.
# В боевом контуре здесь вызывают API сервиса цифровых двойников или профиля клиента.

from pydantic import BaseModel, Field
from langchain_core.tools import tool
from graph_demo.data.client_profiles import CLIENT_PROFILES


class ClientProfile(BaseModel):
    """Структурированный ответ сервиса цифрового двойника (аналог ответа API)."""

    client_id: str = Field(description="Идентификатор клиента")
    no_debts: bool = Field(description="Отсутствие просроченной задолженности")
    segment: str = Field(description="Сегмент клиента (standard, premium и т.д.)")
    salary_project: bool = Field(description="Признак участия в зарплатном проекте")
    monthly_income_rub: int = Field(description="Среднемесячный доход клиента в рублях")
    employment_years: int = Field(description="Стаж работы клиента в годах")


@tool
def get_digital_twin(client_id: str) -> str:
    """По идентификатору клиента возвращает профиль клиента."""
    profile = CLIENT_PROFILES.get(client_id)
    if profile is None:
        raise ValueError(f"Профиль клиента не найден: {client_id}")

    # В источнике данных профиль может быть шире, но tool публикует только тот срез, который нужен текущему сценарию графа.
    payload = ClientProfile(
        client_id=client_id,
        no_debts=profile["no_debts"],
        segment=profile["segment"],
        salary_project=profile["salary_project"],
        monthly_income_rub=profile["monthly_income_rub"],
        employment_years=profile["employment_years"],
    )
    return payload.model_dump_json(ensure_ascii=False)

