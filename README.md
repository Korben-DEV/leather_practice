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

### Бесплатный хостинг PythonAnywhere

В Bash-консоли аккаунта:

```bash
git clone https://github.com/Korben-DEV/leather_practice.git
cd leather_practice
mkvirtualenv --python=/usr/bin/python3.13 leather-practice
pip install -r requirements.txt
python seed_public.py
```

Сохраните выведенный пароль сотрудника. В разделе **Web** создайте приложение через **Manual configuration** с Python 3.13, укажите виртуальное окружение `leather-practice`. В WSGI-файле замените содержимое на:

```python
import sys
path = '/home/ВАШ_ЛОГИН/leather_practice'
if path not in sys.path:
    sys.path.insert(0, path)
from wsgi import application
```

Добавьте static mapping: URL `/static/`, путь `/home/ВАШ_ЛОГИН/leather_practice/app/static/`. Затем нажмите **Reload**. Для публичного сайта используйте `seed_public.py`: он создаёт случайный пароль сотрудника, а обычные пользователи регистрируются самостоятельно. Не запускайте на публичном сайте `seed.py` с тестовыми паролями.

## Тестовые аккаунты

- Покупатель: `user@example.com` / `User123!`
- Сотрудник: `employee@example.com` / `Employee123!`

## Git

Проект готов для GitHub или Gitflic; база, виртуальное окружение и секреты исключены из Git. Фотографии находятся локально в `app/static/images/`, ссылки на источники — в `app/static/images/SOURCES.txt`.

XAMPP может быть установлен отдельно для учебного пункта, но этот Flask-проект запускается встроенным сервером Python и не требует Apache.
