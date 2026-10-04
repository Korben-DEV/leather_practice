from decimal import Decimal, InvalidOperation
from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from .. import db
from ..models import Product, ProductCategory, Article, ArticleCategory, News, Order, OrderItem, ContactRequest
from .auth import login_required

bp = Blueprint('main', __name__)


@bp.get('/')
def home():
    categories = db.session.query(ProductCategory).all()
    featured = []
    for name in ('Сумки', 'Кошельки', 'Ремни', 'Аксессуары'):
        product = db.session.query(Product).join(ProductCategory).filter(ProductCategory.name == name, Product.stock > 0).order_by(Product.id).first()
        if product: featured.append(product)
    return render_template('main/home.html', categories=categories, products=featured, articles=db.session.query(Article).filter_by(published=True).order_by(Article.created_at.desc()).limit(3).all(), news=db.session.query(News).order_by(News.created_at.desc()).limit(3).all())


@bp.get('/catalog')
def catalog():
    query = db.session.query(Product)
    selected = request.args
    if selected.get('category', '').isdigit():
        query = query.filter(Product.category_id == int(selected['category']))
    if selected.get('material'):
        query = query.filter(Product.material == selected['material'])
    for key, operator in [('min_price', Product.price.__ge__), ('max_price', Product.price.__le__)]:
        if selected.get(key):
            try:
                value = Decimal(selected[key])
                if value < 0: raise InvalidOperation
                query = query.filter(operator(value))
            except InvalidOperation:
                flash('Укажите корректную цену.', 'error')
    if selected.get('available') == '1':
        query = query.filter(Product.stock > 0)
    sort = selected.get('sort', 'new')
    orders = {'cheap': Product.price.asc(), 'expensive': Product.price.desc(), 'name': Product.name.asc(), 'new': Product.created_at.desc()}
    query = query.order_by(orders.get(sort, Product.created_at.desc()), Product.id.desc())
    return render_template('catalog/list.html', products=query.all(), categories=db.session.query(ProductCategory).all(), materials=[x[0] for x in db.session.query(Product.material).distinct().order_by(Product.material)], selected=selected)


@bp.get('/catalog/<int:product_id>')
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)
    related = db.session.query(Product).filter(Product.category_id == product.category_id, Product.id != product.id).limit(3).all()
    return render_template('catalog/detail.html', product=product, related=related)


@bp.get('/about')
def about(): return render_template('main/about.html')


@bp.get('/materials')
def materials(): return render_template('main/materials.html')


@bp.get('/articles')
def articles():
    category = request.args.get('category', type=int)
    query = db.session.query(Article).filter_by(published=True)
    if category: query = query.filter_by(category_id=category)
    return render_template('main/articles.html', articles=query.order_by(Article.created_at.desc()).all(), categories=db.session.query(ArticleCategory).all(), category=category)


@bp.get('/articles/<int:article_id>')
def article_detail(article_id):
    article = db.get_or_404(Article, article_id)
    if not article.published: abort(404)
    return render_template('main/article_detail.html', article=article)


@bp.get('/news')
def news(): return render_template('main/news.html', news=db.session.query(News).order_by(News.created_at.desc()).all())


@bp.get('/news/<int:news_id>')
def news_detail(news_id): return render_template('main/news_detail.html', item=db.get_or_404(News, news_id))


@bp.route('/contacts', methods=['GET', 'POST'])
def contacts():
    if request.method == 'POST':
        data = {key: request.form.get(key, '').strip() for key in ('name', 'email', 'subject', 'message')}
        if any(not value for value in data.values()) or '@' not in data['email'] or len(data['message']) > 5000 or any(len(data[k]) > limit for k, limit in [('name', 120), ('email', 255), ('subject', 200)]):
            flash('Заполните все поля корректно.', 'error')
        else:
            db.session.add(ContactRequest(**data))
            db.session.commit()
            flash('Сообщение сохранено. Спасибо!', 'success')
            return redirect(url_for('main.contacts'))
    return render_template('main/contacts.html')


@bp.get('/search')
def search():
    q = request.args.get('q', '').strip()[:100]
    if q:
        term = f'%{q}%'
        products = db.session.query(Product).filter(or_(Product.name.ilike(term), Product.description.ilike(term), Product.material.ilike(term))).all()
        articles = db.session.query(Article).filter(Article.published.is_(True), or_(Article.title.ilike(term), Article.content.ilike(term))).all()
        news = db.session.query(News).filter(or_(News.title.ilike(term), News.content.ilike(term))).all()
    else:
        products = articles = news = []
    return render_template('main/search.html', q=q, products=products, articles=articles, news=news)


@bp.get('/sitemap')
def sitemap(): return render_template('main/sitemap.html')


def cart_rows():
    rows = []
    cart = session.get('cart', {})
    for key, quantity in cart.items():
        product = db.session.get(Product, int(key)) if key.isdigit() else None
        if product and product.stock > 0:
            rows.append((product, quantity))
    return rows


@bp.get('/cart')
def cart():
    rows = cart_rows()
    return render_template('catalog/cart.html', rows=rows, total=sum(p.price * q for p, q in rows))


@bp.post('/cart/add/<int:product_id>')
def cart_add(product_id):
    product = db.get_or_404(Product, product_id)
    try: quantity = int(request.form.get('quantity', '1'))
    except ValueError: quantity = 0
    if quantity < 1 or product.stock < 1:
        flash('Товар недоступен.', 'error')
    else:
        cart = session.get('cart', {}).copy()
        cart[str(product.id)] = min(product.stock, cart.get(str(product.id), 0) + quantity)
        session['cart'] = cart
        flash('Товар добавлен в корзину.', 'success')
    return redirect(url_for('main.cart'))


@bp.post('/cart/update/<int:product_id>')
def cart_update(product_id):
    cart = session.get('cart', {}).copy()
    product = db.get_or_404(Product, product_id)
    try: quantity = int(request.form.get('quantity', '0'))
    except ValueError: quantity = 0
    if quantity <= 0 or product.stock == 0: cart.pop(str(product_id), None)
    else: cart[str(product_id)] = min(quantity, product.stock)
    session['cart'] = cart
    return redirect(url_for('main.cart'))


@bp.post('/cart/clear')
def cart_clear():
    session['cart'] = {}
    return redirect(url_for('main.cart'))


@bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    rows = cart_rows()
    if not rows:
        flash('Корзина пуста.', 'error')
        return redirect(url_for('main.cart'))
    if any(p.stock < q for p, q in rows):
        flash('Количество товара изменилось. Обновите корзину.', 'error')
        return redirect(url_for('main.cart'))
    if request.method == 'POST':
        data = {key: request.form.get(key, '').strip() for key in ('name', 'phone', 'email', 'address', 'comment')}
        if any(not data[k] for k in ('name', 'phone', 'email', 'address')) or '@' not in data['email'] or any(len(data[k]) > lim for k, lim in [('name', 120), ('phone', 40), ('email', 255), ('address', 400), ('comment', 5000)]):
            flash('Проверьте контактные данные и адрес.', 'error')
        else:
            order = Order(user_id=g.user.id, **data)
            db.session.add(order)
            for product, quantity in rows:
                db.session.add(OrderItem(order=order, product_id=product.id, product_name=product.name, price=product.price, quantity=quantity))
                product.stock -= quantity
            db.session.commit()
            session['cart'] = {}
            flash(f'Заказ №{order.id} оформлен.', 'success')
            return redirect(url_for('auth.my_orders'))
    return render_template('catalog/checkout.html', rows=rows, total=sum(p.price * q for p, q in rows))
