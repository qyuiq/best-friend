"""
Сервис проверки возможности встать в очередь на усыновление.
Содержит бизнес-логику, тестируемую с mock-объектами без обращения к БД.
"""


def validate_queue_eligibility(animal, profile, active_count, existing_entry, max_active=3):
    """
    Проверяет, может ли пользователь встать в очередь на животное.

    Args:
        animal: объект с атрибутами is_available, requires_house, min_rooms,
                for_children, with_other_animals
        profile: объект с housing_type, rooms_count, has_children, has_other_animals (или None)
        active_count: количество активных заявок пользователя
        existing_entry: запись в очереди на это животное (или None)
        max_active: максимальное число активных заявок

    Returns:
        tuple: (success: bool, errors: list[str])
    """
    errors = []

    if not animal.is_available:
        errors.append('Это животное уже не доступно для усыновления')
        return False, errors

    if profile is None:
        errors.append('Сначала заполните анкету в личном кабинете')
        return False, errors

    if existing_entry is not None:
        errors.append('Вы уже в очереди на это животное')
        return False, errors

    if active_count >= max_active:
        errors.append(f'Вы не можете иметь более {max_active} активных заявок одновременно')
        return False, errors

    if animal.requires_house and profile.housing_type != 'house':
        errors.append('Для этого животного требуется частный дом')

    if profile.rooms_count < animal.min_rooms:
        errors.append(f'Для этого животного требуется не менее {animal.min_rooms} комнат(ы)')

    if not animal.for_children and profile.has_children:
        errors.append('Это животное не подходит для семей с детьми')

    if not animal.with_other_animals and profile.has_other_animals:
        errors.append('Это животное не уживается с другими животными')

    return len(errors) == 0, errors
