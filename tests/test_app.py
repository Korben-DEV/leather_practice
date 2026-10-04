import re
from io import BytesIO
import pytest
from PIL import Image
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User, ProductCategory, Product, Order, SupportRequest, SupportMessage, ContactRequest, News, Article, ArticleCategory


@pytest.fixture
def app(tmp_path):
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret', 'SQLALCHEMY_DATABASE_URI': f"sqlite:///{(tmp_path / 'test.db').as_posix()}", 'UPLOAD_FOLDER': str(tmp_path / 'uploads')})
    with app.app_context():
        db.create_all()
        category = ProductCategory(name='Сумки')
        db.session.add(category)
        db.session.flush()
        db.session.add(Product(name='Тестовая сумка', category_id=category.id, short_description='Описание', description='Полное описание', material='Натуральная кожа', price=2500, stock=5))
        db.session.add(User(name='Покупатель', email='buyer@example.com', password_hash=generate_password_hash('Password123!'), role='user'))
        db.session.add(User(name='Сотрудник', email='staff@example.com', password_hash=generate_password_hash('Password123!'), role='employee'))
        db.session.commit()
    yield app


@pytest.fixture
def client(app): return app.test_client()


def token(client, path):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def login(client, email='buyer@example.com'):
    return client.post('/login', data={'csrf_token': token(client, '/login'), 'email': email, 'password': 'Password123!'}, follow_redirects=True)


def test_public_pages_and_404(client):
    assert client.get('/').status_code == 200
    assert client.get('/catalog').status_code == 200
    assert client.get('/missing-page').status_code == 404


def test_filters_and_sorting(client):
    assert 'Тестовая сумка' in client.get('/catalog?category=1&material=Натуральная+кожа&min_price=2000&max_price=3000&available=1&sort=cheap').get_data(as_text=True)
    assert 'Тестовая сумка' not in client.get('/catalog?max_price=1000').get_data(as_text=True)


def test_registration_and_login(client, app):
    response = client.post('/register', data={'csrf_token': token(client, '/register'), 'name': 'Новый', 'email': 'new@example.com', 'password': 'Password123!', 'confirm': 'Password123!'}, follow_redirects=True)
    assert 'Личный кабинет' in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.query(User).filter_by(email='new@example.com').first()
    client.post('/logout', data={'csrf_token': token(client, '/profile')})
    assert 'Личный кабинет' in login(client, 'new@example.com').get_data(as_text=True)


def test_employee_access(client):
    assert client.get('/employee/').status_code == 302
    login(client)
    assert client.get('/employee/').status_code == 403
    client.post('/logout', data={'csrf_token': token(client, '/profile')})
    login(client, 'staff@example.com')
    assert client.get('/employee/').status_code == 200


def test_cart_and_order(client, app):
    client.post('/cart/add/1', data={'csrf_token': token(client, '/catalog/1'), 'quantity': 2})
    assert '5 000' not in client.get('/cart').get_data(as_text=True)  # amount is rendered without grouping
    assert '5000' in client.get('/cart').get_data(as_text=True)
    login(client)
    response = client.post('/checkout', data={'csrf_token': token(client, '/checkout'), 'name': 'Покупатель', 'phone': '+7 900 000-00-00', 'email': 'buyer@example.com', 'address': 'г. Примерск, улица Тестовая, 1', 'comment': ''}, follow_redirects=True)
    assert 'Заказ №1' in response.get_data(as_text=True)
    with app.app_context():
        order = db.session.query(Order).first()
        assert order.total == 5000
        assert order.items[0].quantity == 2


def test_csrf_required(client):
    assert client.post('/cart/clear').status_code == 400


