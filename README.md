# Линия кожи

Учебный сайт мастерской изделий из кожи: каталог, корзина, заказы и панель сотрудника.

## Стек

Python 3, Flask, SQLite, SQLAlchemy, Jinja2, HTML, CSS, JavaScript.

## Запуск

В PowerShell из папки проекта:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
python app.py
```

Откройте http://127.0.0.1:5000. `seed.py` создаёт базу и тестовые данные; повторный запуск не дублирует записи. Для проверки: `python -m pytest -q`.

При размещении на Flask-хостинге используйте WSGI-объект `wsgi:application` и задайте случайный `SECRET_KEY` через переменную окружения. Пример настроек — в `.env.example`. Локальная база находится в `instance/leather.db`.

## Тестовые аккаунты

- Покупатель: `user@example.com` / `User123!`
- Сотрудник: `employee@example.com` / `Employee123!`

## Git

Проект готов для GitHub или Gitflic; база, виртуальное окружение и секреты исключены из Git. Фотографии находятся локально в `app/static/images/`, ссылки на источники — в `app/static/images/SOURCES.txt`.

XAMPP может быть установлен отдельно для учебного пункта, но этот Flask-проект запускается встроенным сервером Python и не требует Apache.
