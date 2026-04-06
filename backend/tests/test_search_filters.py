"""
=============================================================================
PAIRWISE-ТЕСТИРОВАНИЕ: фильтры поиска животных
=============================================================================

Техника: AllPairs (pairwise) — покрытие всех пар значений параметров фильтров
при минимальном числе тестов.

Эндпоинт: GET /animals/
Параметры: search, species_id, gender_id, min_age, max_age, color_id

Подробнее: tests/PAIRWISE.md

ЗАПУСК: pytest tests/test_search_filters.py -v
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from allpairspy import AllPairs


def _build_query_string(search, species_id, gender_id, min_age, max_age, color_ids):
    """Собирает query_string для GET /animals/ из параметров pairwise."""
    from urllib.parse import urlencode
    params = []
    if search:
        params.append(("search", search))
    if species_id is not None:
        params.append(("species_id", species_id))
    if gender_id is not None:
        params.append(("gender_id", gender_id))
    if min_age is not None:
        params.append(("min_age", min_age))
    if max_age is not None:
        params.append(("max_age", max_age))
    for c in color_ids:
        params.append(("color_id", c))
    return urlencode(params) if params else None


def _collect_pairwise_combinations():
    """Генерирует pairwise-комбинации для фильтров."""
    parameters = [
        ["", "Мурзик"],      # search: пустой / непустой
        [None, 1],           # species_id: не задан / задан
        [None, 1],           # gender_id: не задан / задан
        [None, 0, 5],        # min_age: не задан / 0 / >0
        [None, 10],          # max_age: не задан / задан
        [[], [1], [1, 2]],   # color_id: [] / [1] / [1,2]
    ]
    combos = []
    for i, combo in enumerate(AllPairs(parameters)):
        search, species_id, gender_id, min_age, max_age, color_ids = combo
        qs = _build_query_string(search, species_id, gender_id, min_age, max_age, color_ids)
        combos.append((qs, combo))
    return combos


# Собираем комбинации один раз при загрузке модуля
_PAIRWISE_COMBOS = _collect_pairwise_combinations()


@pytest.mark.parametrize("query_string,combo", _PAIRWISE_COMBOS,
                         ids=[f"pairwise_{i}" for i in range(len(_PAIRWISE_COMBOS))])
def test_search_filters_pairwise(client, query_string, combo):
    """
    Проверяет: GET /animals/ (list_animals) | Техника: pairwise (AllPairs)

    Pairwise: каждая комбинация фильтров должна возвращать 200.

    combo = (search, species_id, gender_id, min_age, max_age, color_ids)
    """
    url = "/animals/"
    if query_string:
        url = f"{url}?{query_string}"
    response = client.get(url)
    assert response.status_code == 200, (
        f"Pairwise combo {combo} -> GET {url} вернул {response.status_code}"
    )
