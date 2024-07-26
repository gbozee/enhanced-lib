use std::collections::HashMap;
use std::cmp::Ordering;
use crate::trade_signal::{Signal, TradeInstanceType};
use crate::utils::{
    determine_avg as determine_average_entry_and_size,
    determine_pnl,
    to_f,
    fibonacci_analysis,
};

#[derive(Debug, Clone)]
pub struct TradingZoneType {
    pub kind: String,
    pub trend: String,
    pub entry: f64,
    pub stop: f64,
    pub no_of_trades: i32,
    pub use_fibonacci: bool,
}

#[derive(Debug, Clone)]
pub struct TradingZoneDict {
    pub entry: f64,
    pub stop: f64,
    pub size: f64,
}

#[derive(Debug, Clone)]
pub struct AppConfig {
    pub fee: f64,
    pub risk_per_trade: f64,
    pub risk_reward: i32,
    pub focus: f64,
    pub budget: f64,
    pub support: f64,
    pub resistance: f64,
    pub percent_change: f64,
    pub trade_split: f64,
    pub take_profit: Option<f64>,
    pub kind: String,
    pub entry: f64,
    pub stop: f64,
    pub min_size: f64,
    pub minimum_size: Option<f64>,
    pub price_places: Option<String>,
    pub decimal_places: Option<String>,
    pub strategy: String,
    pub as_array: Option<bool>,
    pub raw: Option<bool>,
}

impl AppConfig {
    pub fn current_entry(&self) -> f64 {
        self.entry
    }

    pub fn get_all_fields(&self, exclude: Vec<&str>) -> Vec<String> {
        let fields = vec![
            "fee", "risk_per_trade", "risk_reward", "focus", "budget", "support", "resistance",
            "percent_change", "trade_split", "take_profit", "kind", "entry", "stop", "min_size",
            "minimum_size", "price_places", "decimal_places", "strategy", "as_array", "raw"
        ];
        fields.into_iter().filter(|f| !exclude.contains(&f)).map(|f| f.to_string()).collect()
    }

    pub fn get_trading_zones(&self, params: HashMap<String, f64>) -> Vec<HashMap<String, f64>> {
        let kind = if params.get("kind").is_some() { params.get("kind").unwrap() } else { self.kind.clone() };
        let _entry = if kind == "long" { self.resistance } else { self.support };
        let _stop = if kind == "long" { self.support } else { self.resistance };

        fn build_entry_and_stop(u: Vec<f64>, _kind: &str) -> Vec<HashMap<String, f64>> {
            let mut result = Vec::new();
            for (i, &o) in u.iter().enumerate() {
                if (_kind == "long" && i < u.len() - 1) || (_kind == "short" && i > 0) {
                    let mut map = HashMap::new();
                    if _kind == "long" {
                        map.insert("stop".to_string(), o);
                        map.insert("entry".to_string(), u[i + 1]);
                    } else {
                        map.insert("stop".to_string(), u[i - 1]);
                        map.insert("entry".to_string(), o);
                    }
                    result.push(map);
                }
            }
            result
        }

        let use_fibonacci = params.get("use_fibonacci").unwrap_or(&self.use_fibonacci).unwrap_or(false);
        if use_fibonacci {
            let price_places = self.price_places.as_deref().unwrap_or_default();
            let _r = fibonacci_analysis(self.support, self.resistance, &kind, "long", price_places);
            return build_entry_and_stop(_r, &kind).into_iter()
                .filter(|x| x.contains_key("entry") && x.contains_key("stop"))
                .map(|x| TradingZoneDict {
                    entry: *x.get("entry").unwrap(),
                    stop: *x.get("stop").unwrap(),
                    size: 0.0, // Placeholder, adjust as needed
                })
                .collect();
        }

        let result = build_config(
            self,
            ParamType {
                entry: Some(params.entry),
                stop: Some(params.stop),
                kind: Some(params.trend),
                no_of_trades: Some(params.no_of_trades),
                ..Default::default()
            },
        );

        result.into_iter()
            .map(|x| {
                let entry = if kind == "long" { x.entry } else { x.stop };
                let stop = if kind == "long" { x.stop } else { x.entry };
                HashMap::from([
                    ("entry".to_string(), entry),
                    ("stop".to_string(), stop),
                    ("size".to_string(), x.quantity),
                ])
            })
            .collect()
    }
}

