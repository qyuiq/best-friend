# Этот файл создает blueprint'ы и экспортирует их
from flask import Blueprint

# Создаем основные blueprint'ы
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
animals_bp = Blueprint('animals', __name__)
admin_bp = Blueprint('admin', __name__)
api_bp = Blueprint('api', __name__)

# Импортируем маршруты из каждого модуля
# Это нужно делать после создания blueprint'ов
from .main import main_bp
from .auth import auth_bp
from .animals import animals_bp
from .admin import admin_bp
from .api import api_bp

__all__ = ['main_bp', 'auth_bp', 'animals_bp', 'admin_bp', 'api_bp']