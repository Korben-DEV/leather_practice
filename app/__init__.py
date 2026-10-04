import os
import secrets
from pathlib import Path
from flask import Flask, render_template, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(test_config=None):
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / '.env')
    app = Flask(__name__, instance_path=str(root / 'instance'))
    Path(app.instance_path).mkdir(exist_ok=True)
    secret_file = Path(app.instance_path) / '.secret_key'
    if not os.getenv('SECRET_KEY') and not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(48), encoding='utf-8')
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY') or secret_file.read_text(encoding='utf-8'),
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', f"sqlite:///{(root / 'instance' / 'leather.db').as_posix()}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        UPLOAD_FOLDER=str(root / 'app' / 'static' / 'uploads'),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)

    from .models import User, Product
    from .routes.main import bp as main_bp
    from .routes.auth import bp as auth_bp
    from .routes.employee import bp as employee_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)

    @app.before_request
    def current_user():
        g.user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None

    @app.context_processor
    def common():
        cart = session.get('cart', {})
        return {'cart_count': sum(cart.values()), 'current_user': g.get('user'),
                'image_url': lambda name: '/static/' + (name if name and '/' in name else 'images/' + (name or 'placeholder.svg'))}

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def too_large(error):
        return render_template('errors/413.html'), 413

    return app
