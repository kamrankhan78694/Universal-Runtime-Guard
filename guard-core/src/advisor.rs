//! Error advisor — pattern-matches error messages to fix suggestions.
//!
//! This module contains a set of regex patterns that match common error
//! messages and return actionable fix suggestions.  It mirrors the heuristic
//! patterns from the Python prototype (`guard/advisor.py`).

use regex::Regex;
use std::sync::LazyLock;

/// A single pattern-suggestion pair.
struct Pattern {
    regex: Regex,
    template: &'static str,
}

/// Build the pattern list once.
static PATTERNS: LazyLock<Vec<Pattern>> = LazyLock::new(|| {
    vec![
        Pattern {
            regex: Regex::new(r"No module named '(\w+)'").unwrap(),
            template: "💡 Suggestion: install the missing package with: pip install {}",
        },
        Pattern {
            regex: Regex::new(r"cannot import name '(\w+)'").unwrap(),
            template: "💡 Suggestion: '{}' may have been removed or renamed — check the library version and changelog",
        },
        Pattern {
            regex: Regex::new(r"has no attribute '(\w+)'").unwrap(),
            template: "💡 Suggestion: '{}' might be misspelled or unavailable in this version — check the API docs",
        },
        Pattern {
            regex: Regex::new(r"not callable").unwrap(),
            template: "💡 Suggestion: you are trying to call something that is not a function — check the type",
        },
        Pattern {
            regex: Regex::new(r"KeyError").unwrap(),
            template: "💡 Suggestion: use .get(key, default) instead of [key] to avoid KeyError",
        },
        Pattern {
            regex: Regex::new(r"IndexError").unwrap(),
            template: "💡 Suggestion: check list length before accessing by index",
        },
        Pattern {
            regex: Regex::new(r"division by zero").unwrap(),
            template: "💡 Suggestion: guard the divisor with `if divisor != 0` before dividing",
        },
        Pattern {
            regex: Regex::new(r"No such file or directory").unwrap(),
            template: "💡 Suggestion: verify the file path exists and check for typos",
        },
        Pattern {
            regex: Regex::new(r"Connection refused").unwrap(),
            template: "💡 Suggestion: verify the host and port are correct and the service is running",
        },
        Pattern {
            regex: Regex::new(r"timed out").unwrap(),
            template: "💡 Suggestion: increase the timeout or check if the remote service is responding",
        },
        Pattern {
            regex: Regex::new(r"maximum recursion depth").unwrap(),
            template: "💡 Suggestion: check your recursive function for a missing or incorrect base case",
        },
        Pattern {
            regex: Regex::new(r"MemoryError").unwrap(),
            template: "💡 Suggestion: reduce data size, use generators, or stream data incrementally",
        },
        Pattern {
            regex: Regex::new(r"SSL").unwrap(),
            template: "💡 Suggestion: update your SSL certificates — do not disable SSL verification in production",
        },
        Pattern {
            regex: Regex::new(r"Expecting value").unwrap(),
            template: "💡 Suggestion: the response body is not valid JSON — verify the endpoint returns JSON",
        },
        Pattern {
            regex: Regex::new(r"unsupported operand type").unwrap(),
            template: "💡 Suggestion: check operand types and use explicit type conversion",
        },
    ]
});

/// Suggest a fix based on the error type name and message.
///
/// Returns `Some(suggestion)` if a pattern matches, or `None` if no
/// suggestion is available.
///
/// # Examples
///
/// ```
/// use guard_core::advisor::suggest;
/// let s = suggest("ModuleNotFoundError", "No module named 'flask'");
/// assert!(s.is_some());
/// assert!(s.unwrap().contains("pip install"));
/// ```
pub fn suggest(error_type: &str, message: &str) -> Option<String> {
    let combined = format!("{}: {}", error_type, message);

    for pattern in PATTERNS.iter() {
        // Try matching against the combined string first, then the raw message.
        if let Some(caps) = pattern
            .regex
            .captures(&combined)
            .or_else(|| pattern.regex.captures(message))
        {
            let suggestion = if let Some(m) = caps.get(1) {
                pattern.template.replacen("{}", m.as_str(), 1)
            } else {
                pattern.template.replace("{}", "")
            };
            return Some(suggestion);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_suggest_no_module() {
        let result = suggest("ModuleNotFoundError", "No module named 'flask'");
        assert!(result.is_some());
        assert!(result.unwrap().contains("pip install flask"));
    }

    #[test]
    fn test_suggest_cannot_import() {
        let result = suggest("ImportError", "cannot import name 'foo'");
        assert!(result.is_some());
        assert!(result.unwrap().contains("removed or renamed"));
    }

    #[test]
    fn test_suggest_attribute_error() {
        let result = suggest("AttributeError", "'str' object has no attribute 'foo'");
        assert!(result.is_some());
        assert!(result.unwrap().contains("misspelled"));
    }

    #[test]
    fn test_suggest_key_error() {
        let result = suggest("KeyError", "KeyError: 'missing_key'");
        assert!(result.is_some());
        assert!(result.unwrap().contains(".get("));
    }

    #[test]
    fn test_suggest_division_by_zero() {
        let result = suggest("ZeroDivisionError", "division by zero");
        assert!(result.is_some());
        assert!(result.unwrap().contains("divisor"));
    }

    #[test]
    fn test_suggest_file_not_found() {
        let result = suggest("FileNotFoundError", "No such file or directory: '/tmp/x'");
        assert!(result.is_some());
        assert!(result.unwrap().contains("verify"));
    }

    #[test]
    fn test_suggest_unknown_returns_none() {
        let result = suggest("CustomError", "something completely unknown");
        assert!(result.is_none());
    }

    #[test]
    fn test_suggest_timeout() {
        let result = suggest("TimeoutError", "Connection timed out");
        assert!(result.is_some());
        assert!(result.unwrap().contains("timeout"));
    }

    #[test]
    fn test_suggest_memory_error() {
        let result = suggest("MemoryError", "MemoryError");
        assert!(result.is_some());
        assert!(result.unwrap().contains("reduce"));
    }
}
