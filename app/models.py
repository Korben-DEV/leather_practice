from datetime import datetime, timezone
from . import db


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')


class ProductCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    products = db.relationship('Product', backref='category', lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('product_category.id'), nullable=False)
    short_description = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)
    material = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image = db.Column(db.String(255), default='placeholder.svg')
    stock = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=now, nullable=False)


class ArticleCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    articles = db.relationship('Article', backref='category', lazy=True)


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('article_category.id'), nullable=False)
    short_description = db.Column(db.String(350), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), default='placeholder.svg')
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    author = db.Column(db.String(120), nullable=False)
    published = db.Column(db.Boolean, default=True, nullable=False)


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    short_description = db.Column(db.String(350), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), default='placeholder.svg')
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    author = db.Column(db.String(120), nullable=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(400), nullable=False)
    comment = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default='Новый')
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')
    user = db.relationship('User', backref='orders')

    @property
    def total(self):
        return sum(item.price * item.quantity for item in self.items)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    product_name = db.Column(db.String(160), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product')


class ContactRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)


class SupportRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Новое')
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    user = db.relationship('User', backref='support_requests')
    messages = db.relationship('SupportMessage', backref='request', cascade='all, delete-orphan', order_by='SupportMessage.created_at')


class SupportMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('support_request.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)
    author = db.relationship('User')
