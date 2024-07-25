use chrono::{offset::Local, DateTime};
use std::collections::HashMap;

pub fn get_current_time() -> String {
    let now: DateTime<Local> = Local::now();
    now.timestamp().to_string()
}

pub fn to_f(value: f64, places: &str) -> f64 {
    let decimal_places = places
        .trim_start_matches("%.")
        .trim_end_matches('f')
        .parse::<usize>()
        .unwrap();
    let formatted_value = format!("{:.1$}", value, decimal_places);
    formatted_value.parse().unwrap_or(value)
}

pub fn determine_pnl(entry: f64, close_price: f64, quantity: f64, kind: &str) -> f64 {
    let difference = if kind == "long" {
        close_price - entry
    } else {
        entry - close_price
    };
    difference * quantity
}

pub fn determine_new_amount_to_sell(
    entry: f64,
    quantity: f64,
    sell_price: f64,
    expected_profit: f64,
    kind: &str,
    places: &str,
) -> f64 {
    let expected_loss = determine_pnl(entry, sell_price, quantity.abs(), kind);
    let ratio = to_f(expected_profit / expected_loss.abs(), "%.2");
    let new_quantity = quantity.abs() * ratio;
    to_f(new_quantity, places)
}

pub fn determine_amount_to_sell(
    entry: f64,
    quantity: f64,
    sell_price: f64,
    pnl: f64,
    places: &str,
    kind: Option<&str>,
) -> f64 {
    let kind = kind.unwrap_or(if sell_price > entry { "short" } else { "long" });
    determine_new_amount_to_sell(entry, quantity, sell_price, pnl, kind, places)
}

pub fn determine_stop_and_size(entry: f64, pnl: f64, take_profit: f64, kind: &str) -> f64 {
    let difference = if kind == "long" {
        take_profit - entry
    } else {
        entry - take_profit
    };
    (pnl / difference).abs()
}

pub fn determine_close_price(
    entry: f64,
    pnl: f64,
    quantity: f64,
    leverage: u32,
    kind: &str,
) -> f64 {
    let dollar_value = entry / leverage as f64;
    let position = dollar_value * quantity;
    if position != 0.0 {
        let percent = pnl / position;
        let difference = (position * percent) / quantity;
        if kind == "long" {
            entry + difference
        } else {
            entry - difference
        }
    } else {
        0.0
    }
}

#[derive(Debug)]
pub struct PositionSizeParams {
    pub entry: f64,
    pub stop: Option<f64>,
    pub budget: f64,
    pub percent: Option<f64>,
    pub min_size: Option<u32>,
    pub as_coin: bool,
    pub places: String,
}

impl Default for PositionSizeParams {
    fn default() -> Self {
        Self {
            entry: 0.0,
            stop: None,
            budget: 0.0,
            percent: None,
            min_size: None,
            as_coin: true,
            places: "%.3f".to_string(),
        }
    }
}

pub fn determine_position_size(params: &PositionSizeParams) -> Option<f64> {
    let PositionSizeParams {
        entry,
        stop,
        budget,
        percent,
        min_size,
        as_coin,
        places,
    } = params;

    let stop_percent = if let Some(stop_value) = stop {
        Some((entry - stop_value).abs() / entry)
    } else {
        *percent
    };

    if let Some(stop_percent) = stop_percent {
        let mut size = budget / stop_percent;
        if *as_coin {
            size = size / entry;
            if let Some(1) = min_size {
                return Some(to_f(size.ceil(), places));
            }
        }
        return Some(to_f(size, places));
    }
    None
}

pub fn determine_avg(
    orders: Vec<HashMap<String, f64>>,
    places: &str,
    price_places: &str,
) -> HashMap<String, f64> {
    let sum_values: f64 = orders.iter().map(|x| x["price"] * x["quantity"]).sum();
    let total_quantity: f64 = orders.iter().map(|x| x["quantity"]).sum();
    let avg_value = if total_quantity != 0.0 {
        to_f(sum_values / total_quantity, price_places)
    } else {
        0.0
    };
    let mut result = HashMap::new();
    result.insert("price".to_string(), avg_value);
    result.insert("quantity".to_string(), to_f(total_quantity, places));
    result
}