def test_employee_crud_and_status(client, app):
    login(client, 'staff@example.com')
    for path in ('/employee/', '/employee/products', '/employee/categories', '/employee/articles', '/employee/article-categories', '/employee/news', '/employee/orders', '/employee/users', '/employee/requests'):
        assert client.get(path).status_code == 200, path
    client.post('/employee/categories/new', data={'csrf_token': token(client, '/employee/categories/new'), 'name': 'Аксессуары'})
    with app.app_context():
        category = db.session.query(ProductCategory).filter_by(name='Аксессуары').one()
        category_id = category.id
    client.post(f'/employee/categories/{category_id}/edit', data={'csrf_token': token(client, f'/employee/categories/{category_id}/edit'), 'name': 'Другие аксессуары'})
    assert 'Другие аксессуары' in client.get('/employee/categories').get_data(as_text=True)
    client.post(f'/employee/categories/{category_id}/delete', data={'csrf_token': token(client, '/employee/categories'), 'confirm': 'yes'})
    with app.app_context(): assert db.session.get(ProductCategory, category_id) is None
    response = client.post('/employee/news/new', data={'csrf_token': token(client, '/employee/news/new'), 'title': 'Тестовая новость', 'short_description': 'Короткое сообщение', 'content': 'Подробное сообщение', 'author': 'Редакция'})
    assert response.status_code == 302
    with app.app_context():
        item_id = db.session.query(News).filter_by(title='Тестовая новость').one().id
    client.post(f'/employee/news/{item_id}/edit', data={'csrf_token': token(client, f'/employee/news/{item_id}/edit'), 'title': 'Исправленная новость', 'short_description': 'Короткое сообщение', 'content': 'Подробное сообщение', 'author': 'Редакция'})
    assert 'Исправленная новость' in client.get('/news').get_data(as_text=True)
    client.post(f'/employee/news/{item_id}/delete', data={'csrf_token': token(client, '/employee/news')})
    with app.app_context(): assert db.session.get(News, item_id) is None


def test_contact_support_and_employee_reply(client, app):
    client.post('/contacts', data={'csrf_token': token(client, '/contacts'), 'name': 'Гость', 'email': 'guest@example.com', 'subject': 'Вопрос', 'message': 'Есть ли сумка?'})
    with app.app_context(): assert db.session.query(ContactRequest).count() == 1
    login(client)
    response = client.post('/support', data={'csrf_token': token(client, '/support'), 'subject': 'Доставка', 'message': 'Когда доставите?'})
    assert response.status_code == 302
    with app.app_context(): ticket_id = db.session.query(SupportRequest).one().id
    client.post('/logout', data={'csrf_token': token(client, '/profile')})
    login(client, 'staff@example.com')
    path = f'/employee/requests/{ticket_id}'
    client.post(path, data={'csrf_token': token(client, path), 'status': 'В работе', 'message': 'Свяжемся с вами завтра.'})
    with app.app_context():
        ticket = db.session.get(SupportRequest, ticket_id)
        assert ticket.status == 'В работе'
        assert db.session.query(SupportMessage).filter_by(request_id=ticket_id).count() == 2


def test_employee_creates_user_and_updates_order(client, app):
    client.post('/cart/add/1', data={'csrf_token': token(client, '/catalog/1'), 'quantity': 1})
    login(client)
    client.post('/checkout', data={'csrf_token': token(client, '/checkout'), 'name': 'Покупатель', 'phone': '1234567890', 'email': 'buyer@example.com', 'address': 'Адрес 1'})
    client.post('/logout', data={'csrf_token': token(client, '/profile')})
    login(client, 'staff@example.com')
    client.post('/employee/orders/1/status', data={'csrf_token': token(client, '/employee/orders'), 'status': 'В обработке'})
    with app.app_context(): assert db.session.get(Order, 1).status == 'В обработке'
    client.post('/employee/users/new', data={'csrf_token': token(client, '/employee/users/new'), 'name': 'Созданный', 'email': 'created@example.com', 'password': 'Password123!', 'role': 'user'})
    with app.app_context(): assert db.session.query(User).filter_by(email='created@example.com').one().role == 'user'