#[derive(Debug, Clone, Default)]
pub struct ParamType {
    pub take_profit: Option<f64>,
    pub entry: Option<f64>,
    pub risk: Option<f64>,
    pub stop: Option<f64>,
    pub risk_reward: Option<i32>,
    pub raw_instance: Option<bool>,
    pub no_of_trades: Option<i32>,
    pub increase: Option<bool>,
    pub price_places: Option<String>,
    pub decimal_places: Option<String>,
    pub kind: Option<String>,
    pub support: Option<f64>,
    pub resistance: Option<f64>,
}

pub fn build_config(app_config: &AppConfig, params: ParamType) -> Vec<Signal> {
    let fee = app_config.fee / 100.0;
    let working_risk = params.risk.unwrap_or(app_config.risk_per_trade);
    let trade_no = params.no_of_trades.unwrap_or(app_config.risk_reward as i32);
    let minimum_size = app_config.min_size.max(app_config.minimum_size.unwrap_or(0.0));
    let instance = Signal {
        focus: app_config.focus,
        fee,
        budget: app_config.budget,
        risk_reward: params.risk_reward.unwrap_or((trade_no as u32).try_into().unwrap()).try_into().unwrap(),
        support: params.support.unwrap_or(app_config.support),
        resistance: params.resistance.unwrap_or(app_config.resistance),
        price_places: app_config.price_places.clone().unwrap_or_else(|| params.price_places.clone().unwrap_or_default()),
        decimal_places: params.decimal_places.clone().unwrap_or_default(),
        percent_change: app_config.percent_change / app_config.trade_split,
        risk_per_trade: working_risk,
        increase_position: params.increase.unwrap_or(false),
        minimum_size,
        ..Default::default()
    };

    if params.raw_instance.unwrap_or(false) {
        return vec![instance];
    }

    if params.stop.is_none() {
        return vec![];
    }

    let condition = (params.entry.unwrap_or(0.0) > app_config.support && params.kind.as_deref() == Some("long"))
        || (params.entry.unwrap_or(0.0) >= app_config.support && params.kind.as_deref() == Some("short"))
        && params.stop.unwrap_or(0.0) >= 0.999;

    if params.entry == params.stop || !condition {
        return vec![];
    }

    let result = instance.default_build_entry(
        params.entry.unwrap_or(0.0),
        params.stop.unwrap_or(0.0),
        working_risk,
        params.kind.as_deref().unwrap_or(&app_config.kind),
        trade_no,
    );

    compute_total_average_for_each_trade(app_config, result, 0.0, 0.0)
}

#[derive(Debug, Clone)]
pub struct AvgType {
    pub price: f64,
    pub quantity: f64,
    pub pnl: f64,
}

pub fn build_avg(
    _trades: Vec<HashMap<String, f64>>,
    kind: &str,
    decimal_places: &str,
    price_places: &str,
) -> AvgType {
    assert!(!_trades.is_empty());
    let avg = determine_average_entry_and_size(&_trades, decimal_places, price_places);
    avg
}

