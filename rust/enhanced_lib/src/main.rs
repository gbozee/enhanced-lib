use enhanced_lib::trade_signal::Signal;

pub fn main() {
    let mut signal = Signal {
        focus: 67629.3,
        budget: 2000.0,
        percent_change: 0.027906543465628042,
        price_places: "%.1f".to_string(),
        decimal_places: "%.3f".to_string(),
        fee: 0.0006,
        support: 65858.0,
        resistance: 70495.0,
        take_profit: None,
        risk_per_trade: 1.325,
        risk_reward: 35,
        additional_increase: 0.0,
        split: None,
        minimum_size: 0.004,
        ..Default::default()
    };
    let result = signal.get_future_zones(67629.3, "short");
    println!("Hello, world! {:?}", result);
}
