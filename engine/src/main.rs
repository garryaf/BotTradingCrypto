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
    // Parity with the Python gate (risk/gate.py): it blends TP1/TP2 reward and
    // deducts the fee, and keys winrate off estimated_winrate_pct — not confidence.
    #[serde(default)]
    pub estimated_winrate_pct: f64,
    #[serde(default)]
    pub dollar_risk: f64,
    #[serde(default)]
    pub fee_usd: f64,
    // Thresholds from the Python gate (single source of truth). Absent -> defaults above.
    #[serde(default)]
    pub limits: Limits,
    #[serde(default)]
    pub snapshot: Option<SnapshotCandidate>,
    #[serde(default)]
    pub portfolio: Option<PortfolioCandidate>,
}

// Thresholds come from the Python gate (the single source of truth) via the
// payload's `limits` block. The defaults here only apply when a field is absent,
// so an old caller still gets today's values — they must stay equal to
// backend/src/risk/gate.py + config defaults.
fn d_max_risk_per_trade_pct() -> f64 { 0.005 }
fn d_daily_loss_limit_pct() -> f64 { 2.0 }
fn d_max_drawdown_limit_pct() -> f64 { 8.0 }
fn d_max_spread_pct() -> f64 { 0.08 } // 0.0008 * 100, payload spread_pct is in percent
fn d_min_24h_volume_usd() -> f64 { 1_000_000.0 }
fn d_max_open_positions() -> i64 { 5 }
fn d_data_freshness_max_age_sec() -> i64 { 30 }
fn d_min_risk_reward_ratio() -> f64 { 1.5 }

#[derive(Debug, Deserialize, Clone)]
pub struct Limits {
    #[serde(default = "d_max_risk_per_trade_pct")]
    pub max_risk_per_trade_pct: f64,
    #[serde(default = "d_daily_loss_limit_pct")]
    pub daily_loss_limit_pct: f64,
    #[serde(default = "d_max_drawdown_limit_pct")]
    pub max_drawdown_limit_pct: f64,
    #[serde(default = "d_max_spread_pct")]
    pub max_spread_pct: f64,
    #[serde(default = "d_min_24h_volume_usd")]
    pub min_24h_volume_usd: f64,
    #[serde(default = "d_max_open_positions")]
    pub max_open_positions: i64,
    #[serde(default = "d_data_freshness_max_age_sec")]
    pub data_freshness_max_age_sec: i64,
    #[serde(default = "d_min_risk_reward_ratio")]
    pub min_risk_reward_ratio: f64,
}

impl Default for Limits {
    fn default() -> Self {
        Limits {
            max_risk_per_trade_pct: d_max_risk_per_trade_pct(),
            daily_loss_limit_pct: d_daily_loss_limit_pct(),
            max_drawdown_limit_pct: d_max_drawdown_limit_pct(),
            max_spread_pct: d_max_spread_pct(),
            min_24h_volume_usd: d_min_24h_volume_usd(),
            max_open_positions: d_max_open_positions(),
            data_freshness_max_age_sec: d_data_freshness_max_age_sec(),
            min_risk_reward_ratio: d_min_risk_reward_ratio(),
        }
    }
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
    let lim = &candidate.limits; // thresholds sourced from the Python gate via payload

    // Gate order & reason strings mirror backend/src/risk/gate.py exactly.

    // Pintu 6 — stop loss wajib eksplisit, di sisi benar relatif ke entry, DAN rasio R:R ≥ 1.5 (FR-RSK-01).
    let is_buy = candidate.action.eq_ignore_ascii_case("BUY");
    let direction_ok = if is_buy {
        candidate.suggested_stop_loss < candidate.target_entry_price
    } else {
        candidate.suggested_stop_loss > candidate.target_entry_price
    };
    let sl_present = candidate.suggested_stop_loss > 0.0
        && candidate.suggested_stop_loss != candidate.target_entry_price
        && direction_ok;
    if !sl_present {
        reasons.push("INVALID_STOP_LOSS".to_string());
    }

    let min_rr = lim.min_risk_reward_ratio;
    let rr_ok = if sl_present {
        let risk_unit = (candidate.target_entry_price - candidate.suggested_stop_loss).abs();
        let tp1_dist = (candidate.suggested_take_profit_1 - candidate.target_entry_price).abs();
        let ok = risk_unit > 0.0 && tp1_dist >= min_rr * risk_unit;
        if !ok {
            reasons.push("INSUFFICIENT_RISK_REWARD".to_string());
        }
        ok
    } else {
        false
    };
    let stop_loss_ok = sl_present && rr_ok;
    gates.insert("stop_loss_check".to_string(), stop_loss_ok);

