from flask import Blueprint, request, jsonify
from app import db
from app.models import User, UserProfile, Animal, AnimalSpecies, Gender, Color
from app.forms import RegistrationForm, LoginForm, ProfileForm
from flask_login import login_user, logout_user, current_user, login_required
from config import Config
from sqlalchemy import or_

api_bp = Blueprint('api', __name__, url_prefix='/api')


def errors_from_form(form):
    """Преобразует ошибки формы WTForms в словарь для JSON."""
    errors = {}
    for field, messages in form.errors.items():
        errors[field] = messages[0]  # берём первое сообщение
    return errors


@api_bp.route('/register', methods=['POST'])
def register():
    """
    Регистрация нового пользователя
    ---
    tags:
      - authentication
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
            - password2
            - secret_word
          properties:
            username:
              type: string
              example: "john_doe"
            password:
              type: string
              format: password
              example: "secret123"
            password2:
              type: string
              format: password
              example: "secret123"
            secret_word:
              type: string
              example: "mysupersecret"
    responses:
      201:
        description: Регистрация успешна
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Регистрация успешна"
      400:
        description: Ошибка валидации
        schema:
          type: object
          properties:
            errors:
              type: object
              example: {"username": "Этот логин уже занят"}
    """
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.get_json()
    # Создаём форму без CSRF
    form = RegistrationForm(data=data, meta={'csrf': False})

    if form.validate():
        # Проверка секретного слова (дополнительно к форме, если его нет в форме)
        if data.get('secret_word') != Config.SECRET_REGISTRATION_WORD:
            return jsonify({'errors': {'secret_word': 'Неверное секретное слово'}}), 400

        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Регистрация успешна'}), 201
    else:
        return jsonify({'errors': errors_from_form(form)}), 400


@api_bp.route('/login', methods=['POST'])
def login():
    """
    Вход в систему через API.
    Ожидает JSON с полями: username, password, remember_me (опционально).
    """
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.get_json()
    # Используем форму для валидации
    form = LoginForm(data=data, meta={'csrf': False})

    if form.validate():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return jsonify({
                'message': 'Вход выполнен успешно',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role
                }
            }), 200
        else:
            return jsonify({'errors': {'credentials': 'Неверный логин или пароль'}}), 401
    else:
        return jsonify({'errors': errors_from_form(form)}), 400


@api_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Выход из системы (требуется аутентификация)."""
    logout_user()
    return jsonify({'message': 'Вы вышли из системы'}), 200


@api_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Получение профиля текущего пользователя."""
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    if profile:
        data = {
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'patronymic': profile.patronymic,
            'email': profile.email,
            'phone': profile.phone,
            'address': profile.address,
            'housing_type': profile.housing_type,
            'rooms_count': profile.rooms_count,
            'has_children': profile.has_children,
            'has_other_animals': profile.has_other_animals,
            'previous_experience': profile.previous_experience,
            'animal_care_experience': profile.animal_care_experience
        }
    else:
        # Если профиля нет, возвращаем пустые поля
        data = {
            'first_name': '',
            'last_name': '',
            'patronymic': '',
            'email': '',
            'phone': '',
            'address': '',
            'housing_type': '',
            'rooms_count': 0,
            'has_children': False,
            'has_other_animals': False,
            'previous_experience': '',
            'animal_care_experience': ''
        }
    return jsonify(data), 200


