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
    pub kind: Option<String>,
    pub trend: Option<String>,
    pub entry: f64,
    pub stop: f64,
    pub no_of_trades: i32,
    pub use_fibonacci: Option<bool>,
}

#[derive(Debug, Clone,Default)]
pub struct TradingZoneDict {
    pub entry: f64,
    pub stop: f64,
    pub size: f64,
}

#[derive(Debug, Clone,Default)]
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
    pub use_fibonacci: Option<bool>,
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

    pub fn get_trading_zones(&self, params: TradingZoneType) -> Vec<TradingZoneDict> {
        let kind = if params.kind.is_some() { params.kind.unwrap() } else { self.kind.clone() };
        let _entry = if kind == "long" { self.resistance } else { self.support };
        let _stop = if kind == "long" { self.support } else { self.resistance };

        fn build_entry_and_stop(u: Vec<f64>, _kind: &str) -> Vec<TradingZoneDict> {
            let mut result = Vec::new();
            for (i, &o) in u.iter().enumerate() {
                if (_kind == "long" && i < u.len() - 1) || (_kind == "short" && i > 0) {
                    let mut map = TradingZoneDict::default();
                   
                    if _kind == "long" {
                        map.stop = o;
                        map.entry = u[i + 1];
                    } else {
                        map.stop = u[i - 1];
                        map.entry = o;
                    }
                    result.push(map);
                }
            }
            result
        }

        let use_fibonacci = params.use_fibonacci.unwrap_or(self.use_fibonacci.unwrap_or(false));
        if use_fibonacci {
            let price_places = self.price_places.as_deref().unwrap_or_default();
            let _r = fibonacci_analysis(self.support, self.resistance, &kind, "long", price_places);
            return build_entry_and_stop(_r, &kind)
                // .filter(|x| x.contains_key("entry") && x.contains_key("stop"))
                // .map(|x| TradingZoneDict {
                //     entry: *x.get("entry").unwrap(),
                //     stop: *x.get("stop").unwrap(),
                //     size: 0.0, // Placeholder, adjust as needed
                // })
                // .collect();
        }

        let result = build_config(
            self,
            ParamType {
                entry: Some(params.entry),
                stop: Some(params.stop),
                kind: Some(params.trend.unwrap_or(self.kind.clone())),
                no_of_trades: Some(params.no_of_trades),
                ..Default::default()
            },
        );

        match result {
            BuildConfigType::VecHashMap(vec_hashmap)=>vec_hashmap.into_iter()
            .map(|x| {
                let entry = if kind == "long" { x.get("entry").unwrap() } else { x.get("stop").unwrap() };
                let stop = if kind == "long" { x.get("stop").unwrap() } else { x.get("entry").unwrap() };
                TradingZoneDict {
                    entry: *entry,
                    stop: *stop,
                    size: *x.get("quantity").unwrap(),
                }
            })
            .collect(),
            BuildConfigType::VecSignal(_)=> Vec::new()
        }

        // result.into_iter()
        //     .map(|x| {
        //         let entry = if kind == "long" { x.get("entry").unwrap() } else { x.get("stop").unwrap() };
        //         let stop = if kind == "long" { x.get("stop").unwrap() } else { x.get("entry").unwrap() };
        //         TradingZoneDict {
        //             entry: *entry,
        //             stop: *stop,
        //             size: *x.get("quantity").unwrap(),
        //         }
        //     })
        //     .collect()
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

pub enum BuildConfigType{
     VecHashMap(Vec<HashMap<String, f64>>),
    VecSignal(Vec<Signal>)
    
}

pub fn build_config(app_config: &AppConfig, params: ParamType) -> BuildConfigType {
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
        return BuildConfigType::VecSignal(vec![instance]);
    }

    if params.stop.is_none() {
        return BuildConfigType::VecHashMap(vec![]);
    }

    let condition = (params.entry.unwrap_or(0.0) > app_config.support && params.kind.as_deref() == Some("long"))
        || (params.entry.unwrap_or(0.0) >= app_config.support && params.kind.as_deref() == Some("short"))
        && params.stop.unwrap_or(0.0) >= 0.999;

    if params.entry == params.stop || !condition {
        return BuildConfigType::VecHashMap(vec![]);
    }

    let result = instance.default_build_entry(
        params.entry.unwrap_or(0.0),
        params.stop.unwrap_or(0.0),
        working_risk,
        None,
        params.kind.as_deref().unwrap_or(&app_config.kind),
        None,
        Some((trade_no as i32).try_into().unwrap()),
        None,
        None,
        0.0,
        None,
        None
    ).into_iter().map(|x| {
        TradeInstanceType{
            entry: x["entry"],
            stop: x["stop"],
            quantity: x["quantity"],
            ..Default::default()
        }
    }).collect();
    let r = compute_total_average_for_each_trade(app_config, result, 0.0, 0.0).into_iter().map(|x| {
        let mut map = HashMap::new();
        map.insert("entry".to_string(), x.entry);
        map.insert("stop".to_string(), x.stop);
        map.insert("quantity".to_string(), x.quantity);
        map
    }).collect();
    BuildConfigType::VecHashMap(r)
}

