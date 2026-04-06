from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional, Regexp
from app.models import User, AnimalSpecies, Breed, Gender, Size, Color, HairLength
from flask_wtf.file import FileField, FileAllowed, FileRequired


class RegistrationForm(FlaskForm):
    """Форма регистрации"""
    username = StringField('Логин', validators=[
        DataRequired(message='Введите логин'),
        Length(min=3, max=50, message='Логин должен быть от 3 до 50 символов')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Введите пароль'),
        Length(min=6, max=20, message='Пароль должен быть от 6 до 20 символов')
    ])
    password2 = PasswordField('Повторите пароль', validators=[
        DataRequired(message='Подтвердите пароль'),
        EqualTo('password', message='Пароли не совпадают')
    ])
    secret_word = StringField('Секретное кодовое слово', validators=[
        DataRequired(message='Введите секретное слово')
    ])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Этот логин уже занят')


class LoginForm(FlaskForm):
    """Форма входа"""
    username = StringField('Логин', validators=[DataRequired(message='Введите логин')])
    password = PasswordField('Пароль', validators=[DataRequired(message='Введите пароль')])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class ProfileForm(FlaskForm):
    """Форма профиля пользователя"""
    first_name = StringField('Имя*', validators=[
        DataRequired(message='Введите имя'),
        Length(min=2, max=50, message='Имя должно быть от 2 до 50 символов')
    ])
    last_name = StringField('Фамилия*', validators=[
        DataRequired(message='Введите фамилию'),
        Length(min=2, max=50, message='Фамилия должна быть от 2 до 50 символов')
    ])
    patronymic = StringField('Отчество')
    email = StringField('Email*', validators=[
        DataRequired(message='Введите email'),
        Email(message='Введите корректный email'),
        Length(max=100)
    ])
    phone = StringField('Телефон*', validators=[
        DataRequired(message='Введите телефон'),
        Length(min=16, max=16, message='Телефон должен быть в формате +7 999 999-99-99')],
        render_kw={'id': 'phone', 'placeholder': '+7 (___) ___-__-__'})
    address = TextAreaField('Адрес проживания*', validators=[
        DataRequired(message='Введите адрес'),
        Length(min=10, max=500, message='Адрес должен быть от 10 до 500 символов')
    ])
    housing_type = SelectField('Тип жилья*', choices=[
        ('', 'Выберите тип жилья'),
        ('apartment', 'Квартира'),
        ('house', 'Частный дом')
    ], validators=[DataRequired(message='Выберите тип жилья')])
    rooms_count = IntegerField('Количество комнат*', validators=[
        DataRequired(message='Введите количество комнат'),
        NumberRange(min=1, max=20, message='Количество комнат должно быть от 1 до 20')
    ])
    has_children = BooleanField('Есть дети')
    has_other_animals = BooleanField('Есть другие животные')
    previous_experience = TextAreaField('Предыдущий опыт содержания животных', validators=[
        Length(max=1000, message='Описание не должно превышать 1000 символов')
    ])
    animal_care_experience = TextAreaField('Опыт ухода за животными', validators=[
        Length(max=1000, message='Описание не должно превышать 1000 символов')
    ])
    submit = SubmitField('Сохранить профиль')


class AnimalForm(FlaskForm):
    name = StringField('Кличка', validators=[DataRequired(), Length(max=50)])
    species_id = SelectField('Вид', coerce=int, validators=[DataRequired()])
    breed_id = SelectField('Порода', coerce=int, validators=[Optional()])
    age = IntegerField('Возраст (лет)', validators=[DataRequired(), NumberRange(min=0, max=50)])
    gender_id = SelectField('Пол', coerce=int, validators=[DataRequired()])
    size_id = SelectField('Размер', coerce=int, validators=[Optional()])
    color_id = SelectField('Цвет', coerce=int, validators=[Optional()])
    hair_length_id = SelectField('Длина шерсти', coerce=int, validators=[Optional()])
    description = TextAreaField('Описание', validators=[Optional(), Length(max=1000)])
    special_needs = TextAreaField('Особые потребности', validators=[Optional(), Length(max=500)])
    is_neutered = BooleanField('Стерилизован/кастрирован')
    requires_house = BooleanField('Требует частный дом')
    min_rooms = IntegerField('Минимальное количество комнат', default=1, validators=[Optional(), NumberRange(min=1, max=20)])
    for_children = BooleanField('Подходит для детей', default=True)
    with_other_animals = BooleanField('Уживается с другими животными', default=True)
    is_available = BooleanField('Доступен для усыновления', default=True)
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super(AnimalForm, self).__init__(*args, **kwargs)
        # Заполняем списки выбора
        self.species_id.choices = [(s.id, s.name) for s in AnimalSpecies.query.order_by(AnimalSpecies.name).all()]
        self.species_id.choices.insert(0, (0, '-- Выберите вид --'))

        self.gender_id.choices = [(g.id, g.name) for g in Gender.query.order_by(Gender.name).all()]
        self.gender_id.choices.insert(0, (0, '-- Выберите пол --'))

        self.size_id.choices = [(sz.id, sz.name) for sz in Size.query.order_by(Size.name).all()]
        self.size_id.choices.insert(0, (0, '-- Не указан --'))

        self.color_id.choices = [(c.id, c.name) for c in Color.query.order_by(Color.name).all()]
        self.color_id.choices.insert(0, (0, '-- Не указан --'))

        self.hair_length_id.choices = [(h.id, h.name) for h in HairLength.query.order_by(HairLength.name).all()]
        self.hair_length_id.choices.insert(0, (0, '-- Не указана --'))

        # Для пород изначально пусто, заполним динамически через JS
        self.breed_id.choices = [(0, '-- Сначала выберите вид --')]