pub fn group_into_pairs_with_sum_less_than(
    arr: &[HashMap<String, f64>],
    target_sum: f64,
    key: &str,
) -> Vec<Vec<HashMap<String, f64>>> {
    let mut result: Vec<Vec<HashMap<String, f64>>> = Vec::new();
    let mut current_sum = 0.0;
    let mut current_group: Vec<HashMap<String, f64>> = Vec::new();

    for item in arr {
        current_group.push(item.clone());
        current_sum += item.get(key).unwrap_or(&0.0);
        if current_sum >= target_sum {
            result.push(current_group.clone());
            current_group.clear();
            current_sum = 0.0;
        }
    }

    if !current_group.is_empty() {
        result.push(current_group);
    }

    if result.is_empty() {
        vec![vec![]]
    } else {
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn test_get_current_time() {
        let timestamp = get_current_time();
        assert!(timestamp.parse::<f64>().is_ok());
    }

    #[test]
    fn test_to_f() {
        assert_eq!(to_f(123.456789, "%.2f"), 123.46);
        assert_eq!(to_f(123.456789, "%.1f"), 123.5);
    }

    #[test]
    fn test_determine_pnl() {
        assert_eq!(determine_pnl(100.0, 110.0, 10.0, "long"), 100.0);
        assert_eq!(determine_pnl(100.0, 90.0, 10.0, "short"), 100.0);
    }

    #[test]
    fn test_determine_new_amount_to_sell() {
        assert_eq!(
            determine_new_amount_to_sell(100.0, 10.0, 110.0, 100.0, "long", "%.2f"),
            10.0
        );
        assert_eq!(
            determine_new_amount_to_sell(100.0, 10.0, 90.0, 100.0, "short", "%.2f"),
            10.0
        );
    }

    #[test]
    fn test_determine_amount_to_sell() {
        assert_eq!(
            determine_amount_to_sell(100.0, 10.0, 110.0, 100.0, "%.2f", None),
            10.0
        );
        assert_eq!(
            determine_amount_to_sell(100.0, 10.0, 90.0, 100.0, "%.2f", Some("short")),
            10.0
        );
    }

    #[test]
    fn test_determine_stop_and_size() {
        assert_eq!(determine_stop_and_size(100.0, 100.0, 110.0, "long"), 10.0);
        assert_eq!(determine_stop_and_size(100.0, 100.0, 90.0, "short"), 10.0);
    }

    #[test]
    fn test_determine_close_price() {
        assert_eq!(determine_close_price(100.0, 100.0, 10.0, 1, "long"), 110.0);
        assert_eq!(determine_close_price(100.0, 100.0, 10.0, 1, "short"), 90.0);
    }

    #[test]
    fn test_determine_position_size() {
        let mut params = PositionSizeParams {
            entry: 100.0,
            stop: Some(90.0),
            budget: 1000.0,
            places: "%.2f".to_string(),
            ..Default::default()
        };
        assert_eq!(determine_position_size(&params), Some(100.0));
        params = PositionSizeParams {
            entry: 100.0,
            budget: 1000.0,
            percent: Some(0.1),
            places: "%.2f".to_string(),
            ..Default::default()
        };
        assert_eq!(determine_position_size(&params), Some(100.0));
        params = PositionSizeParams {
            entry: 62500.0,
            stop: Some(62000.0),
            budget: 20.0,
            percent: Some(0.1),
            places: "%.2f".to_string(),
            ..Default::default()
        };
        assert_eq!(determine_position_size(&params), Some(0.04));
    }

    #[test]
    fn test_determine_avg() {
        let mut order1 = HashMap::new();
        order1.insert("price".to_string(), 100.0);
        order1.insert("quantity".to_string(), 1.0);

        let mut order2 = HashMap::new();
        order2.insert("price".to_string(), 200.0);
        order2.insert("quantity".to_string(), 2.0);

        let orders = vec![order1, order2];
        let avg = determine_avg(orders, "%.2f", "%.2f");

        assert_eq!(avg["price"], 166.67);
        assert_eq!(avg["quantity"], 3.0);
    }

    #[test]
    fn test_empty_list() {
        let arr: Vec<HashMap<String, f64>> = vec![];
        let target_sum = 10.0;
        let key = "quantity";
        let result = group_into_pairs_with_sum_less_than(&arr, target_sum, key);
        assert_eq!(result, vec![vec![]]);
    }

    #[test]
    fn test_single_element() {
        let mut item = HashMap::new();
        item.insert("quantity".to_string(), 5.0);
        let arr = vec![item];
        let target_sum = 10.0;
        let key = "quantity";
        let result = group_into_pairs_with_sum_less_than(&arr, target_sum, key);
        assert_eq!(result, vec![vec![arr[0].clone()]]);
    }

    #[test]
    fn test_multiple_elements_with_sum_less_than_target() {
        let mut item1 = HashMap::new();
        item1.insert("quantity".to_string(), 3.0);
        let mut item2 = HashMap::new();
        item2.insert("quantity".to_string(), 4.0);
        let arr = vec![item1.clone(), item2.clone()];
        let target_sum = 10.0;
        let key = "quantity";
        let result = group_into_pairs_with_sum_less_than(&arr, target_sum, key);
        assert_eq!(result, vec![vec![item1, item2]]);
    }

    #[test]
    fn test_multiple_elements_with_sum_greater_than_target() {
        let mut item1 = HashMap::new();
        item1.insert("quantity".to_string(), 6.0);
        let mut item2 = HashMap::new();
        item2.insert("quantity".to_string(), 5.0);
        let arr = vec![item1.clone(), item2.clone()];
        let target_sum = 10.0;
        let key = "quantity";
        let result = group_into_pairs_with_sum_less_than(&arr, target_sum, key);
        assert_eq!(result, vec![vec![item1, item2]]);
    }

    #[test]
    fn test_mixed_elements() {
        let mut item1 = HashMap::new();
        item1.insert("quantity".to_string(), 3.0);
        let mut item2 = HashMap::new();
        item2.insert("quantity".to_string(), 7.0);
        let mut item3 = HashMap::new();
        item3.insert("quantity".to_string(), 2.0);
        let mut item4 = HashMap::new();
        item4.insert("quantity".to_string(), 5.0);
        let arr = vec![item1.clone(), item2.clone(), item3.clone(), item4.clone()];
        let target_sum = 10.0;
        let key = "quantity";
        let result = group_into_pairs_with_sum_less_than(&arr, target_sum, key);
        assert_eq!(result, vec![vec![item1, item2], vec![item3, item4]]);
    }
}