#[derive(Debug, Clone)]
pub struct AvgType {
    pub price: f64,
    pub quantity: f64,
    pub pnl: f64,
}

pub fn build_avg(
    _trades: Vec<HashMap<String, f64>>,
    _kind: &str,
    decimal_places: &str,
    price_places: &str,
) -> AvgType {
    assert!(!_trades.is_empty());
    let avg = determine_average_entry_and_size(_trades, decimal_places, price_places);
    
    AvgType{
        price: *avg.get("price").unwrap(),
        quantity: *avg.get("quantity").unwrap(),
        pnl: *avg.get("pnl").unwrap_or(&0.0),
    }
}

pub fn compute_total_average_for_each_trade(
    app_config: &AppConfig,
    trades: Vec<TradeInstanceType>,
    _current_qty: f64,
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

    let _trades = trades.clone();

    let avg_condition = |x: TradeInstanceType| {
        let considered: Vec<_> = if kind == "long" {
            _trades.iter().filter(|y| y.entry > current_entry).cloned().collect()
        } else {
            _trades.iter().filter(|y| y.entry < current_entry).cloned().collect()
        };

        let remaining: Vec<_> = less.iter().filter(|v| kind_condition(v, Some(x.entry), Some(|a, b| a >= b), Some(|a, b| a <= b))).cloned().collect();

        if remaining.is_empty() {
            return TradeInstanceType { pnl: 0.0, ..x.clone() };
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

        let mut _pnl = Some(x.pnl);
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
            pnl: to_f(_pnl.unwrap_or(0.0), app_config.decimal_places.as_deref().unwrap_or_default()),
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
            fee: 0.06,
            risk_per_trade: 4.0,
            risk_reward: 4,
            focus: 29200.0,
            budget: 2000.0,
            support: 45000.0,
            resistance: 66660.0,
            percent_change: 0.0,
            trade_split: 8.0,
            take_profit: None,
            kind: "short".to_string(),
            entry: 69040.0,
            stop: 64280.0,
            min_size: 0.003,
            minimum_size: None,
            price_places: Some("%.1f".to_string()),
            decimal_places: Some("%.3f".to_string()),
            strategy: "quantity".to_string(),
            as_array: None,
            raw: None,
            ..Default::default()
        };

        let param_type = ParamType {
            take_profit: Some(app_config.entry),
            entry: Some(app_config.entry),
            risk: None,
            stop: Some(app_config.stop),
            risk_reward: Some(30),
            raw_instance: Some(false),
            kind: Some(app_config.kind.clone()),
            no_of_trades: Some(30),
            increase: Some(true),
            price_places: app_config.price_places.clone(),
            decimal_places: app_config.decimal_places.clone(),
            support: None,
            resistance: None,
        };

        let result = build_config(&app_config, param_type);

        let result_vec = match result {
            BuildConfigType::VecHashMap(vec_hashmap)=>vec_hashmap.into_iter()
            .map(|x| {
                let mut map = HashMap::new();
                map.insert("entry".to_string(), *x.get("entry").unwrap());
                map.insert("stop".to_string(), *x.get("stop").unwrap());
                map.insert("quantity".to_string(), *x.get("quantity").unwrap());
                map.insert("avg_entry".to_string(), *x.get("avg_entry").unwrap_or(&0.0));
                map
            })
            .collect(),
            BuildConfigType::VecSignal(_)=> Vec::new()
        };

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

        

        let result_entries: Vec<f64> = result_vec.iter().map(|x| *x.get("avg_entry").unwrap()).collect();
        assert_eq!(result_entries, expected_output);
    }
}