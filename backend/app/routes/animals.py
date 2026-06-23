from flask import render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.models import Animal, AnimalSpecies, Breed, Gender, Size, Color, HairLength, AnimalPhoto, AdoptionQueue, UserProfile
from app.services.queue_service import validate_queue_eligibility
from . import animals_bp
from config import Config


@animals_bp.route('/')
def list_animals():
    # Получаем параметры фильтрации из URL
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    species_id = request.args.get('species_id', type=int)
    gender_id = request.args.get('gender_id', type=int)
    min_age = request.args.get('min_age', type=int)
    max_age = request.args.get('max_age', type=int)

    # Получаем список выбранных цветов (может быть несколько)
    selected_colors = request.args.getlist('color_id')

    # Начинаем запрос только с доступных животных
    query = Animal.query.filter_by(is_available=True)

    # Применяем фильтры
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
        # Преобразуем строки в целые числа
        color_ids = [int(c) for c in selected_colors if c.isdigit()]
        if color_ids:
            query = query.filter(Animal.color_id.in_(color_ids))

    if min_age is not None:
        query = query.filter(Animal.age >= min_age)

    if max_age is not None:
        query = query.filter(Animal.age <= max_age)

    # Сортировка по дате добавления (сначала новые)
    query = query.order_by(Animal.created_at.desc())

    # Пагинация
    per_page = 12
    animals = query.paginate(page=page, per_page=per_page, error_out=False)

    # Получаем данные для фильтров
    species_list = AnimalSpecies.query.all()
    gender_list = Gender.query.all()
    color_list = Color.query.all()

    return render_template('animals/list.html',
                           animals=animals,
                           species_list=species_list,
                           gender_list=gender_list,
                           color_list=color_list,
                           search=search,
                           selected_colors=selected_colors,
                           current_filters=request.args)


@animals_bp.route('/<int:animal_id>')
def animal_detail(animal_id):
    animal = Animal.query.get_or_404(animal_id)

    # Проверяем, доступно ли животное
    if not animal.is_available:
        flash('Это животное уже нашло дом!', 'info')
        return redirect(url_for('animals.list_animals'))

    # Получаем фотографии животного
    photos = AnimalPhoto.query.filter_by(animal_id=animal_id).all()

    # Проверяем, находится ли текущий пользователь в очереди на это животное
    in_queue = False
    queue_position = None

    if current_user.is_authenticated:
        queue_entry = AdoptionQueue.query.filter_by(
            user_id=current_user.id,
            animal_id=animal_id,
            status='active'
        ).first()

        if queue_entry:
            in_queue = True
            queue_position = queue_entry.queue_position

    return render_template('animals/detail.html',
                           animal=animal,
                           photos=photos,
                           in_queue=in_queue,
                           queue_position=queue_position)


