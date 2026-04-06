import re

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db  # Убрали backend.
from app.models import AdoptionQueue, User, UserProfile
from app.forms import RegistrationForm, LoginForm, ProfileForm
from . import auth_bp  # Импортируем из текущего пакета
from config import Config  # Оставили как есть


@auth_bp.route('/register', methods=['GET', 'POST'])  # маршрут для регистрации
def register():
    if current_user.is_authenticated:  # если пользователь уже вошёл
        return redirect(url_for('main.index'))  # отправляем на главную

    form = RegistrationForm()  # создаём форму регистрации

    if form.validate_on_submit():  # если форма отправлена и прошла валидацию
        # Проверка секретного слова
        if form.secret_word.data != Config.SECRET_REGISTRATION_WORD:  # сравниваем с кодом из конфига
            flash('Неверное секретное кодовое слово', 'danger')  # сообщение об ошибке
            return render_template('auth/register.html', form=form)  # показываем форму снова

        # Создание пользователя
        user = User(username=form.username.data)  # создаём объект пользователя с логином из формы
        user.set_password(form.password.data)  # хешируем пароль и сохраняем

        db.session.add(user)  # добавляем пользователя в сессию
        db.session.commit()  # сохраняем в базу данных

        flash('Регистрация успешна! Теперь войдите в систему.', 'success')  # сообщение об успехе
        return redirect(url_for('auth.login'))  # перенаправляем на страницу входа

    return render_template('auth/register.html', form=form)  # отображаем пустую форму (GET-запрос)


@auth_bp.route('/login', methods=['GET', 'POST'])  # маршрут для входа
def login():
    if current_user.is_authenticated:  # если пользователь уже вошёл
        return redirect(url_for('main.index'))  # отправляем на главную

    form = LoginForm()  # создаём форму входа

    if form.validate_on_submit():  # если форма отправлена и прошла валидацию
        user = User.query.filter_by(username=form.username.data).first()  # ищем пользователя по логину

        if user is None or not user.check_password(form.password.data):  # если пользователя нет или пароль неверный
            flash('Неверный логин или пароль', 'danger')  # сообщение об ошибке
            return render_template('auth/login.html', form=form)  # показываем форму снова

        login_user(user, remember=form.remember_me.data)  # выполняем вход, запоминаем если отмечено
        flash(f'Добро пожаловать, {user.username}!', 'success')  # приветствие
        return redirect(url_for('main.index'))  # перенаправляем на главную

    return render_template('auth/login.html', form=form)  # отображаем пустую форму (GET-запрос)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])  # маршрут для профиля
@login_required  # требует авторизации
def profile():
    """Редактирование профиля"""
    # Получаем или создаем профиль с базовыми данными
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()  # ищем профиль текущего пользователя

    form = ProfileForm()  # создаём форму

    if request.method == 'GET':
        # Если профиль существует, заполняем форму его данными
        if user_profile:
            form = ProfileForm(obj=user_profile)  # инициализируем форму данными из БД
    else:
        # Обработка отправки формы
        if form.validate_on_submit():  # если данные валидны
            # raw_phone = re.sub(r'\D', '', form.phone.data)  # можно очистить номер (закомментировано)
            if user_profile is None:  # если профиля ещё нет
                user_profile = UserProfile(user_id=current_user.id)  # создаём новый
                db.session.add(user_profile)  # добавляем в сессию

            # Обновляем поля профиля из формы
            form.populate_obj(user_profile)  # копируем данные из формы в объект
            # user_profile.phone = raw_phone  # сохранение очищенного номера
            db.session.commit()  # сохраняем изменения
            flash('Профиль успешно обновлен!', 'success')
            return redirect(url_for('auth.profile'))  # обновляем страницу

    # Получаем активные заявки пользователя
    active_applications = AdoptionQueue.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).all()  # все активные заявки

    return render_template('auth/profile.html',
                           form=form,
                           active_applications=active_applications)  # отображаем шаблон с формой и заявками