    // Pintu 2 — risk per trade (allocation fraction <= configured cap).
    let risk_per_trade_ok = candidate.recommended_allocation_pct <= lim.max_risk_per_trade_pct;
    gates.insert("risk_per_trade_check".to_string(), risk_per_trade_ok);
    if !risk_per_trade_ok {
        reasons.push("RISK_PER_TRADE_EXCEEDED".to_string());
    }

    // Pintu 7 — kas & lot minimum. The engine has no min_lot_size/capital in the
    // contract; the Python gate owns sizing. Re-confirm only that cash can cover it.
    let cash = port.map(|p| p.cash_balance_usd).unwrap_or(0.0);
    let balance_ok = sl_present && cash > 0.0;
    gates.insert("balance_lot_check".to_string(), balance_ok);
    if !balance_ok {
        reasons.push("INSUFFICIENT_BALANCE_OR_LOT".to_string());
    }

    // Pintu 1 — Expectancy positif bersih biaya. Blend TP1(1.5R)/TP2(3.0R) 50/50,
    // winrate dari estimated_winrate_pct, fee_ratio_r = fee_usd / dollar_risk — identik gate.py.
    let winrate = candidate.estimated_winrate_pct / 100.0;
    let expectancy_ok = if sl_present {
        let risk_unit = (candidate.target_entry_price - candidate.suggested_stop_loss).abs();
        if risk_unit > 0.0 {
            let r1 = (candidate.suggested_take_profit_1 - candidate.target_entry_price).abs() / risk_unit;
            let r2 = (candidate.suggested_take_profit_2 - candidate.target_entry_price).abs() / risk_unit;
            let reward_r = (r1 + r2) / 2.0;
            let fee_ratio_r = if candidate.dollar_risk > 0.0 {
                candidate.fee_usd / candidate.dollar_risk
            } else {
                1.0
            };
            winrate * reward_r - (1.0 - winrate) - fee_ratio_r > 0.0
        } else {
            false
        }
    } else {
        false
    };
    gates.insert("expectancy_check".to_string(), expectancy_ok);
    if !expectancy_ok {
        reasons.push("NON_POSITIVE_EXPECTANCY".to_string());
    }

    // Pintu 3 — Daily loss limit (persen).
    let daily_loss_pct = port.map(|p| p.daily_loss_pct).unwrap_or(0.0);
    let daily_loss_ok = daily_loss_pct < lim.daily_loss_limit_pct;
    gates.insert("daily_loss_check".to_string(), daily_loss_ok);
    if !daily_loss_ok {
        reasons.push("DAILY_LOSS_LIMIT_EXCEEDED".to_string());
    }

    // Pintu 4 — Drawdown limit.
    let drawdown_pct = port.map(|p| p.current_drawdown_pct).unwrap_or(0.0);
    let drawdown_ok = drawdown_pct < lim.max_drawdown_limit_pct;
    gates.insert("drawdown_check".to_string(), drawdown_ok);
    if !drawdown_ok {
        reasons.push("DRAWDOWN_LIMIT_EXCEEDED".to_string());
    }

    // Pintu 5 — Spread (persen) & likuiditas 24h.
    let spread_pct = snap.map(|s| s.spread_pct).unwrap_or(0.0);
    let liquidity = snap.map(|s| s.pool_liquidity_usd).unwrap_or(0.0);
    let spread_ok = spread_pct <= lim.max_spread_pct && liquidity >= lim.min_24h_volume_usd;
    gates.insert("spread_check".to_string(), spread_ok);
    if !spread_ok {
        reasons.push("SPREAD_OR_LIQUIDITY_INADEQUATE".to_string());
    }

    // Pintu 8 — Batas posisi terbuka maksimal.
    let open_pos = port.map(|p| p.open_positions_count).unwrap_or(0);
    let max_pos_ok = open_pos < lim.max_open_positions;
    gates.insert("max_positions_check".to_string(), max_pos_ok);
    if !max_pos_ok {
        reasons.push("MAX_OPEN_POSITIONS_REACHED".to_string());
    }

    // Pintu 8b — Circuit breaker. The Python gate derives this from an explicit
    // flag it has (is_account_paused); the engine has no such flag in the contract,
    // so it re-confirms the loss/drawdown conditions that would trip the breaker.
    let circuit_breaker_ok = daily_loss_ok && drawdown_ok;
    gates.insert("circuit_breaker_check".to_string(), circuit_breaker_ok);
    if !circuit_breaker_ok && !reasons.contains(&"CIRCUIT_BREAKER_ACTIVE".to_string()) {
        reasons.push("CIRCUIT_BREAKER_ACTIVE".to_string());
    }

