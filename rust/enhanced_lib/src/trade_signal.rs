use std::{
    cmp::Ordering,
    collections::{HashMap, HashSet},
};

use ordered_float::OrderedFloat;

// Import the utils module
use crate::utils::{
    determine_avg, determine_close_price, determine_pnl, determine_position_size, to_f,
    PositionSizeParams, group_into_pairs_with_sum_less_than,
};

// Define the TradeInstanceType struct
#[derive(Debug, Clone)]
pub struct TradeInstanceType {
    entry: f64,
    risk: f64,
    quantity: f64,
    sell_price: f64,
    incurred_sell: f64,
    stop: f64,
    pnl: f64,
    fee: f64,
    net: f64,
    incurred: f64,
    stop_percent: f64,
    rr: i32,
}

fn _get_zone_nogen(current_price: f64, focus: f64, percent_change: f64, places: &str) -> Vec<f64> {
    let mut result = Vec::new();
    let mut last = focus;
    let mut focus_high = last * (1.0 + percent_change);
    let mut focus_low = last * (1.0 + percent_change).powf(-1.0);

    if focus_high > current_price {
        while focus_high > current_price {
            if last < 1.0 {
                // to resolve for tother symbols
                break;
            }
            if focus_high == last {
                break;
            }
            result.push(to_f(last, places));
            focus_high = last;
            last = focus_high * (1.0 + percent_change).powf(-1.0);
            focus_low = last * (1.0 + percent_change);
        }
    } else {
        if focus_high <= current_price {
            while focus_high <= current_price {
                result.push(to_f(focus_high, places));
                focus_low = focus_high;
                last = focus_low * (1.0 + percent_change);
                focus_high = last * (1.0 + percent_change);
            }
        } else {
            while focus_low <= current_price {
                result.push(to_f(focus_high, places));
                focus_low = focus_high;
                last = focus_low * (1.0 + percent_change);
                focus_high = last * (1.0 + percent_change);
            }
        }
    }

    result
}

fn _get_range(_range: (f64, f64), divisor: i32, places: &str) -> Vec<f64> {
    let difference = _range.1 - _range.0;
    let factor = if divisor == 0 {
        0.0
    } else {
        difference / (divisor as f64)
    };

    let mut result: Vec<f64> = (0..divisor)
        .map(|x| {
            let val = _range.0 + (factor * (x as f64));
            to_f(val, places)
        })
        .collect();

    result.push(_range.1);
    result
}

fn _get_trade_zone(
    current_price: f64,
    array: (f64, f64),
    risk: i32,
    places: &str,
) -> Option<(f64, f64)> {
    let zones = _get_range(array, risk, places);
    let considered: Vec<usize> = zones
        .iter()
        .enumerate()
        .filter(|(_, x)| **x > current_price)
        .map(|(i, _)| i)
        .collect();

    if !considered.is_empty() && considered[0] > 0 {
        let start = considered[0] - 1;
        let end = considered[0];
        let ranges = (&zones[start..=end]).to_vec();
        Some((ranges[0], ranges[1]))
    } else {
        None
    }
}

// Define the Signal struct
#[derive(Debug, Clone, PartialEq)]
pub struct Signal {
    pub focus: f64,
    pub budget: f64,
    pub percent_change: f64,
    pub price_places: String,
    pub decimal_places: String,
    pub zone_risk: u32,
    pub fee: f64,
    pub support: f64,
    pub risk_reward: u32,
    pub resistance: f64,
    pub take_profit: Option<f64>,
    pub risk_per_trade: f64,
    pub increase_size: bool,
    pub additional_increase: f64,
    pub minimum_pnl: f64,
    pub split: Option<i32>,
    pub max_size: Option<f64>,
    pub trade_size: Option<f64>,
    pub increase_position: bool,
    pub default: bool,
    pub minimum_size: f64,
}
impl Default for Signal {
    fn default() -> Self {
        Self {
            focus: 0.0,
            budget: 0.0,
            percent_change: 0.02,
            price_places: "%.5f".to_string(),
            decimal_places: "%.0f".to_string(),
            zone_risk: 1,
            fee: 0.08 / 100.0,
            support: 0.0,
            risk_reward: 4,
            resistance: 0.0,
            take_profit: None,
            risk_per_trade: 0.0,
            increase_size: false,
            additional_increase: 0.0,
            minimum_pnl: 0.0,
            split: None,
            max_size: None,
            trade_size: None,
            increase_position: false,
            default: false,
            minimum_size: 0.0,
        }
    }
}

