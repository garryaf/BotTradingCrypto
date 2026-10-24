use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::time::Instant;

#[derive(Debug, Deserialize, Clone)]
pub struct SnapshotCandidate {
    #[serde(default)]
    pub price_usd: f64,
    #[serde(default)]
    pub bid_price: f64,
    #[serde(default)]
    pub ask_price: f64,
    #[serde(default)]
    pub spread_pct: f64,
    #[serde(default)]
    pub snapshot_age_seconds: i64,
    #[serde(default)]
    pub pool_liquidity_usd: f64,
}

#[derive(Debug, Deserialize, Clone)]
pub struct PortfolioCandidate {
    #[serde(default)]
    pub total_equity_usd: f64,
    #[serde(default)]
    pub cash_balance_usd: f64,
    #[serde(default)]
    pub daily_realized_pnl_usd: f64,
    #[serde(default)]
    pub daily_loss_pct: f64,
    #[serde(default)]
    pub high_water_mark_usd: f64,
    #[serde(default)]
    pub current_drawdown_pct: f64,
    #[serde(default)]
    pub open_positions_count: i64,
    #[serde(default)]
    pub net_expectancy_usd: Option<f64>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct SignalCandidate {
    pub signal_id: String,
    pub symbol: String,
    pub action: String,
    #[serde(default)]
    pub target_entry_price: f64,
    #[serde(default)]
    pub suggested_stop_loss: f64,
    #[serde(default)]
    pub suggested_take_profit_1: f64,
    #[serde(default)]
    pub suggested_take_profit_2: f64,
    #[serde(default)]
    pub recommended_allocation_pct: f64,
    #[serde(default)]
    pub confidence_score: f64,
    #[serde(default)]
    pub snapshot: Option<SnapshotCandidate>,
    #[serde(default)]
    pub portfolio: Option<PortfolioCandidate>,
}

#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub struct RiskEvaluationResult {
    pub signal_id: String,
    pub passed: bool,
    pub gates: HashMap<String, bool>,
    pub rejection_reasons: Vec<String>,
    pub evaluation_ns: u64,
}

