import os

class Config:
    # Безопасность
    SECRET_KEY = 'dev-secret-key'

    # База данных
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Папка backend
    PROJECT_ROOT = os.path.dirname(BASE_DIR)  # Папка best-friend-shelter

    # Путь к базе данных
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(PROJECT_ROOT, 'instance', 'shelter.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Папка для загрузки файлов
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'images')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 8MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Настройки приложения
    SECRET_REGISTRATION_WORD = "Приют2026"
    MAX_ACTIVE_APPLICATIONS = 3
    ANIMALS_PER_PAGE = 12

    #CSRF Токен
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']