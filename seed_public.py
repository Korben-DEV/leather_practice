"""Initialize a public demo without the passwords from README."""
import secrets

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User
from seed import seed


def main():
    seed(include_test_users=False)
    app = create_app()
    with app.app_context():
        email = 'employee@example.com'
        if db.session.query(User).filter_by(email=email).first():
            print('Сотрудник уже существует. Пароль не изменён.')
            return
        password = secrets.token_urlsafe(24)
        db.session.add(User(
            name='Сотрудник', email=email,
            password_hash=generate_password_hash(password), role='employee',
        ))
        db.session.commit()
        print('Первоначальный доступ сотрудника:')
        print('Email:', email)
        print('Пароль:', password)
        print('Сохраните пароль: он выводится только при создании аккаунта.')


if __name__ == '__main__':
    main()