impl Signal {
    // Implement other methods here...
    pub fn risk(&self) -> f64 {
        self.budget * self.percent_change
    }

    pub fn min_trades(&self) -> i32 {
        self.risk().trunc() as i32
    }

    pub fn min_price(&self) -> f64 {
        let number = self.price_places.replace("%.", "").replace("f", "");
        let precision = number.parse::<i32>().unwrap_or(5);
        10.0_f64.powi(-precision)
    }

    pub fn get_range(&self, current_price: f64, kind: &str) -> Vec<f64> {
        let mut zones = Vec::new();
        let risk = self.risk().trunc() as i32;
        if let Some(future_range) = self.get_future_range(current_price) {
            zones = _get_range(future_range, risk, &self.price_places);
            if kind == "short" {
                if let Some(second_future_range) =
                    self.get_future_range(future_range.0 - self.min_price())
                {
                    let secondary_zones = _get_range(second_future_range, risk, &self.price_places);
                    zones.extend(secondary_zones);
                    if let Some(third_future_range) =
                        self.get_future_range(future_range.1 + self.min_price())
                    {
                        let third_zones = _get_range(third_future_range, risk, &self.price_places);
                        zones.extend(third_zones);
                        zones.sort_by(|a, b| a.partial_cmp(b).unwrap());
                    }
                }
            }
        }
        zones
    }

    pub fn get_future_range(&self, current_price: f64) -> Option<(f64, f64)> {
        if let Some(margin_range) = self.get_margin_range(current_price) {
            if let Some(future_zone) = _get_trade_zone(
                current_price,
                margin_range,
                self.risk().trunc() as i32,
                &self.price_places,
            ) {
                let (zone_start, zone_end) = (self.to_f(future_zone.0), self.to_f(future_zone.1));
                Some((zone_start, zone_end))
            } else {
                None
            }
        } else {
            None
        }
    }

    pub fn get_margin_range(&self, current_price: f64) -> Option<((f64, f64))> {
        let top_zones = _get_zone_nogen(
            current_price - self.min_price(),
            self.focus,
            self.percent_change,
            &self.price_places,
        );

        if !top_zones.is_empty() {
            let result = top_zones[top_zones.len() - 1];
            let range_start = self.to_f(result);
            let range_end = self.to_f(result * (1.0 + self.percent_change));
            Some((range_start, range_end))
        } else {
            None
        }
    }

    pub fn to_f(&self, value: f64) -> f64 {
        to_f(value, &self.price_places)
    }

    pub fn to_df(&self, current_price: f64, places: &str) -> f64 {
        to_f(current_price, places)
    }

    pub fn get_trade_range(&self, current_price: f64, kind: &str) -> Option<(f64, f64)> {
        let future_range = self.get_future_range(current_price);
        if let Some(future_range) = future_range {
            let second_future_range = self.get_future_range(future_range.0 - self.min_price());
            let third_future_range = self.get_future_range(future_range.1 + self.min_price());
            if let Some(second_future_range) = second_future_range {
                let zones = self.get_range(current_price, kind);

                if kind == "short" {
                    let high_zone = zones[zones.len() - 1];
                    if let Some(_) = third_future_range {
                        return Some((zones[3], high_zone));
                    }
                }
                if zones.len() > 2 {
                    let high_zone = zones[1];
                    return Some((second_future_range.0, high_zone));
                }
            }
        }
        None
    }

    pub fn get_trade_zones(
        &self,
        current_price: f64,
        upper_bound: Option<f64>,
        minimum: Option<usize>,
        kind: &str,
    ) -> Option<Vec<f64>> {
        let mut trade_zones = self.get_range(current_price, kind);

        if let (Some(upper_bound), Some(minimum)) = (upper_bound, minimum) {
            if !trade_zones.is_empty() {
                let condition: Box<dyn Fn(f64) -> bool> = if kind == "short" {
                    Box::new(|_| true)
                } else {
                    Box::new(move |x| x <= upper_bound)
                };
                trade_zones.retain(|&x| condition(x));

                if !trade_zones.is_empty() && trade_zones.len() < minimum {
                    if let Some(new_set) =
                        self.get_trade_zones(trade_zones[0] - self.min_price(), None, None, kind)
                    {
                        let mut combined_set: HashSet<OrderedFloat<f64>> =
                            trade_zones.into_iter().map(OrderedFloat).collect();
                        combined_set.extend(new_set.into_iter().map(OrderedFloat));
                        let mut combined_vec: Vec<f64> =
                            combined_set.into_iter().map(|x| x.into_inner()).collect();
                        combined_vec.sort_by(|a, b| a.partial_cmp(b).unwrap());
                        trade_zones = combined_vec;
                    }
                }
            }
        }
        Some(trade_zones)
    }

