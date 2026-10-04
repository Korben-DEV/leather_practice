from pathlib import Path
from uuid import uuid4
from decimal import Decimal, InvalidOperation
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Product, ProductCategory, Article, ArticleCategory, News, Order, OrderItem, User, SupportRequest, SupportMessage, ContactRequest
from .auth import employee_required

bp = Blueprint('employee', __name__, url_prefix='/employee')

CONFIG = {
    'products': (Product, 'Товары', [('name', 'Название', 'text'), ('category_id', 'Категория', 'product_category'), ('short_description', 'Краткое описание', 'text'), ('description', 'Описание', 'textarea'), ('material', 'Материал', 'text'), ('price', 'Цена, ₽', 'number'), ('stock', 'Количество', 'number'), ('image', 'Изображение', 'image')]),
    'categories': (ProductCategory, 'Категории товаров', [('name', 'Название', 'text')]),
    'articles': (Article, 'Статьи', [('title', 'Название', 'text'), ('category_id', 'Категория', 'article_category'), ('short_description', 'Краткое описание', 'text'), ('content', 'Текст', 'textarea'), ('author', 'Автор', 'text'), ('published', 'Опубликовано', 'checkbox'), ('image', 'Изображение', 'image')]),
    'article-categories': (ArticleCategory, 'Категории статей', [('name', 'Название', 'text')]),
    'news': (News, 'Новости', [('title', 'Название', 'text'), ('short_description', 'Краткое описание', 'text'), ('content', 'Текст', 'textarea'), ('author', 'Автор', 'text'), ('image', 'Изображение', 'image')]),
}


def image_upload(file):
    if not file or not file.filename:
        return None
    ext = Path(file.filename).suffix.lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        raise ValueError('Допустимы JPG, PNG и WebP.')
    try:
        image = Image.open(file.stream)
        image.verify()
        file.stream.seek(0)
        image = Image.open(file.stream)
        image.thumbnail((1200, 900))
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        filename = f'{uuid4().hex}.webp'
        image.save(Path(current_app.config['UPLOAD_FOLDER']) / filename, 'WEBP', quality=82)
        return f'uploads/{filename}'
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError('Файл не является изображением.')


def form_data(obj, fields):
    updates = {}
    for name, label, kind in fields:
        if kind == 'image':
            image = image_upload(request.files.get(name))
            if image: updates[name] = image
        elif kind == 'checkbox':
            updates[name] = name in request.form
        else:
            value = request.form.get(name, '').strip()
            if not value:
                raise ValueError(f'Заполните поле «{label}».')
            if kind in ('product_category', 'article_category'):
                try: value = int(value)
                except ValueError: raise ValueError('Выберите категорию.')
                model = ProductCategory if kind == 'product_category' else ArticleCategory
                if not db.session.get(model, value): raise ValueError('Категория не найдена.')
            elif kind == 'number':
                try: value = Decimal(value) if name == 'price' else int(value)
                except (ValueError, InvalidOperation): raise ValueError(f'Некорректное поле «{label}».')
                if value < 0: raise ValueError(f'Поле «{label}» не может быть отрицательным.')
            elif len(value) > (10000 if kind == 'textarea' else 350):
                raise ValueError(f'Слишком длинное поле «{label}».')
            updates[name] = value
    for name, value in updates.items(): setattr(obj, name, value)


@bp.get('/')
@employee_required
def dashboard():
    counts = {'Товаров': db.session.query(Product).count(), 'Пользователей': db.session.query(User).count(), 'Заказов': db.session.query(Order).count(), 'Новых обращений': db.session.query(SupportRequest).filter_by(status='Новое').count()}
    return render_template('employee/dashboard.html', counts=counts)


@bp.get('/<section>')
@employee_required
def list_items(section):
    if section not in CONFIG: abort(404)
    model, title, fields = CONFIG[section]
    items = db.session.query(model).order_by(model.id.desc()).all()
    return render_template('employee/list.html', section=section, title=title, items=items)


@bp.route('/<section>/new', methods=['GET', 'POST'])
@employee_required
def create_item(section):
    if section not in CONFIG: abort(404)
    model, title, fields = CONFIG[section]
    obj = model()
    if request.method == 'POST':
        try:
            form_data(obj, fields)
            db.session.add(obj)
            db.session.commit()
            flash('Запись создана.', 'success')
            return redirect(url_for('employee.list_items', section=section))
        except (ValueError, OSError, IntegrityError) as error:
            db.session.rollback()
            flash('Проверьте поля: запись с таким названием уже существует.' if isinstance(error, IntegrityError) else str(error), 'error')
    return render_template('employee/form.html', title=title, fields=fields, obj=obj, section=section, categories=db.session.query(ProductCategory).all(), article_categories=db.session.query(ArticleCategory).all())


