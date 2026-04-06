import time

from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Animal, AnimalSpecies, Breed, Gender, Size, Color, HairLength, AnimalPhoto, AdoptionQueue, User, UserProfile
from . import admin_bp
from functools import wraps
from app.forms import AnimalForm
import os
from werkzeug.utils import secure_filename
from flask import current_app


def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)  # это сохранит имя оригинальной функции
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required
def index():
    """Главная страница админ-панели"""
    # Статистика
    total_animals = Animal.query.count()
    available_animals = Animal.query.filter_by(is_available=True).count()
    total_users = User.query.count()
    active_applications = AdoptionQueue.query.filter_by(status='active').count()

    return render_template('admin/index.html',
                           total_animals=total_animals,
                           available_animals=available_animals,
                           total_users=total_users,
                           active_applications=active_applications)


@admin_bp.route('/animals')
@admin_required
def manage_animals():
    """Управление животными (список)"""
    page = request.args.get('page', 1, type=int)
    animals = Animal.query.order_by(Animal.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/animals.html', animals=animals)

@admin_bp.route('/users')
@admin_required
def manage_users():
    """
    Получить список всех пользователей
    ---
    tags:
      - dictionaries
    responses:
      200:
        description: Успешный ответ (JSON или HTML)
        schema:
          type: array
          items:
            $ref: '#/definitions/User'
      403:
        description: Доступ запрещён
    security:
      - cookieAuth: []
    """
    users = User.query.all()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        data = []
        for user in users:
            profile = user.profile
            data.append({
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'profile': {
                    'first_name': profile.first_name if profile else None,
                    'last_name': profile.last_name if profile else None,
                    'email': profile.email if profile else None,
                    'phone': profile.phone if profile else None
                } if profile else None
            })
        return jsonify(data)

    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    """
    Получить детальную информацию о пользователе
    ---
    tags:
      - admin (users)
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID пользователя
    responses:
      200:
        description: Успешный ответ (JSON или HTML)
        schema:
          $ref: '#/definitions/User'
      403:
        description: Доступ запрещён
      404:
        description: Пользователь не найден
    security:
      - cookieAuth: []
    """
    user = User.query.get_or_404(user_id)

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        profile = user.profile
        active_apps = AdoptionQueue.query.filter_by(user_id=user.id, status='active').all()
        apps_data = [{
            'id': app.id,
            'animal_id': app.animal_id,
            'animal_name': app.animal.name,
            'queue_position': app.queue_position,
            'created_at': app.created_at.isoformat() if app.created_at else None
        } for app in active_apps]

        data = {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'profile': {
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
            } if profile else None,
            'active_applications': apps_data
        }
        return jsonify(data)

    return render_template('admin/user_detail.html', user=user)


@admin_bp.route('/animals/add', methods=['GET', 'POST'])
@admin_required
def add_animal():
    form = AnimalForm()

    # Устанавливаем начальные значения для поля breed_id (при GET и перед валидацией POST)
    if request.method == 'GET':
        # При открытии формы показываем заглушку
        form.breed_id.choices = [(0, '-- Сначала выберите вид --')]
    elif request.method == 'POST':
        # Если в POST-запросе указан вид, загружаем соответствующие породы
        if form.species_id.data and form.species_id.data != 0:
            breeds = Breed.query.filter_by(species_id=form.species_id.data).order_by(Breed.name).all()
            if breeds:
                form.breed_id.choices = [(b.id, b.name) for b in breeds]
                form.breed_id.choices.insert(0, (0, '-- Не указана --'))
            else:
                form.breed_id.choices = [(0, '-- Не указана --')]  # если пород нет
        else:
            # Вид не выбран – породы недоступны
            form.breed_id.choices = [(0, '-- Сначала выберите вид --')]

    if form.validate_on_submit():
        animal = Animal()
        form.populate_obj(animal)

        # Обработка нулевых значений
        for field in ['species_id', 'breed_id', 'gender_id', 'size_id', 'color_id', 'hair_length_id']:
            if getattr(form, field).data == 0:
                setattr(animal, field, None)

        db.session.add(animal)
        db.session.flush()

        uploaded_files = request.files.getlist('photos')
        if uploaded_files and uploaded_files[0].filename:
            photo_paths = save_uploaded_files(uploaded_files, animal.id)
            for i, path in enumerate(photo_paths):
                db.session.add(AnimalPhoto(
                    animal_id=animal.id,
                    photo_url=path,
                    is_primary=(i == 0)
                ))

        db.session.commit()
        flash(f'Животное {animal.name} добавлено', 'success')
        return redirect(url_for('admin.manage_animals'))

    return render_template('admin/animal_form.html', form=form, title='Добавить животное')


@admin_bp.route('/animals/edit/<int:animal_id>', methods=['GET', 'POST'])  # маршрут для редактирования животного
@admin_required  # проверка прав администратора
def edit_animal(animal_id):
    animal = Animal.query.get_or_404(animal_id)  # получаем животное по id или 404
    form = AnimalForm(obj=animal)  # создаем форму, заполненную данными животного

    # Заполняем список пород в зависимости от текущего вида
    if animal.species_id:  # если у животного указан вид
        # получаем все породы этого вида
        breeds = Breed.query.filter_by(species_id=animal.species_id).order_by(Breed.name).all()
        form.breed_id.choices = [(b.id, b.name) for b in breeds]  # формируем список выбора
        form.breed_id.choices.insert(0, (0, '-- Не указана --'))  # добавляем пустой вариант
    else:
        # если вид не выбран, породы недоступны
        form.breed_id.choices = [(0, '-- Сначала выберите вид --')]

    if form.validate_on_submit():  # если форма отправлена и прошла валидацию
        form.populate_obj(animal)  # обновляем поля животного данными из формы

        # Аналогичная обработка нулевых значений
        if form.species_id.data == 0:  # если вид не выбран
            animal.species_id = None  # сбрасываем внешний ключ в NULL
        if form.breed_id.data == 0:
            animal.breed_id = None
        if form.gender_id.data == 0:
            animal.gender_id = None
        if form.size_id.data == 0:
            animal.size_id = None
        if form.color_id.data == 0:
            animal.color_id = None
        if form.hair_length_id.data == 0:
            animal.hair_length_id = None

        # Обработка загруженных фотографий
        uploaded_files = request.files.getlist('photos')  # получаем список новых фото
        if uploaded_files and uploaded_files[0].filename:  # если файлы загружены
            photo_paths = save_uploaded_files(uploaded_files, animal.id)  # сохраняем на диск
            # Определяем, нужно ли установить первую как главную, если нет ни одной главной
            has_primary = AnimalPhoto.query.filter_by(animal_id=animal.id, is_primary=True).first()
            for i, path in enumerate(photo_paths):  # перебираем сохраненные фото
                photo = AnimalPhoto(
                    animal_id=animal.id,
                    photo_url=path,
                    is_primary=(not has_primary and i == 0)  # если нет главной, первая становится главной
                )
                db.session.add(photo)  # добавляем фото в сессию

        db.session.commit()  # сохраняем изменения в БД
        flash(f'Животное {animal.name} обновлено', 'success')  # сообщение об успехе
        return redirect(url_for('admin.manage_animals'))  # перенаправление в список

    # Получаем все фотографии животного для отображения в форме
    photos = AnimalPhoto.query.filter_by(animal_id=animal.id).order_by(
        AnimalPhoto.is_primary.desc(), AnimalPhoto.id).all()

    return render_template('admin/animal_form.html', form=form, title='Редактировать животное', animal=animal,
                           photos=photos)  # рендерим шаблон с формой и списком фото

@admin_bp.route('/animals/hide/<int:animal_id>', methods=['POST'], endpoint='hide_animal')
@admin_required
def hide_animal(animal_id):
    """
    Скрыть животное (сделать недоступным) – POST
    ---
    tags:
      - admin (animals)
    parameters:
      - name: animal_id
        in: path
        type: integer
        required: true
        description: ID животного
    responses:
      302:
        description: Редирект на список животных
      401:
        description: Пользователь не авторизован
      403:
        description: Доступ запрещён
      404:
        description: Животное не найдено
    security:
      - cookieAuth: []
    """
    animal = Animal.query.get_or_404(animal_id)
    animal.is_available = False
    db.session.commit()
    flash(f'Животное {animal.name} скрыто из каталога', 'success')
    return redirect(url_for('admin.manage_animals'))

@admin_bp.route('/animals/show/<int:animal_id>', methods=['POST'], endpoint='show_animal')
@admin_required
def show_animal(animal_id):
    """
    Показать животное (сделать доступным) – POST
    ---
    tags:
      - admin (animals)
    parameters:
      - name: animal_id
        in: path
        type: integer
        required: true
        description: ID животного
    responses:
      302:
        description: Редирект на список животных
      401:
        description: Пользователь не авторизован
      403:
        description: Доступ запрещён
      404:
        description: Животное не найдено
    security:
      - cookieAuth: []
    """
    animal = Animal.query.get_or_404(animal_id)
    animal.is_available = True
    db.session.commit()
    flash(f'Животное {animal.name} снова доступно в каталоге', 'success')
    return redirect(url_for('admin.manage_animals'))


@admin_bp.route('/animals/delete/<int:animal_id>', methods=['POST'], endpoint='delete_animal')
@admin_required
def delete_animal(animal_id):
    """
    Удалить животное (полностью) – POST
    ---
    tags:
      - admin (animals)
    parameters:
      - name: animal_id
        in: path
        type: integer
        required: true
        description: ID животного
    responses:
      200:
        description: Редирект на список животных
      401:
        description: Пользователь не авторизован
      403:
        description: Доступ запрещён
      404:
        description: Животное не найдено
    security:
      - cookieAuth: []
    """
    animal = Animal.query.get_or_404(animal_id)

    # Удаляем физические файлы фотографий
    for photo in animal.photos:
        filepath = os.path.join(current_app.static_folder, photo.photo_url)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.session.delete(animal)
    db.session.commit()

    flash(f'Животное {animal.name} и все связанные данные удалены', 'success')
    return redirect(url_for('admin.manage_animals'))

@admin_bp.route('/photo/set_primary/<int:photo_id>', methods=['POST'], endpoint='set_primary_photo')
@admin_required
def set_primary_photo(photo_id):
    photo = AnimalPhoto.query.get_or_404(photo_id)
    # Сбросить флаг is_primary у всех фото этого животного
    AnimalPhoto.query.filter_by(animal_id=photo.animal_id).update({'is_primary': False})
    photo.is_primary = True
    db.session.commit()
    flash('Главная фотография изменена', 'success')
    return redirect(url_for('admin.edit_animal', animal_id=photo.animal_id))

@admin_bp.route('/photo/delete/<int:photo_id>', methods=['POST'], endpoint='delete_photo')
@admin_required
def delete_photo(photo_id):
    """
    Удалить фотографию – POST
    ---
    tags:
      - admin (photos)
    parameters:
      - name: photo_id
        in: path
        type: integer
        required: true
        description: ID фотографии
    responses:
      200:
        description: Редирект на страницу редактирования животного
      401:
        description: Пользователь не авторизован
      403:
        description: Доступ запрещён
      404:
        description: Фотография не найдена
    security:
      - cookieAuth: []
    """
    photo = AnimalPhoto.query.get_or_404(photo_id)
    animal_id = photo.animal_id

    # Удаляем файл с диска
    filepath = os.path.join(current_app.static_folder, photo.photo_url)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(photo)
    db.session.commit()
    flash('Фотография удалена', 'success')
    return redirect(url_for('admin.edit_animal', animal_id=animal_id))


@admin_bp.route('/get_breeds/<int:species_id>', endpoint='get_breeds_json')
@admin_required
def get_breeds(species_id):
    """
    Получить список пород по виду животного
    ---
    tags:
      - dictionaries
    parameters:
      - name: species_id
        in: path
        type: integer
        required: true
        description: ID вида животного
    responses:
      200:
        description: Список пород
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
      403:
        description: Доступ запрещён (не админ)
    security:
      - cookieAuth: []
    """
    breeds = Breed.query.filter_by(species_id=species_id).order_by(Breed.name).all()
    breed_list = [{'id': b.id, 'name': b.name} for b in breeds]
    return jsonify(breed_list)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_uploaded_files(files, animal_id):
    saved_photos = []
    # Базовая папка загрузок
    base_upload = os.path.join(current_app.static_folder, 'images', 'animals', str(animal_id))
    os.makedirs(base_upload, exist_ok=True)

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Генерируем уникальное имя (можно добавить timestamp)
            name, ext = os.path.splitext(filename)
            unique_name = f"{name}_{int(time.time())}{ext}"
            filepath = os.path.join(base_upload, unique_name)
            file.save(filepath)
            # Относительный путь для БД
            db_path = f"images/animals/{animal_id}/{unique_name}"
            saved_photos.append(db_path)
    return saved_photos