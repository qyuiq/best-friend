from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


# ========== МОДЕЛИ ПОЛЬЗОВАТЕЛЕЙ ==========

class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    # Связи
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    queue_applications = db.relationship('AdoptionQueue', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        # Для совместимости с Werkzeug 2.3.7
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'


class UserProfile(db.Model):
    """Профиль пользователя"""
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    patronymic = db.Column(db.String(50))
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    housing_type = db.Column(db.String(20), nullable=False)  # 'apartment' or 'house'
    rooms_count = db.Column(db.Integer, nullable=False)
    has_children = db.Column(db.Boolean, default=False)
    has_other_animals = db.Column(db.Boolean, default=False)
    previous_experience = db.Column(db.Text)
    animal_care_experience = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())


# ========== СПРАВОЧНЫЕ ТАБЛИЦЫ ==========

class AnimalSpecies(db.Model):
    """Виды животных"""
    __tablename__ = 'animal_species'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    has_hair = db.Column(db.Boolean, default=False)

    # Связи
    breeds = db.relationship('Breed', backref='species', lazy=True, cascade='all, delete-orphan')
    animals = db.relationship('Animal', backref='species', lazy=True)


class Breed(db.Model):
    """Породы животных"""
    __tablename__ = 'breeds'

    id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('animal_species.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    size_category = db.Column(db.String(10), default='medium')  # small, medium, large

    # Связи
    animals = db.relationship('Animal', backref='breed', lazy=True)


class Gender(db.Model):
    """Пол животных"""
    __tablename__ = 'genders'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    # Связи
    animals = db.relationship('Animal', backref='gender', lazy=True)


class Size(db.Model):
    """Размеры животных"""
    __tablename__ = 'sizes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    # Связи
    animals = db.relationship('Animal', backref='size', lazy=True)


class Color(db.Model):
    """Цвета животных"""
    __tablename__ = 'colors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # Связи
    animals = db.relationship('Animal', backref='color', lazy=True)


class HairLength(db.Model):
    """Длина шерсти"""
    __tablename__ = 'hair_lengths'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    # Связи
    animals = db.relationship('Animal', backref='hair_length', lazy=True)


# ========== ОСНОВНЫЕ ТАБЛИЦЫ ==========

class Animal(db.Model):
    """Животные"""
    __tablename__ = 'animals'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    species_id = db.Column(db.Integer, db.ForeignKey('animal_species.id'), nullable=False)
    breed_id = db.Column(db.Integer, db.ForeignKey('breeds.id'))
    age = db.Column(db.Integer)
    gender_id = db.Column(db.Integer, db.ForeignKey('genders.id'), nullable=False)
    size_id = db.Column(db.Integer, db.ForeignKey('sizes.id'))
    color_id = db.Column(db.Integer, db.ForeignKey('colors.id'))
    hair_length_id = db.Column(db.Integer, db.ForeignKey('hair_lengths.id'))
    description = db.Column(db.Text)
    special_needs = db.Column(db.Text)
    is_neutered = db.Column(db.Boolean, default=False)
    requires_house = db.Column(db.Boolean, default=False)
    min_rooms = db.Column(db.Integer, default=1)
    for_children = db.Column(db.Boolean, default=True)
    with_other_animals = db.Column(db.Boolean, default=True)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    # Связи
    photos = db.relationship('AnimalPhoto', backref='animal', lazy=True, cascade='all, delete-orphan')
    queue_applications = db.relationship('AdoptionQueue', backref='animal', lazy=True, cascade='all, delete-orphan')
    edit_logs = db.relationship('AnimalEditLog', backref='animal', lazy=True)

    def get_age_display(self):
        """Возвращает возраст в удобочитаемом формате"""
        if self.age is None:
            return "—"
        years = self.age
        if years == 1:
            return "1 год"
        elif 2 <= years <= 4:
            return f"{years} года"
        else:
            return f"{years} лет"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'species': self.species.name if self.species else None,
            'breed': self.breed.name if self.breed else None,
            'age': self.age,
            'gender': self.gender.name if self.gender else None,
            'size': self.size.name if self.size else None,
            'color': self.color.name if self.color else None,
            'hair_length': self.hair_length.name if self.hair_length else None,
            'description': self.description,
            'special_needs': self.special_needs,
            'is_neutered': self.is_neutered,
            'requires_house': self.requires_house,
            'min_rooms': self.min_rooms,
            'for_children': self.for_children,
            'with_other_animals': self.with_other_animals,
            'main_photo': self.get_main_photo_url(),
            'photos': [p.photo_url for p in self.photos]
        }

    def get_main_photo_url(self):
        main = next((p for p in self.photos if p.is_primary), None)
        return main.photo_url if main else None


class AnimalPhoto(db.Model):
    """Фотографии животных"""
    __tablename__ = 'animal_photos'

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)
    photo_url = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class AdoptionQueue(db.Model):
    """Очередь на усыновление"""
    __tablename__ = 'adoption_queue'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)
    queue_position = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')  # active, cancelled, approved
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    __table_args__ = (db.UniqueConstraint('user_id', 'animal_id'),)


class AnimalEditLog(db.Model):
    """Лог изменений животных"""
    __tablename__ = 'animal_edit_log'

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id', ondelete='SET NULL'), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # created, updated, archived
    field_name = db.Column(db.String(50))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, default=db.func.current_timestamp())