    // Pintu 9 — Freshness data.
    let age = snap.map(|s| s.snapshot_age_seconds).unwrap_or(0);
    let freshness_ok = age <= lim.data_freshness_max_age_sec;
    gates.insert("data_freshness_check".to_string(), freshness_ok);
    if !freshness_ok {
        reasons.push("STALE_MARKET_DATA".to_string());
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

const MAX_REQUEST_BYTES: usize = 64 * 1024;

/// Reads one whole HTTP request: headers, then exactly Content-Length body bytes. The backend's
/// httpx client sends headers and body in separate TCP writes, so a single read() usually saw only
/// the headers -> empty body -> 400 for most real requests. None = closed early, oversized or not UTF-8.
fn read_request(stream: &mut TcpStream) -> Option<String> {
    let mut buf: Vec<u8> = Vec::new();
    let mut chunk = [0u8; 4096];
    loop {
        if let Some(end) = buf.windows(4).position(|w| w == b"\r\n\r\n") {
            let head = std::str::from_utf8(&buf[..end]).ok()?;
            let body_len = head
                .lines()
                .filter_map(|line| line.split_once(':'))
                .find(|(name, _)| name.trim().eq_ignore_ascii_case("content-length"))
                .and_then(|(_, value)| value.trim().parse::<usize>().ok())
                .unwrap_or(0);
            if end + 4 + body_len > MAX_REQUEST_BYTES {
                return None;
            }
            if buf.len() >= end + 4 + body_len {
                return String::from_utf8(buf).ok();
            }
        } else if buf.len() > MAX_REQUEST_BYTES {
            return None;
        }
        match stream.read(&mut chunk) {
            Ok(0) | Err(_) => return None,
            Ok(n) => buf.extend_from_slice(&chunk[..n]),
        }
    }
}

fn handle_client(mut stream: TcpStream) {
    // A client that stalls mid-request must not pin this thread forever.
    let _ = stream.set_read_timeout(Some(std::time::Duration::from_secs(5)));
    let request = match read_request(&mut stream) {
        Some(s) => s,
        None => {
            let res = "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
            let _ = stream.write_all(res.as_bytes());
            return;
        }
    };
    let request_str = request.as_str();

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
            estimated_winrate_pct: 60.0,
            dollar_risk: 50.0,
            fee_usd: 0.1,
            limits: Limits::default(),
            snapshot: Some(SnapshotCandidate {
                price_usd: 150.0,
                bid_price: 149.9,
                ask_price: 150.1,
                spread_pct: 0.01, // 0.01% <= 0.08% cap
                snapshot_age_seconds: 5,
                pool_liquidity_usd: 2_000_000.0, // >= 1,000,000 min 24h volume
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

    // --- F-02 parity guards: thresholds must match backend/src/risk/gate.py ---

    #[test]
    fn test_risk_per_trade_above_half_pct_rejected() {
        // Python cap is 0.5% (0.005), not the old 2%. 0.01 must now fail.
        let mut candidate = valid_candidate();
        candidate.recommended_allocation_pct = 0.01;
        let res = evaluate_candidate(&candidate);
        assert!(!res.passed);
        assert!(res.rejection_reasons.contains(&"RISK_PER_TRADE_EXCEEDED".to_string()));
    }

    #[test]
    fn test_fourth_position_rejected() {
        // Python cap is < 5 open positions, not < 3. 4 must still pass, 5 must fail.
        let mut candidate = valid_candidate();
        if let Some(ref mut p) = candidate.portfolio {
            p.open_positions_count = 4;
        }
        assert!(evaluate_candidate(&candidate).passed);
        if let Some(ref mut p) = candidate.portfolio {
            p.open_positions_count = 5;
        }
        let res = evaluate_candidate(&candidate);
        assert!(!res.passed);
        assert!(res.rejection_reasons.contains(&"MAX_OPEN_POSITIONS_REACHED".to_string()));
    }

    #[test]
    fn test_spread_above_cap_and_thin_liquidity_rejected() {
        // Python caps spread at 0.08% and requires >= 1,000,000 24h volume.
        let mut candidate = valid_candidate();
        if let Some(ref mut s) = candidate.snapshot {
            s.spread_pct = 0.5; // 0.5% > 0.08%
        }
        assert!(res_has(&candidate, "SPREAD_OR_LIQUIDITY_INADEQUATE"));
        let mut candidate2 = valid_candidate();
        if let Some(ref mut s) = candidate2.snapshot {
            s.pool_liquidity_usd = 500_000.0; // below 1,000,000
        }
        assert!(res_has(&candidate2, "SPREAD_OR_LIQUIDITY_INADEQUATE"));
    }

    #[test]
    fn test_expectancy_uses_fee_and_winrate() {
        // Fee large enough to erase the blended reward must flip expectancy negative.
        let mut candidate = valid_candidate();
        candidate.fee_usd = 1000.0; // fee_ratio_r huge vs dollar_risk=50
        let res = evaluate_candidate(&candidate);
        assert!(!res.passed);
        assert!(res.rejection_reasons.contains(&"NON_POSITIVE_EXPECTANCY".to_string()));
    }

    #[test]
    fn test_payload_limits_override_defaults() {
        // Single source of truth: if the Python gate tightens max_open_positions to 2,
        // the engine must enforce 2 even though its default is 5.
        let mut candidate = valid_candidate();
        if let Some(ref mut p) = candidate.portfolio {
            p.open_positions_count = 3; // passes default (<5)
        }
        assert!(evaluate_candidate(&candidate).passed);
        candidate.limits.max_open_positions = 2; // payload-sent tighter limit
        let res = evaluate_candidate(&candidate);
        assert!(!res.passed);
        assert!(res.rejection_reasons.contains(&"MAX_OPEN_POSITIONS_REACHED".to_string()));
    }

    #[test]
    fn test_rr_below_minimum_rejected() {
        // F-17: entry=150, SL=145 -> risk_unit=5. TP1=155 -> tp1_dist=5 -> R:R=1.0 < 1.5
        let mut candidate = valid_candidate();
        candidate.suggested_take_profit_1 = 155.0;
        assert!(res_has(&candidate, "INSUFFICIENT_RISK_REWARD"));
    }

    #[test]
    fn test_exact_rr_passes() {
        // F-17: entry=150, SL=145 -> risk_unit=5. TP1=157.5 -> tp1_dist=7.5 -> R:R=1.5
        let mut candidate = valid_candidate();
        candidate.suggested_take_profit_1 = 157.5;
        assert!(evaluate_candidate(&candidate).passed);
    }

    #[test]
    fn test_missing_limits_json_falls_back_to_defaults() {
        // An old caller that sends no `limits` must still get today's thresholds.
        let json = r#"{"signal_id":"x","symbol":"S","action":"BUY","target_entry_price":150,
            "suggested_stop_loss":145,"suggested_take_profit_1":160,"suggested_take_profit_2":170,
            "recommended_allocation_pct":0.005,"estimated_winrate_pct":60,"dollar_risk":50,"fee_usd":0.1,
            "snapshot":{"spread_pct":0.01,"snapshot_age_seconds":5,"pool_liquidity_usd":2000000},
            "portfolio":{"cash_balance_usd":10000,"daily_loss_pct":0,"current_drawdown_pct":0,"open_positions_count":0}}"#;
        let candidate: SignalCandidate = serde_json::from_str(json).unwrap();
        assert_eq!(candidate.limits.max_open_positions, 5);
        assert_eq!(candidate.limits.min_risk_reward_ratio, 1.5);
        assert!(evaluate_candidate(&candidate).passed);
    }

    #[test]
    fn test_request_split_across_tcp_writes_is_read_whole() {
        // Regression: headers and body arriving in separate writes (what httpx does) must not
        // be answered with 400 because only the first segment was read.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let body = r#"{"signal_id":"split","symbol":"S","action":"BUY"}"#;
        let client = std::thread::spawn(move || {
            let mut s = TcpStream::connect(addr).unwrap();
            s.write_all(format!("POST /evaluate HTTP/1.1\r\nContent-Length: {}\r\n\r\n", body.len()).as_bytes())
                .unwrap();
            s.flush().unwrap();
            std::thread::sleep(std::time::Duration::from_millis(50));
            s.write_all(body.as_bytes()).unwrap();
            let mut resp = String::new();
            s.read_to_string(&mut resp).unwrap();
            resp
        });
        let (stream, _) = listener.accept().unwrap();
        handle_client(stream);
        let resp = client.join().unwrap();
        assert!(resp.starts_with("HTTP/1.1 200"), "{resp}");
        assert!(resp.contains(r#""signal_id":"split""#), "{resp}");
    }

    #[test]
    fn test_oversized_request_rejected() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let client = std::thread::spawn(move || {
            let mut s = TcpStream::connect(addr).unwrap();
            s.write_all(b"POST /evaluate HTTP/1.1\r\nContent-Length: 999999999\r\n\r\n").unwrap();
            let mut resp = String::new();
            s.read_to_string(&mut resp).unwrap();
            resp
        });
        let (stream, _) = listener.accept().unwrap();
        handle_client(stream);
        assert!(client.join().unwrap().starts_with("HTTP/1.1 400"));
    }

    fn res_has(c: &SignalCandidate, reason: &str) -> bool {
        let res = evaluate_candidate(c);
        !res.passed && res.rejection_reasons.contains(&reason.to_string())
    }
}
