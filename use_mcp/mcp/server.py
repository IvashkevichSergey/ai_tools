# Локальный MCP-сервис публикует предметные операции каталога сервисных пакетов.
# Файл содержит слой публикации инструментов и точку входа для локального запуска сервиса.

import asyncio  # Нужен для получения списка опубликованных инструментов перед запуском.
import logging  # Настраиваем служебное логирование сервера.
from mcp.server.fastmcp import FastMCP  # Подключаем серверную обёртку MCP.
from mcp_demo.mcp import service_catalog  # Подключаем предметные операции сервиса.

from rich.console import Console
console = Console()

# Ограничиваем служебное логирование MCP, чтобы вывод проверки оставался читаемым.
for logger_name in ("mcp", "mcp.server", "mcp.server.lowlevel.server"):
    logging.getLogger(logger_name).setLevel(logging.WARNING)


# Инициализируем локальный MCP-сервис для публикации инструментов.
mcp = FastMCP("ServiceCatalog", host="127.0.0.1", port=8085)

# Публикуем инструмент подбора доступных пакетов.
@mcp.tool()
def get_available_packages(client_id: str) -> dict:
    """Возвращает доступные пакеты и, при наличии, явно указывает рекомендуемый вариант."""
    return service_catalog.get_available_packages(client_id)

# Публикуем инструмент получения детальной карточки пакета.
@mcp.tool()
def get_package_details(package_code: str) -> dict:
    """Возвращает детальное описание сервисного пакета."""
    return service_catalog.get_package_details(package_code)

# Публикуем инструмент создания заявки на подключение пакета.
@mcp.tool()
def create_package_request(client_id: str, package_code: str, comment: str) -> dict:
    """Создаёт заявку на подключение выбранного сервисного пакета."""
    return service_catalog.create_package_request(client_id, package_code, comment)

# Публикуем инструмент проверки статуса ранее созданной заявки.
@mcp.tool()
def get_package_request_status(request_id: str) -> dict:
    """Возвращает статус ранее созданной заявки на подключение."""
    return service_catalog.get_package_request_status(request_id)

# Запускаем локальный MCP-сервер и выводим стартовую информацию в журнал.
if __name__ == "__main__":
    server_endpoint = f"http://{mcp.settings.host}:{mcp.settings.port}{mcp.settings.streamable_http_path}"
    published_tools = asyncio.run(mcp.list_tools())
    console.print(f"[bold green]Локальный MCP-сервер ServiceCatalog доступен по адресу {server_endpoint}[/bold green]")
    console.print("[bold cyan]Опубликованные инструменты:[/bold cyan]")
    for tool in published_tools:
        console.print(f"- {tool.name}")
    mcp.run(transport="streamable-http")

    # Для запуска в фоне: nohup python3 -m mcp_demo.mcp.server > ./mcp_demo/mcp/server.log 2>&1 &