    pub fn get_margin_zones(&self, current_price: f64, kind: &str) -> Vec<(f64, f64)> {
        let mut result = Vec::new();
        let mut start = current_price;
        let mut counter = 0;

        if self.support > 0.0 && kind == "long" {
            while start > self.support {
                if let Some(v) = self.get_margin_range(start) {
                    result.push(v);
                    start = v.0 - self.min_price();
                    counter += 1;
                    if counter > 20 {
                        break;
                    }
                }
            }
            return result;
        }
        if self.resistance > 0.0 {
            while start < self.resistance {
                if let Some(v) = self.get_margin_range(start) {
                    result.push(v);
                    start = v.1 + self.min_price();
                    counter += 1;
                    if counter > 20 {
                        break;
                    }
                }
            }
            return result;
        }

        if let Some(v) = self.get_margin_range(current_price) {
            result.push(v);
        }
        // result.push(self.get_margin_range(current_price));
        result
    }

    fn get_future_range_new(&self, current_price: f64, kind: &str) -> Vec<f64> {
        let mut entries = Vec::new();
        let current_price_f = to_f(current_price, &self.price_places);
        if let Some(margin_range) = self.get_margin_range(current_price_f) {
            if margin_range.1 < self.support {
                return entries;
            }
            let percent_change = self.percent_change / self.risk_reward as f64;
            let difference = (margin_range.0 - margin_range.1).abs();
            let spread = self.to_f(difference / self.risk_reward as f64);
            entries = (0..=self.risk_reward as usize)
                .map(|x| to_f(margin_range.1 - spread * x as f64, &self.price_places))
                .collect();
            if kind == "short" {
                entries = (0..=self.risk_reward as usize)
                    .map(|x| {
                        to_f(
                            margin_range.1 * (1.0 + percent_change).powi(x as i32),
                            &self.price_places,
                        )
                    })
                    .collect();
            }
            if let (Some(&min_entry), Some(&max_entry)) = (
                entries.iter().min_by(|a, b| a.partial_cmp(b).unwrap()),
                entries.iter().max_by(|a, b| a.partial_cmp(b).unwrap()),
            ) {
                if min_entry < current_price_f && current_price_f < max_entry {
                    entries.sort_by(|a, b| a.partial_cmp(b).unwrap());
                    return entries;
                }
            }
            let margin_zones = self.get_margin_zones(current_price_f, "long");
            let remaining_zones: Vec<(f64, f64)> = margin_zones
                .into_iter()
                .filter(|&x| x != margin_range)
                .collect();
            if !remaining_zones.is_empty() {
                if let Some(new_range) = remaining_zones.first().map(|&x| x.1) {
                    entries.clear();
                    let mut x = 0;
                    let new_range = to_f(new_range, &self.price_places);
                    while entries.len() < self.risk_reward as usize + 1 {
                        if kind == "long" {
                            let value = to_f(new_range - spread * x as f64, &self.price_places);
                            if value <= current_price_f {
                                entries.push(value);
                            }
                        } else {
                            let value = to_f(
                                new_range * (1.0 + percent_change).powi(x),
                                &self.price_places,
                            );
                            if value >= current_price_f {
                                entries.push(value);
                            }
                        }
                        x += 1;
                    }
                }
            }
            if remaining_zones.is_empty()
                && to_f(current_price, &self.price_places)
                    <= *entries
                        .iter()
                        .min_by(|a, b| a.partial_cmp(b).unwrap())
                        .unwrap()
            {
                let next_focus = margin_range.0 * (1.0 + self.percent_change).powi(-1);
                let mut entries = Vec::new();
                let mut x = 0;
                while entries.len() < self.risk_reward as usize + 1 {
                    let value = if kind == "long" {
                        to_f(next_focus - spread * x as f64, &self.price_places)
                    } else {
                        to_f(
                            next_focus * (1.0 + percent_change).powi(x),
                            &self.price_places,
                        )
                    };
                    if (kind == "long" && value <= to_f(current_price, &self.price_places))
                        || (kind != "long" && value >= to_f(current_price, &self.price_places))
                    {
                        entries.push(value);
                    }
                    x += 1;
                }
                entries.sort_by(|a, b| a.partial_cmp(b).unwrap());
                return entries;
            }
            entries.sort_by(|a, b| a.partial_cmp(b).unwrap());
        }
        entries
    }
    pub fn get_future_zones(&self, current_price: f64, kind: &str) -> Vec<f64> {
        self.get_future_range_new(current_price, kind)
    }

