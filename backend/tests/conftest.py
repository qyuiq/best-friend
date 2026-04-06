"""
Фикстуры pytest для тестов приложения.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import create_app, db


@pytest.fixture(scope="module")
def app():
    """Flask-приложение с in-memory БД для тестов."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture(scope="module")
def client(app):
    """Flask test client для запросов к приложению."""
    with app.app_context():
        db.create_all()
    with app.test_client() as c:
        yield c