@animals_bp.route('/<int:animal_id>/join', methods=['POST'])  # маршрут для вступления в очередь
@login_required  # требует авторизации пользователя
def join_queue(animal_id):
    """
        Вступление авторизованного пользователя в очередь на усыновление питомца
        ---
        tags:
          - animals
        parameters:
          - name: animal_id
            in: path
            type: integer
            required: true
            description: Уникальный идентификатор (ID) питомца в базе данных
        responses:
          302:
            description: >
              Успешная обработка запроса. Происходит перенаправление (редирект)
              обратно на детальную страницу питомца /animals/<animal_id>. В сессию записывается
              flash-сообщение (успех вступления в очередь, либо ошибка проверки условий проживания).
          401:
            description: Пользователь не авторизован в системе (необходима сессия авторизации)
          404:
            description: Питомец с указанным ID не найден в приюте
        """
    animal = Animal.query.get_or_404(animal_id)  # получаем животное по id или 404

    # Проверка доступности животного
    if not animal.is_available:  # если животное недоступно
        flash('Это животное уже не доступно для усыновления', 'danger')
        return redirect(url_for('animals.animal_detail', animal_id=animal_id))  # обратно на страницу

    # Проверка наличия анкеты у пользователя
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()  # ищем анкету текущего пользователя
    if not profile:  # если анкета не заполнена
        flash('Сначала заполните анкету в личном кабинете', 'warning')
        return redirect(url_for('auth.profile'))  # отправляем на заполнение анкеты

    # РЕШЕНИЕ INTEGRITY ERROR: Ищем в БД запись для данной пары (user, animal) с ЛЮБЫМ статусом
    any_existing_entry = AdoptionQueue.query.filter_by(
        user_id=current_user.id,
        animal_id=animal_id
    ).first()

    # Извлекаем активную запись для передачи в функцию валидации (если она активна)
    existing_active_entry = any_existing_entry if (any_existing_entry and any_existing_entry.status == 'active') else None

    # Подсчёт количества активных заявок пользователя
    active_applications = AdoptionQueue.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).count()  # сколько всего активных заявок у пользователя

    # Вызов функции валидации соответствия бизнес-правилам
    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=active_applications,
        existing_entry=existing_active_entry,  # теперь передаем только действительно активную запись
        max_active=Config.MAX_ACTIVE_APPLICATIONS,  # максимальное количество заявок (из конфига)
    )

    if not success:  # если проверка не пройдена
        if len(errors) == 1:  # если только одна ошибка
            if 'анкету' in errors[0].lower():  # если сообщение связано с анкетой
                flash(errors[0], 'warning')
            elif 'уже в очереди' in errors[0].lower():  # если уже в очереди
                flash(errors[0], 'info')
            else:
                flash(errors[0], 'danger')  # остальные ошибки
        else:  # если несколько ошибок
            flash('Ваша анкета не соответствует требованиям этого животного:', 'danger')
            for error in errors:
                flash(f'• {error}', 'danger')  # выводим каждую ошибку списком
        return redirect(url_for('animals.animal_detail', animal_id=animal_id))  # обратно на страницу

    # Определяем следующую позицию в очереди для активных заявок
    last_in_queue = AdoptionQueue.query.filter_by(
        animal_id=animal_id,
        status='active'
    ).order_by(AdoptionQueue.queue_position.desc()).first()  # последний в очереди

    next_position = last_in_queue.queue_position + 1 if last_in_queue else 1  # следующая позиция

    # Сохраняем состояние (UPSERT - Update или Insert)
    if any_existing_entry:
        # Если запись уже существовала в базе ранее — просто переводим её в активное состояние на новую позицию
        any_existing_entry.queue_position = next_position
        any_existing_entry.status = 'active'
        # Также обновляем временные метки, чтобы в истории отображалось актуальное время вступления
        any_existing_entry.updated_at = db.func.current_timestamp()
    else:
        # Если пользователь вступает в очередь на этого питомца впервые в истории
        queue_entry = AdoptionQueue(
            user_id=current_user.id,
            animal_id=animal_id,
            queue_position=next_position,
            status='active'
        )
        db.session.add(queue_entry)  # добавляем новую запись в сессию

    # Фиксируем все сделанные изменения в базе данных
    db.session.commit()

    flash(f'Вы успешно встали в очередь на {animal.name}! Ваша позиция: {next_position}', 'success')
    return redirect(url_for('animals.animal_detail', animal_id=animal_id))  # возвращаем на страницу животного

@animals_bp.route('/cancel_queue/<int:queue_id>', methods=['POST'])
@login_required
def cancel_queue(queue_id):
    """Отмена заявки на усыновление"""
    queue_entry = AdoptionQueue.query.get_or_404(queue_id)

    # Проверяем, что заявка принадлежит текущему пользователю
    if queue_entry.user_id != current_user.id:
        flash('У вас нет прав на отмену этой заявки', 'danger')
        return redirect(url_for('main.index'))

    # Проверяем, что заявка активна
    if queue_entry.status != 'active':
        flash('Эта заявка уже была отменена или обработана', 'info')
        return redirect(url_for('auth.profile'))

    # Изменяем статус на "cancelled" (можно также удалить запись, но лучше сохранить историю)
    queue_entry.status = 'cancelled'
    db.session.commit()

    # Опционально: можно пересчитать позиции в очереди для оставшихся заявок,
    # но для простоты оставим как есть (позиция остаётся прежней, но заявка неактивна)

    flash(f'Заявка на {queue_entry.animal.name} отменена', 'success')
    return redirect(url_for('auth.profile'))