    fn build_trade_dict(
        &self,
        entry: f64,
        stop: f64,
        mut risk: f64,
        arr: &[f64],
        index: usize,
        new_fees: f64,
        kind: &str,
        take_profit: Option<f64>,
        start: usize,
    ) -> Option<HashMap<String, f64>> {
        let considered: Vec<usize> = arr
            .iter()
            .enumerate()
            .filter_map(|(i, &x)| if i > index { Some(i) } else { None })
            .collect();
        let mut with_quantity: Vec<HashMap<String, f64>> = Vec::new();
        for &x in &considered {
            if let Some(q) = determine_position_size(&PositionSizeParams {
                entry: arr[x],
                stop: Some(arr[x - 1]),
                budget: risk,
                places: self.decimal_places.clone(),
                ..Default::default()
            }) {
                let mut map = HashMap::new();
                map.insert("quantity".to_string(), q);
                map.insert("entry".to_string(), arr[x]);
                with_quantity.push(map);
            }
        }
        if self.increase_size {
            let arr_length = with_quantity.len();
            with_quantity = with_quantity
                .into_iter()
                .enumerate()
                .map(|(i, mut x)| {
                    x.insert(
                        "quantity".to_string(),
                        x["quantity"] * (arr_length - i) as f64,
                    );
                    x
                })
                .collect();
        }
        let fees: Vec<f64> = with_quantity
            .iter()
            .map(|x| self.to_df(self.fee * x["quantity"] * x["entry"], &self.decimal_places))
            .collect();
        let previous_risks: Vec<f64> = with_quantity
            .iter()
            .map(|_| self.to_df(risk, &self.decimal_places))
            .collect();
        let multiplier = start as f64 - index as f64;
        let incured_fees = fees.iter().sum::<f64>() + previous_risks.iter().sum::<f64>();
        let lost_risk = fees.len() as f64 * risk;
        let quantity = determine_position_size(&PositionSizeParams {
            entry: entry,
            stop: Some(stop),
            budget: risk,
            places: self.decimal_places.clone(),
            ..Default::default()
        })?;
        if self.increase_size {
            let quantity = quantity * multiplier;
            let new_risk = determine_pnl(entry, stop, quantity, kind);
            risk = new_risk.abs();
        }
        let fee = self.to_df(self.fee * quantity * entry, &self.decimal_places);
        let increment = (arr.len() - (index + 1)) as f64;
        let pnl = self.to_df(risk, &self.decimal_places) * (self.risk_reward as f64 + increment);
        let pnl = if self.minimum_pnl > 0.0 {
            self.minimum_pnl + fee
        } else {
            pnl
        };
        let sell_price = determine_close_price(entry, pnl, quantity, 1, kind);
        let (pnl, sell_price) = if let Some(take_profit) = take_profit {
            let pnl = determine_pnl(entry, take_profit, quantity, kind) + fee;
            (pnl, determine_close_price(entry, pnl, quantity, 1, kind))
        } else {
            (pnl, sell_price)
        };
        let risk_sell = sell_price;
        let incurred = self.to_df(incured_fees + new_fees, &self.decimal_places);
        let incurred_sell = if incurred > 0.0 {
            determine_close_price(entry, incurred, quantity, 1, kind)
        } else {
            sell_price
        };
        let mut map = HashMap::new();
        map.insert("entry".to_string(), entry);
        map.insert("risk".to_string(), self.to_df(risk, &self.decimal_places));
        map.insert("quantity".to_string(), quantity);
        map.insert("sell_price".to_string(), self.to_f(sell_price));
        map.insert("incurred_sell".to_string(), self.to_f(incurred_sell));
        map.insert("stop".to_string(), stop);
        map.insert("pnl".to_string(), pnl);
        map.insert("fee".to_string(), fee);
        map.insert(
            "net".to_string(),
            self.to_df(pnl - fee, &self.decimal_places),
        );
        map.insert("incurred".to_string(), incurred);
        map.insert(
            "stop_percent".to_string(),
            self.to_df((entry - stop).abs() / entry, &self.decimal_places),
        );
        map.insert("rr".to_string(), self.risk_reward as f64);
        Some(map)
    }