pub fn evaluate_candidate(candidate: &SignalCandidate) -> RiskEvaluationResult {
    let start = Instant::now();
    let mut gates = HashMap::new();
    let mut reasons = Vec::new();

    let snap = candidate.snapshot.as_ref();
    let port = candidate.portfolio.as_ref();

    // 1. stop_loss_check
    let is_buy = candidate.action.eq_ignore_ascii_case("BUY");
    let stop_loss_ok = if is_buy {
        candidate.suggested_stop_loss > 0.0 && candidate.suggested_stop_loss < candidate.target_entry_price
    } else {
        candidate.suggested_stop_loss > candidate.target_entry_price
    };
    gates.insert("stop_loss_check".to_string(), stop_loss_ok);
    if !stop_loss_ok {
        reasons.push("INVALID_STOP_LOSS".to_string());
    }

    // 2. expectancy_check
    let risk = (candidate.target_entry_price - candidate.suggested_stop_loss).abs();
    let reward = (candidate.suggested_take_profit_1 - candidate.target_entry_price).abs();
    let winrate = if candidate.confidence_score > 0.0 {
        candidate.confidence_score
    } else {
        0.5
    };
    let expectancy = (winrate * reward) - ((1.0 - winrate) * risk);
    let expectancy_ok = stop_loss_ok && reward > 0.0 && expectancy > 0.0;
    gates.insert("expectancy_check".to_string(), expectancy_ok);
    if !expectancy_ok {
        reasons.push("NON_POSITIVE_EXPECTANCY".to_string());
    }

    // 3. daily_loss_check (limit < 2.0%)
    let daily_loss_pct = port.map(|p| p.daily_loss_pct).unwrap_or(0.0);
    let daily_loss_ok = daily_loss_pct < 2.0;
    gates.insert("daily_loss_check".to_string(), daily_loss_ok);
    if !daily_loss_ok {
        reasons.push("DAILY_LOSS_LIMIT_EXCEEDED".to_string());
    }

    // 4. drawdown_check (limit < 8.0%)
    let drawdown_pct = port.map(|p| p.current_drawdown_pct).unwrap_or(0.0);
    let drawdown_ok = drawdown_pct < 8.0;
    gates.insert("drawdown_check".to_string(), drawdown_ok);
    if !drawdown_ok {
        reasons.push("DRAWDOWN_LIMIT_EXCEEDED".to_string());
    }

    // 5. spread_check (spread <= 0.05 / 5% and liquidity >= 1000)
    let spread_pct = snap.map(|s| s.spread_pct).unwrap_or(0.0);
    let liquidity = snap.map(|s| s.pool_liquidity_usd).unwrap_or(10_000.0);
    let spread_ok = spread_pct <= 0.05 && liquidity >= 1000.0;
    gates.insert("spread_check".to_string(), spread_ok);
    if !spread_ok {
        reasons.push("SPREAD_OR_LIQUIDITY_INADEQUATE".to_string());
    }

    // 6. data_freshness_check (age < 30s)
    let age = snap.map(|s| s.snapshot_age_seconds).unwrap_or(0);
    let freshness_ok = age < 30;
    gates.insert("data_freshness_check".to_string(), freshness_ok);
    if !freshness_ok {
        reasons.push("STALE_MARKET_DATA".to_string());
    }

    // 7. balance_lot_check (cash > 0.0)
    let cash = port.map(|p| p.cash_balance_usd).unwrap_or(100.0);
    let balance_ok = cash > 0.0;
    gates.insert("balance_lot_check".to_string(), balance_ok);
    if !balance_ok {
        reasons.push("INSUFFICIENT_BALANCE_OR_LOT".to_string());
    }

    // 8. max_positions_check (< 3 positions)
    let open_pos = port.map(|p| p.open_positions_count).unwrap_or(0);
    let max_pos_ok = open_pos < 3;
    gates.insert("max_positions_check".to_string(), max_pos_ok);
    if !max_pos_ok {
        reasons.push("MAX_OPEN_POSITIONS_REACHED".to_string());
    }

    // 9. risk_per_trade_check (allocation <= 0.02 / 2%)
    let alloc = candidate.recommended_allocation_pct;
    let risk_per_trade_ok = alloc <= 0.02;
    gates.insert("risk_per_trade_check".to_string(), risk_per_trade_ok);
    if !risk_per_trade_ok {
        reasons.push("EXCEEDS_MAX_RISK_PER_TRADE".to_string());
    }

    // 10. circuit_breaker_check
    let circuit_breaker_ok = daily_loss_ok && drawdown_ok;
    gates.insert("circuit_breaker_check".to_string(), circuit_breaker_ok);
    if !circuit_breaker_ok && !reasons.contains(&"CIRCUIT_BREAKER_ACTIVE".to_string()) {
        reasons.push("CIRCUIT_BREAKER_ACTIVE".to_string());
    }

    let passed = reasons.is_empty() && gates.values().all(|&v| v);
    let elapsed = start.elapsed().as_nanos() as u64;

    RiskEvaluationResult {
        signal_id: candidate.signal_id.clone(),
        passed,
        gates,
        rejection_reasons: reasons,
        evaluation_ns: elapsed,
    }
}

fn handle_client(mut stream: TcpStream) {
    let mut buffer = [0u8; 16384];
    let n = match stream.read(&mut buffer) {
        Ok(n) if n > 0 => n,
        _ => return,
    };

    let request_str = match std::str::from_utf8(&buffer[..n]) {
        Ok(s) => s,
        Err(_) => {
            let res = "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
            let _ = stream.write_all(res.as_bytes());
            return;
        }
    };

    let mut lines = request_str.split("\r\n");
    let req_line = lines.next().unwrap_or("");
    let mut parts = req_line.split_whitespace();
    let method = parts.next().unwrap_or("");
    let path = parts.next().unwrap_or("");

    if method == "POST" && path == "/evaluate" {
        let body = if let Some(idx) = request_str.find("\r\n\r\n") {
            &request_str[idx + 4..]
        } else {
            ""
        };

        match serde_json::from_str::<SignalCandidate>(body) {
            Ok(candidate) => {
                let result = evaluate_candidate(&candidate);
                let json_res = serde_json::to_string(&result).unwrap_or_else(|_| "{}".to_string());
                let response = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    json_res.len(),
                    json_res
                );
                let _ = stream.write_all(response.as_bytes());
            }
            Err(_) => {
                let err_body = r#"{"error":"invalid_json"}"#;
                let response = format!(
                    "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    err_body.len(),
                    err_body
                );
                let _ = stream.write_all(response.as_bytes());
            }
        }
    } else if method == "GET" && (path == "/health" || path == "/") {
        let ok_body = r#"{"status":"healthy","service":"auto-trade-engine"}"#;
        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            ok_body.len(),
            ok_body
        );
        let _ = stream.write_all(response.as_bytes());
    } else {
        let res = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
        let _ = stream.write_all(res.as_bytes());
    }
}

