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

@admin_bp.route('/queue')
@admin_required
def manage_queue():
    """
    Получить список активных заявок на усыновление
    ---
    tags:
      - dictionaries
    responses:
      200:
        description: Успешный ответ (JSON или HTML)
        schema:
          type: array
          items:
            $ref: '#/definitions/AdoptionQueue'
      403:
        description: Доступ запрещён (не админ)
    security:
      - cookieAuth: []
    """
    applications = AdoptionQueue.query.filter_by(status='active').order_by(
        AdoptionQueue.animal_id, AdoptionQueue.queue_position
    ).all()

    # Если клиент хочет JSON
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        data = []
        for app in applications:
            data.append({
                'id': app.id,
                'user_id': app.user_id,
                'username': app.user.username,
                'animal_id': app.animal_id,
                'animal_name': app.animal.name,
                'queue_position': app.queue_position,
                'status': app.status,
                'created_at': app.created_at.isoformat() if app.created_at else None
            })
        return jsonify(data)

    # Иначе HTML
    return render_template('admin/queue.html', applications=applications)


@admin_bp.route('/queue/approve/<int:queue_id>', methods=['POST'])
@admin_required
def approve_application(queue_id):
    """
    Одобрить заявку на усыновление (POST)
    ---
    tags:
      - admin (actions)
    parameters:
      - name: queue_id
        in: path
        type: integer
        required: true
        description: ID заявки
    responses:
      302:
        description: Редирект на страницу управления очередью
      401:
        description: Пользователь не авторизован
      403:
        description: Доступ запрещён (не админ)
      404:
        description: Заявка не найдена
    security:
      - cookieAuth: []
    """
    app = AdoptionQueue.query.get_or_404(queue_id)
    if app.status == 'active':
        app.status = 'approved'
        # Можно также отметить животное как недоступное
        animal = Animal.query.get(app.animal_id)
        animal.is_available = False
        db.session.commit()
        flash(f'Заявка пользователя {app.user.username} на {app.animal.name} одобрена', 'success')
    else:
        flash('Заявка уже обработана', 'warning')
    return redirect(url_for('admin.manage_queue'))


@admin_bp.route('/queue/reject/<int:queue_id>', methods=['POST'])
@admin_required
def reject_application(queue_id):
    """
    Отклонить заявку на усыновление (POST)
    ---
    tags:
      - admin (actions)
    parameters:
      - name: queue_id
        in: path
        type: integer
        required: true
        description: ID заявки
    responses:
      302:
        description: Редирект на страницу управления очередью
      401:
        description: Пользователь не авторизован
      403:
        description: Доступ запрещён (не админ)
      404:
        description: Заявка не найдена
    security:
      - cookieAuth: []
    """
    app = AdoptionQueue.query.get_or_404(queue_id)
    if app.status == 'active':
        app.status = 'cancelled'
        db.session.commit()
        flash(f'Заявка пользователя {app.user.username} на {app.animal.name} отклонена', 'success')
    else:
        flash('Заявка уже обработана', 'warning')
    return redirect(url_for('admin.manage_queue'))


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
        form.breed_id.choices = [(0, '-- Сначала выберите вид --')]
    elif request.method == 'POST':
        if form.species_id.data and form.species_id.data != 0:
            breeds = Breed.query.filter_by(species_id=form.species_id.data).order_by(Breed.name).all()
            if breeds:
                form.breed_id.choices = [(b.id, b.name) for b in breeds]
                form.breed_id.choices.insert(0, (0, '-- Не указана --'))
            else:
                form.breed_id.choices = [(0, '-- Не указана --')]
        else:
            form.breed_id.choices = [(0, '-- Сначала выберите вид --')]

    if form.validate_on_submit():
        # ========== ВАЛИДАЦИЯ ФАЙЛОВ ==========
        uploaded_files = request.files.getlist('photos')
        valid_files = []
        invalid_files = []

        for file in uploaded_files:
            if file and file.filename:
                if allowed_file(file.filename):
                    valid_files.append(file)
                else:
                    invalid_files.append(file.filename)

        # Если загружены файлы, но ни одного допустимого – не создаём животное
        if uploaded_files and not valid_files:
            for fname in invalid_files:
                flash(f'Файл "{fname}" имеет недопустимое расширение. Разрешены: png, jpg, jpeg, gif, webp', 'danger')
            # Возвращаем форму с уже введёнными данными (кроме файлов)
            return render_template('admin/animal_form.html', form=form, title='Добавить животное')

        # Создаём животное
        animal = Animal()
        form.populate_obj(animal)

        # Обработка нулевых значений
        for field in ['species_id', 'breed_id', 'gender_id', 'size_id', 'color_id', 'hair_length_id']:
            if getattr(form, field).data == 0:
                setattr(animal, field, None)

        db.session.add(animal)
        db.session.flush()

        # Сохраняем только допустимые файлы
        if valid_files:
            photo_paths = save_uploaded_files(valid_files, animal.id)
            for i, path in enumerate(photo_paths):
                db.session.add(AnimalPhoto(
                    animal_id=animal.id,
                    photo_url=path,
                    is_primary=(i == 0)
                ))

        # Если были недопустимые файлы, но также были и допустимые – показываем предупреждение
        if invalid_files:
            flash(f'Некоторые файлы не были добавлены: {", ".join(invalid_files)}. Разрешены только изображения.', 'warning')

        db.session.commit()
        flash(f'Животное {animal.name} добавлено', 'success')
        return redirect(url_for('admin.manage_animals'))

    return render_template('admin/animal_form.html', form=form, title='Добавить животное')