    fn process_orders(
        &self,
        current_price: f64,
        stop_loss: f64,
        trade_zones: &[f64],
        kind: &str,
    ) -> Vec<HashMap<String, f64>> {
        let number_of_orders = trade_zones.len() - 1;
        let mut take_profit = stop_loss * (1.0 + 2.0 * self.percent_change);
        if kind == "short" {
            take_profit = stop_loss * (1.0 + 2.0 * self.percent_change).powi(-1);
        }
        if let Some(tp) = self.take_profit {
            take_profit = tp;
        }
        if number_of_orders > 0 {
            let risk_per_trade = self.get_risk_per_trade(number_of_orders);
            let allowed_spread = self.percent_change / 100.0;
            let mut limit_orders: Vec<f64> = Vec::new();
            let mut market_orders: Vec<f64> = Vec::new();
            for &x in trade_zones.iter().skip(1) {
                if x <= self.to_f(current_price) {
                    limit_orders.push(x);
                } else {
                    market_orders.push(x);
                }
            }
            if kind == "short" {
                limit_orders.retain(|&x| x >= self.to_f(current_price));
                market_orders.retain(|&x| x < self.to_f(current_price));
            }
            let increase_position = self.support > 0.0 && self.increase_position;
            let mut market_trades: Vec<HashMap<String, f64>> = Vec::new();
            for (i, &x) in market_orders.iter().enumerate() {
                if let Some(y) = self.build_trade_dict(
                    x,
                    if increase_position {
                        self.support
                    } else {
                        if i == 0 {
                            limit_orders.last().copied().unwrap_or(market_orders[i])
                        } else {
                            market_orders[i - 1]
                        }
                    },
                    risk_per_trade,
                    &market_orders,
                    i,
                    kind,
                    market_orders.len() + limit_orders.len(),
                    Some(take_profit),
                ) {
                    market_trades.push(y);
                }
            }
            let total_incurred_market_fees = market_trades
                .first()
                .map_or(0.0, |x| x["incurred"] + x["fee"]);
            let new_stop = if kind == "long" {
                self.support
            } else {
                stop_loss
            };
            let mut limit_trades: Vec<HashMap<String, f64>> = Vec::new();
            for (i, &x) in limit_orders.iter().enumerate() {
                if let Some(y) = self.build_trade_dict(
                    x,
                    if increase_position {
                        new_stop
                    } else {
                        if i == 0 {
                            stop_loss
                        } else {
                            limit_orders[i - 1]
                        }
                    },
                    risk_per_trade,
                    &limit_orders,
                    i,
                    total_incurred_market_fees,
                    kind,
                    market_orders.len() + limit_orders.len(),
                    Some(take_profit),
                ) {
                    limit_trades.push(y);
                }
            }
            let mut total_orders = limit_trades;
            total_orders.extend(market_trades);
            if self.minimum_size > 0.0 {
                let greater_than_min_size: Vec<HashMap<String, f64>> = total_orders
                    .iter()
                    .filter(|&x| x["quantity"] >= self.minimum_size)
                    .cloned()
                    .collect();
                let mut less_than_min_size: Vec<HashMap<String, f64>> = total_orders
                    .iter()
                    .filter(|&x| x["quantity"] < self.minimum_size)
                    .cloned()
                    .collect();
                if less_than_min_size.is_empty() {
                    return greater_than_min_size;
                }
                let pair_size =
                    (self.minimum_size / total_orders.last().unwrap()["quantity"]).ceil() as usize;
                less_than_min_size =
                    group_into_pairs_with_sum_less_than(&less_than_min_size, self.minimum_size); // Group into pairs with sum less than minimum size
                let mut result: Vec<HashMap<String, f64>> = Vec::new();
                for mut x in less_than_min_size {
                    let prices: Vec<f64> = x.iter().map(|y| y["entry"]).collect();
                    let avg =
                        determine_avg(&prices, &self.price_places, &self.decimal_places)
                        let mut map = HashMap::new();
                        map.insert("entry".to_string(), avg["price"]);
                        map.insert("quantity".to_string(), avg["quantity"]);
                        map.insert(
                            "risk".to_string(),
                            to_f(
                                x.iter().map(|y| y["risk"]).sum::<f64>(),
                                &self.decimal_places,
                            ),
                        );
                        let pnl =
                            determine_pnl(avg["price"], x[0]["sell_price"], avg["quantity"], kind);
                        map.insert("pnl".to_string(), to_f(pnl, &self.decimal_places));
                        result.push(map);
                }
                if greater_than_min_size.is_empty() {
                    return result;
                }
                total_orders = greater_than_min_size;
                total_orders.extend(result);
            }
            total_orders
        } else {
            Vec::new()
        }
    }

