from functools import wraps
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, abort
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from .. import db
from ..models import User, Order, SupportRequest, SupportMessage

bp = Blueprint('auth', __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            flash('Сначала войдите в аккаунт.', 'error')
            return redirect(url_for('auth.login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


def employee_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user.role != 'employee':
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not name or len(name) > 120 or '@' not in email or len(email) > 255 or len(password) < 8 or password != request.form.get('confirm'):
            flash('Проверьте поля. Пароль должен содержать минимум 8 символов и совпадать с подтверждением.', 'error')
        elif db.session.query(User).filter(func.lower(User.email) == email).first():
            flash('Этот email уже зарегистрирован.', 'error')
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            cart = session.get('cart', {})
            session.clear()
            session['user_id'] = user.id
            session['cart'] = cart
            return redirect(url_for('auth.profile'))
    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = db.session.query(User).filter(func.lower(User.email) == request.form.get('email', '').strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password', '')):
            cart = session.get('cart', {})
            session.clear()
            session['user_id'] = user.id
            session['cart'] = cart
            next_url = request.args.get('next', '')
            return redirect(next_url if next_url.startswith('/') and not next_url.startswith('//') else url_for('auth.profile'))
        flash('Неверный email или пароль.', 'error')
    return render_template('auth/login.html')


@bp.post('/logout')
@login_required
def logout():
    cart = session.get('cart', {})
    session.clear()
    session['cart'] = cart
    return redirect(url_for('main.home'))


@bp.get('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')


@bp.get('/my-orders')
@login_required
def my_orders():
    orders = db.session.query(Order).filter_by(user_id=g.user.id).order_by(Order.created_at.desc()).all()
    return render_template('auth/orders.html', orders=orders)


@bp.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        if not subject or not message or len(subject) > 200 or len(message) > 5000:
            flash('Укажите тему и сообщение (до 5000 символов).', 'error')
        else:
            ticket = SupportRequest(user_id=g.user.id, subject=subject)
            db.session.add(ticket)
            db.session.flush()
            db.session.add(SupportMessage(request_id=ticket.id, author_id=g.user.id, text=message))
            db.session.commit()
            return redirect(url_for('auth.support_detail', ticket_id=ticket.id))
    tickets = db.session.query(SupportRequest).filter_by(user_id=g.user.id).order_by(SupportRequest.created_at.desc()).all()
    return render_template('auth/support.html', tickets=tickets)


@bp.get('/support/<int:ticket_id>')
@login_required
def support_detail(ticket_id):
    ticket = db.get_or_404(SupportRequest, ticket_id)
    if ticket.user_id != g.user.id and g.user.role != 'employee':
        abort(403)
    return render_template('auth/support_detail.html', ticket=ticket)