fn main() {
    let addr = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "0.0.0.0:8080".to_string());
    let listener = match TcpListener::bind(&addr) {
        Ok(l) => {
            println!("auto-trade-engine listening on {}", addr);
            l
        }
        Err(e) => {
            eprintln!("Failed to bind to {}: {}", addr, e);
            std::process::exit(1);
        }
    };

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                std::thread::spawn(move || handle_client(stream));
            }
            Err(e) => eprintln!("Connection failed: {}", e),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid_candidate() -> SignalCandidate {
        SignalCandidate {
            signal_id: "sig-test-1".to_string(),
            symbol: "SOLUSDT".to_string(),
            action: "BUY".to_string(),
            target_entry_price: 150.0,
            suggested_stop_loss: 145.0,
            suggested_take_profit_1: 160.0,
            suggested_take_profit_2: 170.0,
            recommended_allocation_pct: 0.005,
            confidence_score: 0.8,
            snapshot: Some(SnapshotCandidate {
                price_usd: 150.0,
                bid_price: 149.9,
                ask_price: 150.1,
                spread_pct: 0.001,
                snapshot_age_seconds: 5,
                pool_liquidity_usd: 500000.0,
            }),
            portfolio: Some(PortfolioCandidate {
                total_equity_usd: 10000.0,
                cash_balance_usd: 10000.0,
                daily_realized_pnl_usd: 0.0,
                daily_loss_pct: 0.0,
                high_water_mark_usd: 10000.0,
                current_drawdown_pct: 0.0,
                open_positions_count: 0,
                net_expectancy_usd: Some(15.0),
            }),
        }
    }

    #[test]
    fn test_valid_signal_passes() {
        let candidate = valid_candidate();
        let res = evaluate_candidate(&candidate);
        assert!(res.passed, "expected pass, got: {:?}", res.rejection_reasons);
        assert_eq!(res.signal_id, "sig-test-1");
        assert!(res.rejection_reasons.is_empty());
        assert_eq!(res.gates.get("drawdown_check"), Some(&true));
    }

    #[test]
    fn test_drawdown_limit_rejected() {
        let mut candidate = valid_candidate();
        if let Some(ref mut p) = candidate.portfolio {
            p.current_drawdown_pct = 9.0;
        }
        let res = evaluate_candidate(&candidate);
        assert!(!res.passed);
        assert!(res.rejection_reasons.contains(&"DRAWDOWN_LIMIT_EXCEEDED".to_string()));
    }

    #[test]
    fn test_daily_loss_limit_rejected() {
        let mut candidate = valid_candidate();
        if let Some(ref mut p) = candidate.portfolio {
            p.daily_loss_pct = 2.5;
        }
        let res = evaluate_candidate(&candidate);
        assert!(!res.passed);
        assert!(res.rejection_reasons.contains(&"DAILY_LOSS_LIMIT_EXCEEDED".to_string()));
    }

    #[test]
    fn test_stale_data_rejected() {
        let mut candidate = valid_candidate();
        if let Some(ref mut s) = candidate.snapshot {
            s.snapshot_age_seconds = 35;
        }
        let res = evaluate_candidate(&candidate);
        assert!(!res.passed);
        assert!(res.rejection_reasons.contains(&"STALE_MARKET_DATA".to_string()));
    }
}