    fn get_risk_per_trade(&self, number_of_orders: usize) -> f64 {
        if self.risk_per_trade > 0.0 {
            self.risk_per_trade
        } else {
            self.zone_risk as f64 / number_of_orders as f64
        }
    }
}

// Tests for the Signal struct and its methods
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_signal_creation() {
        let mut signal = Signal {
            focus: 67629.3,
            budget: 2000.0,
            percent_change: 0.027906543465628042,
            price_places: "%.1f".to_string(),
            decimal_places: "%.3f".to_string(),
            fee: 0.0006,
            support: Some(65858.0),
            resistance: Some(70495.0),
            take_profit: None,
            risk_per_trade: 1.325,
            risk_reward: 35,
            additional_increase: 0.0,
            split: None,
            minimum_size: 0.004,
            ..Default::default()
        };

        assert_eq!(signal.focus, 67629.3);
        assert_eq!(signal.budget, 2000.0);
        assert_eq!(signal.percent_change, 0.027906543465628042);
        assert_eq!(signal.price_places, "%.1f");
        assert_eq!(signal.decimal_places, "%.3f");
        assert_eq!(signal.zone_risk, 1);
        assert_eq!(signal.fee, 0.0006);
        assert_eq!(signal.support, Some(65858.0));
        assert_eq!(signal.risk_reward, 35);
        assert_eq!(signal.resistance, Some(70495.0));
        assert_eq!(signal.take_profit, None);
        assert_eq!(signal.risk_per_trade, 1.325);
        assert_eq!(signal.increase_size, false);
        assert_eq!(signal.additional_increase, 0.0);
        assert_eq!(signal.minimum_pnl, 0.0);
        assert_eq!(signal.split, None);
        assert_eq!(signal.max_size, None);
        assert_eq!(signal.trade_size, None);
        assert_eq!(signal.increase_position, None);
        assert_eq!(signal.default, false);
        assert_eq!(signal.minimum_size, 0.004);
        assert_eq!(signal.min_trades(), 55);
        assert_eq!(signal.risk(), 55.81308693125608);
        assert_eq!(signal.min_price(), 0.1);

        // get_range tests
        let expected_output = vec![
            100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
            100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
            100.0, 100.0, 100.0, 100.0, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1,
            100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1,
            100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1,
        ];
        let result = signal.get_range(100.0, "long");
        assert_eq!(result, expected_output);
        let expected_output = vec![
            99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9,
            99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9, 99.9,
            100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
            100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
            100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
            100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
            100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.1, 100.1, 100.1, 100.1,
            100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1,
            100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1,
            100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1,
            100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1, 100.1,
            100.1, 100.1, 100.1, 100.1, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2,
            100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2,
            100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2,
        ];
        let result = signal.get_range(100.0, "short");
        assert_eq!(result, expected_output);

        // get_margin_range tests
        let margin_range = signal.get_margin_range(63629.2);
        assert!(margin_range.is_some());
        let (range_start, range_end) = margin_range.unwrap();
        assert_eq!(range_start, 62269.3);
        assert_eq!(range_end, 64007.0);

        // get_future_range tests
        let expected_output = Some((63627.9, 63659.5));
        let result = signal.get_future_range(63629.2);
        assert_eq!(result, expected_output);

        // get_trade_range tests
        let expected_output = Some((67732.2, 67767.2));
        let result = signal.get_trade_range(67800.0, "long");
        assert_eq!(result, expected_output);

        // get_trade_zones test
        let expected_output = Some(vec![
            67766.6, 67767.2, 67767.8, 67768.5, 67769.1, 67769.7, 67770.3, 67771.0, 67771.6,
            67772.2, 67772.8, 67773.5, 67774.1, 67774.7, 67775.3, 67776.0, 67776.6, 67777.2,
            67777.8, 67778.4, 67779.1, 67779.7, 67780.3, 67780.9, 67781.6, 67782.2, 67782.8,
            67783.4, 67784.1, 67784.7, 67785.3, 67785.9, 67786.6, 67787.2, 67787.8, 67788.4,
            67789.1, 67789.7, 67790.3, 67790.9, 67791.5, 67792.2, 67792.8, 67793.4, 67794.0,
            67794.7, 67795.3, 67795.9, 67796.5, 67797.2, 67797.8, 67798.4, 67799.0, 67799.7,
            67800.3, 67800.9,
        ]);
        let result = signal.get_trade_zones(67800.0, None, None, "long");
        assert_eq!(result, expected_output);

        // get_margin_zones test
        let expected_output = vec![(67629.3, 69516.6), (65793.2, 67629.3)];
        let result = signal.get_margin_zones(67800.0, "long");
        assert_eq!(result, expected_output);

        // get_future_zones test
        let expected_output = vec![
            67845.2, 67899.3, 67953.5, 68007.7, 68061.9, 68116.2, 68170.5, 68224.8, 68279.2,
            68333.7, 68388.1, 68442.7, 68497.2, 68551.9, 68606.5, 68661.2, 68716.0, 68770.8,
            68825.6, 68880.5, 68935.4, 68990.3, 69045.4, 69100.4, 69155.5, 69210.6, 69265.8,
            69321.1, 69376.3, 69431.6, 69487.0, 69542.4, 69597.9, 69653.3, 69708.9, 69764.5,
        ];
        let result = signal.get_future_zones(67800.0, "short");
        assert_eq!(result, expected_output);
    }

    // Add more tests for other methods...
    #[test]
    fn test_get_zone_nogen() {
        // Test case 1
        let current_price = 100.0;
        let focus = 95.0;
        let percent_change = 0.02;
        let places = "%.5f";
        let expected_output = vec![96.9];
        let result = _get_zone_nogen(current_price, focus, percent_change, places);
        assert_eq!(result, expected_output);

        // Test case 2
        let current_price = 90.0;
        let focus = 95.0;
        let percent_change = 0.02;
        let places = "%.5f";
        let expected_output = vec![95.0, 93.13725, 91.31103, 89.52062];
        let result = _get_zone_nogen(current_price, focus, percent_change, places);
        assert_eq!(result, expected_output);

        // Test case 3
        let current_price = 105.0;
        let focus = 95.0;
        let percent_change = 0.02;
        let places = "%.5f";
        let expected_output = vec![96.9, 100.81476, 104.88768];
        let result = _get_zone_nogen(current_price, focus, percent_change, places);
        assert_eq!(result, expected_output);
    }

    #[test]
    fn test_get_range() {
        // Test case 1
        let _range = (10.0, 20.0);
        let divisor = 5;
        let places = "%.5f";
        let expected_output = vec![10.00000, 12.00000, 14.00000, 16.00000, 18.00000, 20.00000];
        let result = _get_range(_range, divisor, places);
        assert_eq!(result, expected_output);

        // Test case 2
        let _range = (5.123, 10.456);
        let divisor = 3;
        let places = "%.3f";
        let expected_output = vec![5.123, 6.901, 8.678, 10.456];
        let result = _get_range(_range, divisor, places);
        assert_eq!(result, expected_output);

        // Test case 3
        let _range = (0.0, 1.0);
        let divisor = 0;
        let places = "%.2f";
        let expected_output = vec![1.00];
        let result = _get_range(_range, divisor, places);
        assert_eq!(result, expected_output);
    }

    #[test]
    fn test_get_trade_zone() {
        // Test case 1
        let current_price = 15.0;
        let array = (10.0, 20.0);
        let risk = 5;
        let places = "%.5f";
        let expected_output = Some((14.00000, 16.00000));
        let result = _get_trade_zone(current_price, array, risk, places);
        assert_eq!(result, expected_output);

        // Test case 2
        let current_price = 8.0;
        let array = (5.0, 15.0);
        let risk = 3;
        let places = "%.3f";
        let expected_output = Some((5.0, 8.333));
        let result = _get_trade_zone(current_price, array, risk, places);
        assert_eq!(result, expected_output);

        // Test case 3
        let current_price = 25.0;
        let array = (10.0, 20.0);
        let risk = 5;
        let places = "%.2f";
        let expected_output = None;
        let result = _get_trade_zone(current_price, array, risk, places);
        assert_eq!(result, expected_output);
    }
}
