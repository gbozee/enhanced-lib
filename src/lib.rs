use pyo3::prelude::*;
use rand::Rng;
use std::cmp::Ordering;
use std::io;
use regex::Regex;


fn extract_number(s: &str) -> Option<u32> {
    let re = Regex::new(r"%\.(\d)f").unwrap();
    re.captures(s).and_then(|cap| cap.get(1).map(|m| m.as_str().parse().unwrap()))
}


// #[pyfunction]
// fn get_zones(current_price: f64, mut focus: f64, percent_change: f64, places: &str) -> impl Iterator<Item = f64> {
//     let mut last = focus;
//     let mut focus_high = last * (1.0 + percent_change);
//     let mut focus_low = last * (1.0 + percent_change).powf(-1.0);
//     let mut vec = Vec::new();

//     if focus_high > current_price {
//         while focus_high > current_price {
//             if last < 1.0 { // to resolve for other symbols
//                 break;
//             }
//             if (focus_high - last).abs() < f64::EPSILON {
//                 break;
//             }
//             vec.push(format!("{:.*}", places, last).parse().unwrap());
//             focus_high = last;
//             last = focus_high * (1.0 + percent_change).powf(-1.0);
//             focus_low = last * (1.0 + percent_change).powf(-1.0);
//         }
//     } else {
//         if focus_high <= current_price {
//             while focus_high <= current_price {
//                 vec.push(format!("{:.*}", places, focus_high).parse().unwrap());
//                 focus_low = focus_high;
//                 last = focus_low * (1.0 + percent_change);
//                 focus_high = last * (1.0 + percent_change);
//             }
//         } else {
//             while focus_low <= current_price {
//                 vec.push(format!("{:.*}", places, focus_high).parse().unwrap());
//                 focus_low = focus_high;
//                 last = focus_low * (1.0 + percent_change);
//                 focus_high = last * (1.0 + percent_change);
//             }
//         }
//     }
//     vec.into_iter()
// }

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_zones() {
        // let mut result = get_zones(100.0, 50.0, 0.1, "2").collect::<Vec<_>>();
        // let expected = vec![55.0, 60.5, 66.55, 73.21, 80.53, 88.58];
        // assert_eq!(result, expected);
        let value = 3.14159;
        let places = 2;
        let formatted = format!("{:.*}", places, value);
        assert_eq!(formatted, "3.14");
        let _places = "%.2f";
        let number = extract_number(_places).unwrap();
        assert_eq!(number, 2);
        // println!("{}", formatted);  // Outputs: 3.14
    }
}


#[pyfunction]
fn guess_the_number() {
    println!("Guess the number!");

    let secret_number = rand::thread_rng().gen_range(1..101);

    loop {
        println!("Please input your guess.");

        let mut guess = String::new();

        io::stdin()
            .read_line(&mut guess)
            .expect("Failed to read line");

        let guess: u32 = match guess.trim().parse() {
            Ok(num) => num,
            Err(_) => continue,
        };

        println!("You guessed: {}", guess);

        match guess.cmp(&secret_number) {
            Ordering::Less => println!("Too small!"),
            Ordering::Greater => println!("Too big!"),
            Ordering::Equal => {
                println!("You win!");
                break;
            }
        }
    }
}

/// A Python module implemented in Rust. The name of this function must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
/// A Python module implemented in Rust.
#[pymodule]
fn _enhanced_lib(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(guess_the_number, m)?)?;
    Ok(())
}