@bp.route('/<section>/<int:item_id>/edit', methods=['GET', 'POST'])
@employee_required
def edit_item(section, item_id):
    if section not in CONFIG: abort(404)
    model, title, fields = CONFIG[section]
    obj = db.get_or_404(model, item_id)
    if request.method == 'POST':
        try:
            form_data(obj, fields)
            db.session.commit()
            flash('Изменения сохранены.', 'success')
            return redirect(url_for('employee.list_items', section=section))
        except (ValueError, OSError, IntegrityError) as error:
            db.session.rollback()
            flash('Проверьте поля: запись с таким названием уже существует.' if isinstance(error, IntegrityError) else str(error), 'error')
    return render_template('employee/form.html', title=title, fields=fields, obj=obj, section=section, categories=db.session.query(ProductCategory).all(), article_categories=db.session.query(ArticleCategory).all())


@bp.post('/<section>/<int:item_id>/delete')
@employee_required
def delete_item(section, item_id):
    if section not in CONFIG: abort(404)
    model = CONFIG[section][0]
    obj = db.get_or_404(model, item_id)
    if section == 'categories' and obj.products or section == 'article-categories' and obj.articles:
        flash('Сначала удалите или перенесите связанные записи.', 'error')
    else:
        if section == 'products':
            for item in db.session.query(OrderItem).filter_by(product_id=obj.id):
                item.product_id = None
        db.session.delete(obj)
        db.session.commit()
        flash('Запись удалена.', 'success')
    return redirect(url_for('employee.list_items', section=section))


@bp.get('/orders')
@employee_required
def orders(): return render_template('employee/orders.html', orders=db.session.query(Order).order_by(Order.created_at.desc()).all())


@bp.post('/orders/<int:order_id>/status')
@employee_required
def order_status(order_id):
    order = db.get_or_404(Order, order_id)
    status = request.form.get('status')
    if status not in ('Новый', 'В обработке', 'Выполнен', 'Отменён'): abort(400)
    order.status = status
    db.session.commit()
    return redirect(url_for('employee.orders'))


@bp.get('/users')
@employee_required
def users(): return render_template('employee/users.html', users=db.session.query(User).order_by(User.id.desc()).all())


@bp.route('/users/new', methods=['GET', 'POST'])
@employee_required
def user_new(): return user_form(None)


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@employee_required
def user_edit(user_id): return user_form(db.get_or_404(User, user_id))


def user_form(user):
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')
        other = db.session.query(User).filter(func.lower(User.email) == email).first()
        if not name or len(name) > 120 or '@' not in email or len(email) > 255 or role not in ('user', 'employee') or (not user and len(password) < 8) or (password and len(password) < 8) or (other and other != user):
            flash('Проверьте имя, email, роль и пароль (минимум 8 символов).', 'error')
        else:
            if user is None:
                user = User()
                db.session.add(user)
            user.name, user.email, user.role = name, email, role
            if password: user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash('Пользователь сохранён.', 'success')
            return redirect(url_for('employee.users'))
    return render_template('employee/user_form.html', user=user)


@bp.get('/requests')
@employee_required
def requests_list():
    return render_template('employee/requests.html', tickets=db.session.query(SupportRequest).order_by(SupportRequest.created_at.desc()).all(), contacts=db.session.query(ContactRequest).order_by(ContactRequest.created_at.desc()).all())


@bp.route('/requests/<int:ticket_id>', methods=['GET', 'POST'])
@employee_required
def request_detail(ticket_id):
    ticket = db.get_or_404(SupportRequest, ticket_id)
    if request.method == 'POST':
        status = request.form.get('status')
        message = request.form.get('message', '').strip()
        if status not in ('Новое', 'В работе', 'Закрыто') or len(message) > 5000:
            flash('Проверьте статус и текст ответа.', 'error')
        else:
            ticket.status = status
            if message: db.session.add(SupportMessage(request_id=ticket.id, author_id=g.user.id, text=message))
            db.session.commit()
            flash('Обращение обновлено.', 'success')
            return redirect(url_for('employee.request_detail', ticket_id=ticket.id))
    return render_template('employee/request_detail.html', ticket=ticket)
