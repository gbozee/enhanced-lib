import pytest
from enhanced_lib.calculations.utils import (
    group_into_pairs_with_sum_less_than,
    fibonacci_analysis,determine_fib_support,extend_fibonacci
)


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


def test_fibonacci_analysis():
    support = 100.0
    resistance = 200.0
    kind = "long"
    trend = "long"
    places = "%.1f"
    result = fibonacci_analysis(support, resistance, kind, trend, places)
    expected = [100.0, 123.6, 138.2, 150.0, 161.8, 178.9, 200.0, 227.2, 241.4, 261.8]
    assert result == expected

    kind = "short"
    result = fibonacci_analysis(support, resistance, kind, trend, places)
    expected = [261.8, 241.4, 227.2, 200.0, 178.9, 161.8, 150.0, 138.2, 123.6, 100.0]
    assert result == expected


def test_determine_fib_support():
    value_with_fibs = [
        {"fib": 0.236, "value": 123.6},
        {"fib": 0.382, "value": 138.2},
    ]
    places = "%.1f"
    result = determine_fib_support(value_with_fibs, places)
    expected = {
        "support": 100.0,  # Replace with the expected support value
        "resistance": 200.0,  # Replace with the expected resistance value
    }
    assert result == expected

    value_with_fibs = [
        {"fib": 0.5, "value": 150.0},
        {"fib": 0.618, "value": 161.8},
    ]
    result = determine_fib_support(value_with_fibs, places)
    expected = {
        "support": 100.0,  # Replace with the expected support value
        "resistance": 200.0,  # Replace with the expected resistance value
    }
    assert result == expected


def test_extend_fibonacci():
    support = 50000.0
    resistance = 60000.0
    focus = 52300.0
    kind = "long"
    trend = "long"
    places = "%.1f"
    high = 1.0
    low = 0.0

    result = extend_fibonacci(
        support, resistance, focus, kind, trend, places, high, low
    )
    expected_support = 50000.0  # Replace with the expected support value
    expected_resistance = 52360.0  # Replace with the expected resistance value
    assert result["support"] == expected_support
    assert result["resistance"] == expected_resistance
    
    
