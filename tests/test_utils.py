import pytest
from enhanced_lib.calculations.utils import group_into_pairs_with_sum_less_than


def test_empty_list():
    arr = []
    target_sum = 10.0
    key = "quantity"
    result = group_into_pairs_with_sum_less_than(arr, target_sum, key)
    assert result == [[]]


def test_single_element():
    arr = [{"quantity": 5.0}]
    target_sum = 10.0
    key = "quantity"
    result = group_into_pairs_with_sum_less_than(arr, target_sum, key)
    assert result == [[{"quantity": 5.0}]]


def test_multiple_elements_with_sum_less_than_target():
    arr = [{"quantity": 3.0}, {"quantity": 4.0}]
    target_sum = 10.0
    key = "quantity"
    result = group_into_pairs_with_sum_less_than(arr, target_sum, key)
    assert result == [[{"quantity": 3.0}, {"quantity": 4.0}]]


def test_multiple_elements_with_sum_greater_than_target():
    arr = [{"quantity": 6.0}, {"quantity": 5.0}]
    target_sum = 10.0
    key = "quantity"
    result = group_into_pairs_with_sum_less_than(arr, target_sum, key)
    assert result == [[{"quantity": 6.0}, {"quantity": 5.0}]]


def test_mixed_elements():
    arr = [{"quantity": 3.0}, {"quantity": 7.0}, {"quantity": 2.0}, {"quantity": 5.0}]
    target_sum = 10.0
    key = "quantity"
    result = group_into_pairs_with_sum_less_than(arr, target_sum, key)
    assert result == [
        [{"quantity": 3.0}, {"quantity": 7.0}],
    ]
