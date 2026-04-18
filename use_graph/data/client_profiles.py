# Учебный набор профилей клиентов для цифрового двойника.
# В боевом контуре на месте этого модуля будет внешний сервис или хранилище профилей.

CLIENT_PROFILES = {
    "client_01": {
        "no_debts": True,
        "segment": "standard",
        "salary_project": False,
        "monthly_income_rub": 115000,
        "employment_years": 3,
        "region": "Москва",
        "age": 31,
        "active_products_count": 2,
    },
    "client_02": {
        "no_debts": True,
        "segment": "premium",
        "salary_project": True,
        "monthly_income_rub": 420000,
        "employment_years": 9,
        "region": "Санкт-Петербург",
        "age": 42,
        "active_products_count": 5,
    },
    "client_03": {
        "no_debts": False,
        "segment": "standard",
        "salary_project": True,
        "monthly_income_rub": 98000,
        "employment_years": 2,
        "region": "Казань",
        "age": 28,
        "active_products_count": 1,
    },
    "client_04": {
        "no_debts": True,
        "segment": "premium",
        "salary_project": False,
        "monthly_income_rub": 260000,
        "employment_years": 6,
        "region": "Екатеринбург",
        "age": 37,
        "active_products_count": 4,
    },
}