def test_product_and_article_crud(client, app):
    login(client, 'staff@example.com')
    data = {'csrf_token': token(client, '/employee/products/new'), 'name': 'Новый ремень', 'category_id': '1', 'short_description': 'Коротко', 'description': 'Подробно', 'material': 'Натуральная кожа', 'price': '1500', 'stock': '3'}
    assert client.post('/employee/products/new', data=data).status_code == 302
    with app.app_context(): product_id = db.session.query(Product).filter_by(name='Новый ремень').one().id
    data['csrf_token'] = token(client, f'/employee/products/{product_id}/edit')
    data['name'] = 'Исправленный ремень'
    assert client.post(f'/employee/products/{product_id}/edit', data=data).status_code == 302
    assert 'Исправленный ремень' in client.get('/catalog').get_data(as_text=True)
    assert client.post(f'/employee/products/{product_id}/delete', data={'csrf_token': token(client, '/employee/products')}).status_code == 302
    with app.app_context(): assert db.session.get(Product, product_id) is None
    assert client.post('/employee/article-categories/new', data={'csrf_token': token(client, '/employee/article-categories/new'), 'name': 'Материалы'}).status_code == 302
    article = {'csrf_token': token(client, '/employee/articles/new'), 'title': 'Новая статья', 'category_id': '1', 'short_description': 'Коротко', 'content': 'Подробно', 'author': 'Автор', 'published': 'on'}
    assert client.post('/employee/articles/new', data=article).status_code == 302
    with app.app_context(): article_id = db.session.query(Article).filter_by(title='Новая статья').one().id
    article['csrf_token'] = token(client, f'/employee/articles/{article_id}/edit')
    article['title'] = 'Исправленная статья'
    assert client.post(f'/employee/articles/{article_id}/edit', data=article).status_code == 302
    assert 'Исправленная статья' in client.get('/articles').get_data(as_text=True)
    assert client.post(f'/employee/articles/{article_id}/delete', data={'csrf_token': token(client, '/employee/articles')}).status_code == 302
    with app.app_context(): assert db.session.get(Article, article_id) is None


def test_image_upload_validation(client, app, tmp_path):
    login(client, 'staff@example.com')
    data = {'csrf_token': token(client, '/employee/products/new'), 'name': 'Сумка с фото', 'category_id': '1', 'short_description': 'Коротко', 'description': 'Подробно', 'material': 'Натуральная кожа', 'price': '1500', 'stock': '3'}
    bad = dict(data, image=(BytesIO(b'not an image'), 'bad.jpg'))
    assert 'не является изображением' in client.post('/employee/products/new', data=bad, content_type='multipart/form-data').get_data(as_text=True)
    picture = BytesIO()
    Image.new('RGB', (100, 100), '#b8cbd5').save(picture, 'PNG')
    picture.seek(0)
    good = dict(data, image=(picture, '../../unsafe.png'))
    assert client.post('/employee/products/new', data=good, content_type='multipart/form-data').status_code == 302
    with app.app_context():
        image_name = db.session.query(Product).filter_by(name='Сумка с фото').one().image
        assert image_name.startswith('uploads/') and image_name.endswith('.webp')
        assert (tmp_path / 'uploads' / image_name.split('/')[-1]).exists()


def test_single_search_across_content_types(client, app):
    with app.app_context():
        category = ArticleCategory(name='Материалы')
        db.session.add(category)
        db.session.flush()
        db.session.add(Article(title='Уход за кожей', category_id=category.id, short_description='Советы', content='Натуральная кожа', author='Редакция', published=True))
        db.session.add(News(title='Новая кожа', short_description='Новость', content='Материал поступил', author='Редакция'))
        db.session.commit()
    html = client.get('/search?q=кожа').get_data(as_text=True)
    assert 'Тестовая сумка' in html and 'Уход за кожей' in html and 'Новая кожа' in html
    assert 'Ничего не найдено' in client.get('/search?q=несуществующийзапрос').get_data(as_text=True)
