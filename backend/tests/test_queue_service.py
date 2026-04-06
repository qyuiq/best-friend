"""
=============================================================================
MOCK-ТЕСТИРОВАНИЕ: validate_queue_eligibility()
=============================================================================

Тесты используют техники тест-дизайна:
- ГРАНИЧНЫЕ ЗНАЧЕНИЯ (BVA): active_count (2, 3), rooms_count (min-1, min, min+1)
- КЛАССЫ ЭКВИВАЛЕНТНОСТИ: один представитель из каждого класса (см. EQUIVALENCE_CLASSES.md)
- ТАБЛИЦА ПРИНЯТИЯ РЕШЕНИЙ: комбинации условий (см. DECISION_TABLE.md)

Функционал покрыт частично - выбраны репрезентативные тесты по каждой технике.

ЗАПУСК: pytest tests/test_queue_service.py -v
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock
from app.services.queue_service import validate_queue_eligibility

# =============================================================================
# ТАБЛИЦА ПРИНЯТИЯ РЕШЕНИЙ (Decision Table)
# =============================================================================


def test_decision_table_rule1_success():
    """
    DECISION TABLE RULE 1: Все условия выполнены.

    Класс: животное доступно, требования по жилью/комнатам/детям/животным выполнены,
           лимит заявок не превышен, пользователь не в очереди.
    Представитель: animal.is_available=True, requires_house=False, min_rooms=1,
                   for_children=True, with_other_animals=True;
                   profile.housing_type='apartment', rooms_count=2,
                   has_children=False, has_other_animals=False;
                   active_count=0, existing_entry=None.
    Ожидаем: success=True, errors=[].
    """
    animal = Mock()
    animal.is_available = True
    animal.requires_house = False
    animal.min_rooms = 1
    animal.for_children = True
    animal.with_other_animals = True

    profile = Mock()
    profile.housing_type = 'apartment'
    profile.rooms_count = 2
    profile.has_children = False
    profile.has_other_animals = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is True
    assert errors == []


def test_decision_table_rule2_animal_unavailable():
    """
    DECISION TABLE RULE 2: Животное недоступно.

    Класс: is_available=False.
    Представитель: animal.is_available=False (остальные поля не важны).
    Ожидаем: success=False, ошибка о недоступности животного.
    """
    animal = Mock()
    animal.is_available = False

    profile = Mock()

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is False
    assert 'не доступно' in errors[0].lower()


def test_decision_table_rule3_no_profile():
    """
    DECISION TABLE RULE 3: У пользователя нет анкеты.

    Класс: profile is None.
    Представитель: profile=None, animal.is_available=True.
    Ожидаем: success=False, ошибка о необходимости заполнить анкету.
    """
    animal = Mock()
    animal.is_available = True

    profile = None

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is False
    assert 'анкету' in errors[0].lower()


def test_decision_table_rule4_already_in_queue():
    """
    DECISION TABLE RULE 4: Пользователь уже в очереди на это животное.

    Класс: existing_entry is not None (активная заявка).
    Представитель: existing_entry (любой объект, не None),
                   animal.is_available=True, profile есть.
    Ожидаем: success=False, ошибка о том, что уже в очереди.
    """
    animal = Mock()
    animal.is_available = True

    profile = Mock()

    existing_entry = Mock()
    existing_entry.user_id = 1
    existing_entry.animal_id = 1

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=1,
        existing_entry=existing_entry,
    )
    assert success is False
    assert 'уже в очереди' in errors[0].lower()


def test_decision_table_rule6_house_required():
    """
    DECISION TABLE RULE 6: Животному требуется частный дом, у пользователя квартира.

    Класс: requires_house=True И housing_type='apartment'.
    Представитель: animal.requires_house=True, profile.housing_type='apartment',
                   остальные условия проходные.
    Ожидаем: success=False, ошибка про частный дом.
    """
    animal = Mock()
    animal.is_available = True
    animal.requires_house = True
    animal.min_rooms = 1
    animal.for_children = True
    animal.with_other_animals = True

    profile = Mock()
    profile.housing_type = 'apartment'
    profile.rooms_count = 2
    profile.has_children = False
    profile.has_other_animals = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is False
    assert 'частный дом' in errors[0].lower()


# =============================================================================
# ГРАНИЧНЫЕ ЗНАЧЕНИЯ (Boundary Value Analysis)
# =============================================================================

def test_bva_active_count_at_boundary_2_pass():
    """
    BVA: Активных заявок 2 (меньше лимита 3) – разрешено.

    Класс: active_count = 2.
    Представитель: active_count=2, остальные условия проходные.
    Ожидаем: success=True.
    """
    animal = Mock()
    animal.is_available = True
    animal.requires_house = False
    animal.min_rooms = 1
    animal.for_children = True
    animal.with_other_animals = True

    profile = Mock()
    profile.housing_type = 'apartment'
    profile.rooms_count = 1
    profile.has_children = False
    profile.has_other_animals = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=2,
        existing_entry=None,
    )
    assert success is True


def test_bva_active_count_at_boundary_3_fail():
    """
    BVA: Активных заявок 3 (лимит достигнут) – отказ.

    Класс: active_count = 3.
    Представитель: active_count=3, остальные условия проходные.
    Ожидаем: success=False, ошибка о превышении лимита.
    """
    animal = Mock()
    animal.is_available = True
    animal.requires_house = False
    animal.min_rooms = 1
    animal.for_children = True
    animal.with_other_animals = True

    profile = Mock()
    profile.housing_type = 'apartment'
    profile.rooms_count = 1
    profile.has_children = False
    profile.has_other_animals = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=3,
        existing_entry=None,
    )
    assert success is False
    assert any(keyword in errors[0].lower() for keyword in ['3', 'более', 'лимит'])


def test_bva_rooms_count_below_boundary_fail():
    """
    BVA: Количество комнат ниже минимального – отказ.

    Класс: rooms_count < min_rooms.
    Представитель: animal.min_rooms=3, profile.rooms_count=2.
    Ожидаем: success=False, ошибка о недостаточном количестве комнат.
    """
    animal = Mock()
    animal.is_available = True
    animal.min_rooms = 3
    animal.requires_house = False
    animal.for_children = True
    animal.with_other_animals = True

    profile = Mock()
    profile.rooms_count = 2
    profile.housing_type = 'apartment'
    profile.has_children = False
    profile.has_other_animals = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is False
    assert 'комнат' in errors[0].lower()


def test_bva_rooms_count_at_boundary_pass():
    """
    BVA: Количество комнат равно минимальному – разрешено.

    Класс: rooms_count == min_rooms.
    Представитель: animal.min_rooms=3, profile.rooms_count=3.
    Ожидаем: success=True.
    """
    animal = Mock()
    animal.is_available = True
    animal.min_rooms = 3
    animal.requires_house = False
    animal.for_children = True
    animal.with_other_animals = True

    profile = Mock()
    profile.rooms_count = 3
    profile.housing_type = 'apartment'
    profile.has_children = False
    profile.has_other_animals = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is True


def test_bva_rooms_count_above_boundary_pass():
    """
    BVA: Количество комнат выше минимального – разрешено.

    Класс: rooms_count > min_rooms.
    Представитель: animal.min_rooms=3, profile.rooms_count=4.
    Ожидаем: success=True.
    """
    animal = Mock()
    animal.is_available = True
    animal.min_rooms = 3
    animal.requires_house = False
    animal.for_children = True
    animal.with_other_animals = True

    profile = Mock()
    profile.rooms_count = 4
    profile.housing_type = 'apartment'
    profile.has_children = False
    profile.has_other_animals = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is True


# =============================================================================
# КЛАССЫ ЭКВИВАЛЕНТНОСТИ (Equivalence Partitioning)
# =============================================================================
#
# Идея: делим входные данные на группы (классы), внутри которых система ведёт
# себя одинаково. Из каждой группы берём ОДНО значение (представителя).
# Подробнее: tests/EQUIVALENCE_CLASSES.md
#
# Пример: profile
#   - Валидный класс: profile — объект -> тест test_eq_profile_valid
#   - Невалидный класс: profile = None -> тест test_eq_profile_invalid
#
# Пример: совместимость с детьми
#   - Несовместимый класс: for_children=False И has_children=True -> test_eq_children_forbidden_but_user_has
#
# Пример: совместимость с питомцами
#   - Несовместимый класс: with_other_animals=False И has_other_animals=True -> test_eq_pets_forbidden_but_user_has
#
# =============================================================================

def test_eq_profile_valid():
    """
    EP: Профиль существует и все требования выполнены – разрешено.

    Класс: profile is not None, все проверки пройдены.
    Представитель: profile имеет корректные значения, животное требует частный дом,
                   у пользователя он есть.
    Ожидаем: success=True.
    """
    animal = Mock()
    animal.is_available = True
    animal.requires_house = True
    animal.min_rooms = 1
    animal.for_children = True
    animal.with_other_animals = True

    profile = Mock()
    profile.housing_type = 'house'
    profile.rooms_count = 2
    profile.has_children = False
    profile.has_other_animals = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is True


def test_eq_profile_invalid():
    """
    EP: Профиль отсутствует – отказ (аналогично RULE 3).

    Класс: profile is None.
    Представитель: profile=None.
    Ожидаем: success=False, ошибка об анкете.
    """
    animal = Mock()
    animal.is_available = True

    profile = None

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is False
    assert 'анкету' in errors[0].lower()


def test_eq_children_forbidden_but_user_has():
    """
    EP: Несовместимый класс – животное не для детей, у пользователя есть дети.

    Класс: for_children=False И has_children=True.
    Представитель: animal.for_children=False, profile.has_children=True.
    Ожидаем: success=False, ошибка о детях/семьях.
    """
    animal = Mock()
    animal.is_available = True
    animal.for_children = False
    animal.requires_house = False
    animal.min_rooms = 1
    animal.with_other_animals = True

    profile = Mock()
    profile.has_children = True
    profile.housing_type = 'apartment'
    profile.rooms_count = 2
    profile.has_other_animals = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is False
    assert any(keyword in errors[0].lower() for keyword in ['дет', 'семей'])


def test_eq_pets_forbidden_but_user_has():
    """
    EP: Несовместимый класс – животное не с другими, у пользователя есть питомцы.

    Класс: with_other_animals=False И has_other_animals=True.
    Представитель: animal.with_other_animals=False, profile.has_other_animals=True.
    Ожидаем: success=False, ошибка о других животных.
    """
    animal = Mock()
    animal.is_available = True
    animal.with_other_animals = False
    animal.requires_house = False
    animal.min_rooms = 1
    animal.for_children = True

    profile = Mock()
    profile.has_other_animals = True
    profile.housing_type = 'apartment'
    profile.rooms_count = 2
    profile.has_children = False

    success, errors = validate_queue_eligibility(
        animal=animal,
        profile=profile,
        active_count=0,
        existing_entry=None,
    )
    assert success is False
    assert 'другими животными' in errors[0].lower()