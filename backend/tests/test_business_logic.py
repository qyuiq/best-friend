import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.models import User, Animal
from app.routes.admin import allowed_file


def test_animal_get_age_display():
    """
    Проверяет: Animal.get_age_display() | Техника: позитивный тест

    Бизнес-логика форматирования возраста (1 год, 2 года, 5 лет, None → —).
    Используется реальный класс Animal, объект создаётся в памяти без сохранения в БД.
    """
    # Создаём объекты животного с различным возрастом
    # Обязательные поля (name, species_id, gender_id) заполняем фиктивными значениями
    assert Animal(name='Test', species_id=1, gender_id=1, age=1).get_age_display() == '1 год'
    assert Animal(name='Test', species_id=1, gender_id=1, age=2).get_age_display() == '2 года'
    assert Animal(name='Test', species_id=1, gender_id=1, age=5).get_age_display() == '5 лет'
    assert Animal(name='Test', species_id=1, gender_id=1, age=11).get_age_display() == '11 лет'
    assert Animal(name='Test', species_id=1, gender_id=1, age=None).get_age_display() == '—'


def test_user_is_admin():
    """
    Проверяет: User.is_admin() | Техника: позитивный/негативный тест

    Возвращает True только при role == 'admin'.
    Используется реальный класс User, объекты создаются в памяти.
    """
    admin = User(username='admin', role='admin')
    user = User(username='user', role='user')
    assert admin.is_admin() is True
    assert user.is_admin() is False


def test_allowed_file(app):
    """
    Проверяет: allowed_file() | Техника: позитивный тест

    Разрешённые расширения из ALLOWED_EXTENSIONS (png, jpg, jpeg, gif, webp).
    """
    with app.app_context():
        assert allowed_file('photo.jpg') is True
        assert allowed_file('IMG.PNG') is True
        assert allowed_file('pic.webp') is True
        assert allowed_file('doc.pdf') is False
        assert allowed_file('noext') is False


def test_user_set_password_check_password():
    """
    Проверяет: User.set_password(), User.check_password() | Техника: позитивный тест

    Хеширование и проверка пароля. User создаём в памяти без session.add/commit.
    """
    user = User(username='testuser', role='user')
    user.set_password('secret123')
    assert user.check_password('secret123') is True
    assert user.check_password('wrong') is False