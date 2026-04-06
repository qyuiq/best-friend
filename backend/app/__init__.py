from flasgger import Swagger
from flask import Flask, redirect, url_for, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS

# Создаем экземпляры расширений
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    CORS(app)

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec_1.json',
                "rule_filter": lambda rule: True,  # все эндпоинты
                "model_filter": lambda tag: True,  # все модели
            }
        ],
        "debug": True,
        "securityDefinitions": {
            "cookieAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "session"  # имя cookie сессии (обычно "session" для Flask)
            }
        },
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/",
        "title": "Animal Adoption API",
        "version": "1.0.0",
        "description": "API для сервиса усыновления животных",
        "termsOfService": "",
        "definitions": {
            "Animal": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "species": {"type": "string"},
                    "breed": {"type": "string"},
                    "age": {"type": "integer"},
                    "gender": {"type": "string"},
                    "size": {"type": "string"},
                    "color": {"type": "string"},
                    "hair_length": {"type": "string"},
                    "description": {"type": "string"},
                    "special_needs": {"type": "string"},
                    "is_neutered": {"type": "boolean"},
                    "requires_house": {"type": "boolean"},
                    "min_rooms": {"type": "integer"},
                    "for_children": {"type": "boolean"},
                    "with_other_animals": {"type": "boolean"},
                    "main_photo": {"type": "string"},
                    "photos": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "username": {"type": "string"},
                    "role": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "profile": {"$ref": "#/definitions/UserProfile"},
                    "active_applications": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/AdoptionQueue"}
                    }
                }
            },
            "UserProfile": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "patronymic": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                    "housing_type": {"type": "string", "enum": ["apartment", "house"]},
                    "rooms_count": {"type": "integer"},
                    "has_children": {"type": "boolean"},
                    "has_other_animals": {"type": "boolean"},
                    "previous_experience": {"type": "string"},
                    "animal_care_experience": {"type": "string"}
                }
            },
            "AdoptionQueue": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "user_id": {"type": "integer"},
                    "username": {"type": "string"},
                    "animal_id": {"type": "integer"},
                    "animal_name": {"type": "string"},
                    "queue_position": {"type": "integer"},
                    "status": {"type": "string", "enum": ["active", "cancelled", "approved"]},
                    "created_at": {"type": "string", "format": "date-time"}
                }
            }
        }
    }

    swagger = Swagger(app, config=swagger_config)

    # Загрузка конфигурации
    app.config.from_object('config.Config')

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице'
    login_manager.login_message_category = 'info'

    # Настройка user_loader для Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        # Если запрос ожидает JSON (например, от Swagger UI или API-клиента)
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({'error': 'Authentication required'}), 401
        # Иначе перенаправляем на страницу входа (для обычных браузеров)
        return redirect(url_for('auth.login', next=request.url))

    # Импорт и регистрация blueprints из routes/__init__.py
    from .routes import main_bp, auth_bp, animals_bp, admin_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(animals_bp, url_prefix='/animals')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp)

    # Создаем таблицы в БД (если их нет)
    with app.app_context():
        db.create_all()

    # В функции create_app() после создания app:
    @app.route('/images/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    return app