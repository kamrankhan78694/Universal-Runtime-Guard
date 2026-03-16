//! API sanitiser — strips control characters and validates JSON schemas.
//!
//! This module provides the core string-sanitisation logic used by language
//! wrappers to clean HTTP response bodies before they reach application code.

use regex::Regex;
use serde_json::Value;
use std::sync::LazyLock;

/// Regex matching ASCII control characters that should be stripped.
/// Matches 0x00–0x08, 0x0B, 0x0C, 0x0E–0x1F, and 0x7F.
static CONTROL_CHAR_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]").unwrap());

/// Strip dangerous ASCII control characters from a string.
///
/// Preserves tabs (`\t`), newlines (`\n`), and carriage returns (`\r`).
///
/// # Examples
///
/// ```
/// use guard_core::sanitiser::strip_control_chars;
/// assert_eq!(strip_control_chars("hello\x00world"), "helloworld");
/// assert_eq!(strip_control_chars("tabs\tare\tok"), "tabs\tare\tok");
/// ```
pub fn strip_control_chars(input: &str) -> String {
    CONTROL_CHAR_RE.replace_all(input, "").into_owned()
}

/// Recursively sanitise all string values in a JSON value.
pub fn sanitise_json(value: &Value) -> Value {
    match value {
        Value::String(s) => Value::String(strip_control_chars(s)),
        Value::Array(arr) => Value::Array(arr.iter().map(sanitise_json).collect()),
        Value::Object(map) => {
            let sanitised = map
                .iter()
                .map(|(k, v)| (k.clone(), sanitise_json(v)))
                .collect();
            Value::Object(sanitised)
        }
        other => other.clone(),
    }
}

/// Schema validation warning.
#[derive(Debug, Clone)]
pub struct SchemaWarning {
    pub path: String,
    pub message: String,
}

/// Check HTTP status code and return a warning message if applicable.
pub fn check_status_code(status: u16, url: &str) -> Option<String> {
    if status >= 500 {
        Some(format!(
            "⚠️  API response: server error {} from {}",
            status, url
        ))
    } else if status >= 400 {
        Some(format!(
            "⚠️  API response: client error {} from {}",
            status, url
        ))
    } else if status >= 300 {
        Some(format!(
            "⚠️  API response: unexpected redirect {} from {}",
            status, url
        ))
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strip_null_bytes() {
        assert_eq!(strip_control_chars("hello\x00world"), "helloworld");
    }

    #[test]
    fn test_preserve_tabs_newlines() {
        assert_eq!(strip_control_chars("a\tb\nc\r\n"), "a\tb\nc\r\n");
    }

    #[test]
    fn test_strip_mixed_control_chars() {
        assert_eq!(
            strip_control_chars("a\x01b\x02c\x7fd"),
            "abcd"
        );
    }

    #[test]
    fn test_sanitise_json_string() {
        let input = Value::String("hello\x00world".into());
        let result = sanitise_json(&input);
        assert_eq!(result, Value::String("helloworld".into()));
    }

    #[test]
    fn test_sanitise_json_nested() {
        let input = serde_json::json!({
            "name": "test\x01value",
            "nested": {"key": "val\x02ue"}
        });
        let result = sanitise_json(&input);
        assert_eq!(result["name"], "testvalue");
        assert_eq!(result["nested"]["key"], "value");
    }

    #[test]
    fn test_sanitise_json_array() {
        let input = serde_json::json!(["a\x00b", "c\x01d"]);
        let result = sanitise_json(&input);
        assert_eq!(result[0], "ab");
        assert_eq!(result[1], "cd");
    }

    #[test]
    fn test_check_status_500() {
        let warning = check_status_code(500, "https://example.com");
        assert!(warning.is_some());
        assert!(warning.unwrap().contains("server error"));
    }

    #[test]
    fn test_check_status_404() {
        let warning = check_status_code(404, "https://example.com");
        assert!(warning.is_some());
        assert!(warning.unwrap().contains("client error"));
    }

    #[test]
    fn test_check_status_301() {
        let warning = check_status_code(301, "https://example.com");
        assert!(warning.is_some());
        assert!(warning.unwrap().contains("redirect"));
    }

    #[test]
    fn test_check_status_200() {
        let warning = check_status_code(200, "https://example.com");
        assert!(warning.is_none());
    }
}