@admin_bp.route('/animals/edit/<int:animal_id>', methods=['GET', 'POST'])
@admin_required
def edit_animal(animal_id):
    animal = Animal.query.get_or_404(animal_id)
    form = AnimalForm(obj=animal)

    # Заполняем список пород в зависимости от текущего вида
    if animal.species_id:
        breeds = Breed.query.filter_by(species_id=animal.species_id).order_by(Breed.name).all()
        form.breed_id.choices = [(b.id, b.name) for b in breeds]
        form.breed_id.choices.insert(0, (0, '-- Не указана --'))
    else:
        form.breed_id.choices = [(0, '-- Сначала выберите вид --')]

    if form.validate_on_submit():
        # ========== ВАЛИДАЦИЯ ФАЙЛОВ ==========
        uploaded_files = request.files.getlist('photos')
        valid_files = []
        invalid_files = []

        for file in uploaded_files:
            if file and file.filename:
                if allowed_file(file.filename):
                    valid_files.append(file)
                else:
                    invalid_files.append(file.filename)

        # Если загружены файлы, но ни одного допустимого – не добавляем фото, но обновляем остальные поля
        # (пользователь мог изменить другие данные)
        if uploaded_files and not valid_files:
            for fname in invalid_files:
                flash(f'Файл "{fname}" имеет недопустимое расширение. Разрешены: png, jpg, jpeg, gif, webp', 'danger')
            # Не прерываем обновление, но фото не добавляем

        # Обновляем поля животного
        form.populate_obj(animal)

        # Обработка нулевых значений
        if form.species_id.data == 0:
            animal.species_id = None
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

        # Сохраняем только допустимые файлы
        if valid_files:
            photo_paths = save_uploaded_files(valid_files, animal.id)
            has_primary = AnimalPhoto.query.filter_by(animal_id=animal.id, is_primary=True).first()
            for i, path in enumerate(photo_paths):
                db.session.add(AnimalPhoto(
                    animal_id=animal.id,
                    photo_url=path,
                    is_primary=(not has_primary and i == 0)
                ))

        # Если были недопустимые файлы, но также были и допустимые – показываем предупреждение
        if invalid_files and valid_files:
            flash(f'Некоторые файлы не были добавлены: {", ".join(invalid_files)}. Разрешены только изображения.', 'warning')

        db.session.commit()
        flash(f'Животное {animal.name} обновлено', 'success')
        return redirect(url_for('admin.manage_animals'))

    photos = AnimalPhoto.query.filter_by(animal_id=animal.id).order_by(AnimalPhoto.is_primary.desc(), AnimalPhoto.id).all()
    return render_template('admin/animal_form.html', form=form, title='Редактировать животное', animal=animal, photos=photos)

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