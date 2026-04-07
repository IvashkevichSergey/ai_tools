from pydantic import BaseModel, create_model, Field
from typing import Literal, Type


def create_model_from_function_json(function_json: dict) -> Type[BaseModel]:
    """Автоматически создает модель из JSON описания"""

    parameters = function_json["parameters"]
    properties = parameters["properties"]
    required_fields = parameters["required"]

    field_definitions = {}

    for field_name, field_schema in properties.items():
        field_type = field_schema["type"]
        description = field_schema["description"]
        example = field_schema.get("example")

        # Определяем тип поля
        if "enum" in field_schema:
            # Для enum полей используем Literal тип
            field_type = Literal[tuple(field_schema["enum"])]
            base_type = str
        else:
            base_type = {
                "string": str,
                "integer": int,
                "number": float,
                "boolean": bool
            }.get(field_type, str)

        # Настройки Field
        field_kwargs = {
            "description": description,
            "example": example
        }

        # Добавляем ограничения
        if "maxLength" in field_schema:
            field_kwargs["max_length"] = field_schema["maxLength"]
        if "minLength" in field_schema:
            field_kwargs["min_length"] = field_schema["minLength"]

        # Определяем обязательность
        is_required = field_name in required_fields

        if is_required:
            if "enum" in field_schema:
                field_definitions[field_name] = (field_type, Field(...))
            else:
                field_definitions[field_name] = (base_type, Field(...))
        else:
            default_value = field_schema.get("default", None)
            if "enum" in field_schema:
                field_definitions[field_name] = (field_type, Field(default_value))
            else:
                field_definitions[field_name] = (base_type, Field(default_value))

    model_name = f"{function_json['name']}Input"
    return create_model(model_name, **field_definitions)
