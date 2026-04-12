# Модуль с инструментами (tools) для работы агента с базой данных задач.
# Содержит четыре инструмента: добавление задачи, просмотр списка, обновление статуса и удаление задачи.
from langchain.tools import tool
from source.db import get_conn
from langchain.tools import tool, ToolRuntime


@tool(parse_docstring=True)
def add_task(
        title: str,
        status: str = "todo",
        priority: int = 1,
        due_date: str | None = None,
) -> str:
    """Добавить новую задачу в базу данных.

    Args:
        title: Краткое текстовое описание задачи.
        status: Статус задачи. Ожидаются значения "todo", "in_progress" или "done".
        priority: Приоритет задачи как целое число. Чем больше число, тем выше приоритет.
        due_date: Необязательная дата дедлайна в формате YYYY-MM-DD. Используйте
            None или пустую строку, если дедлайн не указан.

    Returns:
        Строка с информацией о созданной задаче, включая её идентификатор.
    """
    conn = get_conn()
    with conn:
        conn.execute(
            """
            INSERT INTO tasks (title, status, priority, due_date)
            VALUES (?, ?, ?, ?)
            """,
            (title, status, priority, due_date),
        )
        row = conn.execute(
            "SELECT last_insert_rowid() AS id"
        ).fetchone()
        task_id = row["id"]
    conn.close()
    return (
        f"Задача #{task_id} создана: {title!r} "
        f"(status={status}, priority={priority}, due_date={due_date})"
    )


@tool(parse_docstring=True)
def list_tasks(status: str | None = None) -> str:
    """Показать список задач из базы данных.

    Args:
        status: Необязательный статус для фильтрации. Если указан, должен быть
            одним из "todo", "in_progress" или "done". Если параметр не задан
            или пустой, выводятся все задачи.

    Returns:
        Человекочитаемый список задач с их идентификаторами, статусами,
        приоритетами и дедлайнами.
    """
    conn = get_conn()
    if status:
        rows = conn.execute(
            """
            SELECT id, title, status, priority, COALESCE(due_date, '') AS due_date
            FROM tasks
            WHERE status = ?
            ORDER BY priority DESC, id ASC
            """,
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, title, status, priority, COALESCE(due_date, '') AS due_date
            FROM tasks
            ORDER BY priority DESC, id ASC
            """
        ).fetchall()
    conn.close()

    if not rows:
        if status:
            return f"Задач со статусом {status!r} не найдено."
        return "В базе пока нет задач."

    lines: list[str] = ["Текущие задачи:"]
    for r in rows:
        line = f"#{r['id']}: [{r['status']}] (p={r['priority']}) {r['title']}"
        if r["due_date"]:
            line += f" (due={r['due_date']})"
        lines.append(line)
    return "\n".join(lines)


@tool(parse_docstring=True)
def update_task_status(task_id: int, new_status: str) -> str:
    """Изменить статус существующей задачи.

    Args:
        task_id: Идентификатор задачи, статус которой нужно изменить.
        new_status: Новый статус задачи. Должен быть одним из:
            "todo", "in_progress" или "done".

    Returns:
        Краткое текстовое сообщение с результатом изменения.
    """
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (new_status, task_id),
        )
        updated = cur.rowcount
    conn.close()

    if updated == 0:
        return f"Задача с id={task_id} не найдена."
    return f"Статус задачи #{task_id} изменён на {new_status!r}."


@tool
def delete_task(task_id: int, runtime: ToolRuntime) -> str:
    """Удаляет задачу по ID с учётом ролей и режима."""
    user_id = runtime.context.user_id
    settings_item = runtime.store.get(("agent_settings",), user_id)
    settings = settings_item.value if settings_item else {"role": "user", "mode": "apply"}

    role = settings.get("role", "user")
    mode = settings.get("mode", "apply")

    if role == "user":
        return "У Вас нет прав на удаление задач."

    if role == "admin" and mode == "plan":
        # Переключаем режим на apply при первом вызове
        settings["mode"] = "apply"
        runtime.store.put(("agent_settings",), user_id, settings)
        return (
            "Вы администратор и работаете в режиме PLAN. "
            "Если Вы уверены, повторите запрос к этому же инструменту "
            "с теми же параметрами — после этого удаление будет разрешено."
        )

    # Реальное удаление (admin + apply)
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )
        deleted = cur.rowcount
    conn.close()

    if deleted == 0:
        return f"Задача с id={task_id} не найдена."
    return f"Задача #{task_id} удалена."