@api_bp.route('/profile', methods=['POST'])
@login_required
def update_profile():
    """
    Обновление профиля пользователя
    ---
    tags:
      - profile
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            first_name:
              type: string
              example: "Иван"
            last_name:
              type: string
              example: "Петров"
            patronymic:
              type: string
              example: "Иванович"
            email:
              type: string
              format: email
              example: "ivan@example.com"
            phone:
              type: string
              example: "+7 999 123-45-67"
            address:
              type: string
              example: "ул. Ленина, д. 1, кв. 1"
            housing_type:
              type: string
              enum: [apartment, house]
              example: "apartment"
            rooms_count:
              type: integer
              example: 2
            has_children:
              type: boolean
              example: true
            has_other_animals:
              type: boolean
              example: false
            previous_experience:
              type: string
              example: "Был кот 5 лет"
            animal_care_experience:
              type: string
              example: "Опыт ухода за собаками"
    responses:
      200:
        description: Профиль обновлён
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Профиль обновлён"
      400:
        description: Ошибка валидации
        schema:
          type: object
          properties:
            errors:
              type: object
      401:
        description: Не авторизован
    security:
      - cookieAuth: []
    """
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.get_json()
    # Используем форму для валидации
    form = ProfileForm(data=data, meta={'csrf': False})

    if form.validate():
        profile = UserProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)

        # Обновляем поля
        profile.first_name = form.first_name.data
        profile.last_name = form.last_name.data
        profile.patronymic = form.patronymic.data
        profile.email = form.email.data
        profile.phone = form.phone.data
        profile.address = form.address.data
        profile.housing_type = form.housing_type.data
        profile.rooms_count = form.rooms_count.data
        profile.has_children = form.has_children.data
        profile.has_other_animals = form.has_other_animals.data
        profile.previous_experience = form.previous_experience.data
        profile.animal_care_experience = form.animal_care_experience.data

        db.session.commit()
        return jsonify({'message': 'Профиль обновлён'}), 200
    else:
        return jsonify({'errors': errors_from_form(form)}), 400


@api_bp.route('/animals', methods=['GET'])
def get_animals():
    """
    Получить список доступных животных с фильтрацией
    ---
    tags:
      - animals
    parameters:
      - name: search
        in: query
        type: string
        description: Поиск по имени или описанию
      - name: species_id
        in: query
        type: integer
        description: ID вида
      - name: gender_id
        in: query
        type: integer
        description: ID пола
      - name: min_age
        in: query
        type: integer
        description: Минимальный возраст
      - name: max_age
        in: query
        type: integer
        description: Максимальный возраст
      - name: color_id
        in: query
        type: array
        items:
          type: integer
        collectionFormat: multi
        description: Один или несколько ID цветов
    responses:
      200:
        description: Список животных
        schema:
          type: object
          properties:
            items:
              type: array
              items:
                $ref: '#/definitions/Animal'
            total:
              type: integer
            page:
              type: integer
            pages:
              type: integer
            per_page:
              type: integer
      400:
        description: Неверные параметры запроса
    """
    # Используйте логику из animals_bp.list_animals, но верните JSON

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    search = request.args.get('search', '').strip()
    species_id = request.args.get('species_id', type=int)
    gender_id = request.args.get('gender_id', type=int)
    min_age = request.args.get('min_age', type=int)
    max_age = request.args.get('max_age', type=int)
    selected_colors = request.args.getlist('color_id', type=int)

    query = Animal.query.filter_by(is_available=True)

    if search:
        query = query.filter(
            or_(
                Animal.name.ilike(f'%{search}%'),
                Animal.description.ilike(f'%{search}%')
            )
        )
    if species_id:
        query = query.filter_by(species_id=species_id)
    if gender_id:
        query = query.filter_by(gender_id=gender_id)
    if selected_colors:
        query = query.filter(Animal.color_id.in_(selected_colors))
    if min_age is not None:
        query = query.filter(Animal.age >= min_age)
    if max_age is not None:
        query = query.filter(Animal.age <= max_age)

    pagination = query.order_by(Animal.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    animals = []
    for animal in pagination.items:
        animals.append(animal.to_dict())  # предположим, что у модели есть метод to_dict()

    return jsonify({
        'items': animals,
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
        'per_page': pagination.per_page
    })

@api_bp.route('/animals/<int:animal_id>', methods=['GET'])
def get_animal(animal_id):
    """
    Получить детальную информацию о животном
    ---
    tags:
      - animals
    parameters:
      - name: animal_id
        in: path
        type: integer
        required: true
        description: ID животного
    responses:
      200:
        description: Информация о животном
        schema:
          $ref: '#/definitions/Animal'
      404:
        description: Животное не найдено или недоступно
    """
    animal = Animal.query.get_or_404(animal_id)
    if not animal.is_available:
        return jsonify({'error': 'Animal not available'}), 404
    return jsonify(animal.to_dict())