pub fn compute_total_average_for_each_trade(
    app_config: &AppConfig,
    trades: Vec<TradeInstanceType>,
    current_qty: f64,
    _current_entry: f64,
) -> Vec<TradeInstanceType> {
    let take_profit = if app_config.kind == "long" {
        app_config.entry.max(app_config.stop)
    } else {
        app_config.entry.min(app_config.stop)
    };
    let current_entry = if _current_entry == 0.0 { app_config.current_entry() } else { _current_entry };
    let kind = &app_config.kind;

    let kind_condition = |x: &TradeInstanceType, v: Option<f64>, operand: Option<fn(f64, f64) -> bool>, operand_reverse: Option<fn(f64, f64) -> bool>| {
        let _v = v.unwrap_or(current_entry);
        let _operand = operand.unwrap_or(|a, b| a <= b);
        let _operand_reverse = operand_reverse.unwrap_or(|a, b| a >= b);
        if kind == "long" {
            _operand(x.entry, _v)
        } else {
            _operand_reverse(x.entry, _v)
        }
    };

    let less: Vec<_> = trades.iter().filter(|x| kind_condition(x, None, None, None)).cloned().collect();

    let avg_condition = |x: &TradeInstanceType| {
        let considered: Vec<_> = if kind == "long" {
            trades.iter().filter(|y| y.entry > current_entry).cloned().collect()
        } else {
            trades.iter().filter(|y| y.entry < current_entry).cloned().collect()
        };

        let remaining: Vec<_> = less.iter().filter(|v| kind_condition(v, Some(x.entry), Some(|a, b| a >= b), Some(|a, b| a <= b))).cloned().collect();

        if remaining.is_empty() {
            return TradeInstanceType { pnl: None, ..x.clone() };
        }

        let start = if kind == "long" {
            remaining.iter().map(|x| x.entry).max_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal)).unwrap()
        } else {
            remaining.iter().map(|x| x.entry).min_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal)).unwrap()
        };

        let mut considered = considered.into_iter().map(|mut x| { x.entry = start; x }).collect::<Vec<_>>();
        considered.extend(remaining);

        let avg_entry = build_avg(
            considered.iter().map(|x| {
                let mut map = HashMap::new();
                map.insert("price".to_string(), x.entry);
                map.insert("quantity".to_string(), x.quantity);
                map
            }).collect(),
            kind,
            app_config.price_places.as_deref().unwrap_or_default(),
            app_config.decimal_places.as_deref().unwrap_or_default(),
        );

        let mut _pnl = x.pnl;
        let mut sell_price = x.sell_price;
        let mut loss = 0.0;

        if take_profit != 0.0 {
            _pnl = Some(determine_pnl(avg_entry.price, take_profit, avg_entry.quantity, kind));
            sell_price = take_profit;
            loss = determine_pnl(avg_entry.price, x.stop, avg_entry.quantity, kind);
        }

        TradeInstanceType {
            avg_entry: Some(avg_entry.price),
            avg_size: Some(avg_entry.quantity),
            pnl: Some(to_f(_pnl.unwrap_or(0.0), app_config.decimal_places.as_deref().unwrap_or_default())),
            neg_pnl: Some(to_f(loss, app_config.decimal_places.as_deref().unwrap_or_default())),
            sell_price,
            start_entry: Some(current_entry),
            ..x.clone()
        }
    };

    trades.into_iter().map(avg_condition).collect()
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_build_config() {
        let app_config = AppConfig {
            fee: 0.08,
            risk_per_trade: 1.325,
            risk_reward: 35,
            focus: 67629.3,
            budget: 2000.0,
            support: 65858.0,
            resistance: 70495.0,
            percent_change: 0.027906543465628042,
            trade_split: 1.0,
            take_profit: None,
            kind: "long".to_string(),
            entry: 67800.0,
            stop: 67600.0,
            min_size: 0.004,
            minimum_size: None,
            price_places: Some("%.1f".to_string()),
            decimal_places: Some("%.3f".to_string()),
            strategy: "quantity".to_string(),
            as_array: Some(false),
            raw: Some(false),
        };

        let param_type = ParamType {
            take_profit: None,
            entry: Some(67800.0),
            risk: None,
            stop: Some(67600.0),
            risk_reward: None,
            raw_instance: Some(false),
            kind: Some("long".to_string()),
            no_of_trades: None,
            increase: Some(false),
            price_places: None,
            decimal_places: None,
            support: None,
            resistance: None,
        };

        let result = build_config(&app_config, param_type);

        // Define the expected output based on the logic of the function
        let expected_output = vec![
            67703.1,
            67705.9,
            67708.8,
            67711.6,
            67714.5,
            67717.3,
            67720.2,
            67723.0,
            67725.9,
            67728.7,
            67731.6,
            67734.4,
            67737.3,
            67740.1,
            67743.0,
            67745.8,
            67748.7,
            67751.5,
            67754.4,
            67757.2,
            67760.1,
            67762.9,
            67765.8,
            67768.6,
            67771.5,
            67774.3,
            67777.2,
            67780.1,
            67782.9,
            67785.7,
            67788.6,
            67791.4,
            67794.3,
            67797.2,
            67800.0,
        ];

        let result_entries: Vec<f64> = result.iter().map(|x| x.avg_entry.unwrap()).collect();
        assert_eq!(result_entries, expected_output);
    }
}