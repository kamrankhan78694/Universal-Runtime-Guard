//! # guard-core
//!
//! Core engine for **Universal Runtime Guard** — a defensive runtime toolkit
//! that protects applications through three independent safety layers:
//!
//! 1. **Vulnerability Scanner** — matches installed packages against a
//!    built-in advisory database (CVE / OSV entries).
//! 2. **API Sanitiser** — strips control characters, validates JSON schemas,
//!    and checks HTTP status codes.
//! 3. **Error Advisor** — pattern-matches exception/error messages to
//!    actionable fix suggestions.
//!
//! This crate is the shared Rust implementation that powers thin wrappers
//! for Python (PyO3), Node.js (napi-rs), Go (cgo), and a standalone CLI.
//!
//! ## Usage
//!
//! ```rust
//! use guard_core::{scanner, sanitiser, advisor};
//!
//! // Scan for known vulnerabilities
//! let warnings = scanner::scan_packages(&[
//!     ("requests".into(), "2.19.0".into()),
//! ]);
//!
//! // Sanitise a string
//! let clean = sanitiser::strip_control_chars("hello\x00world");
//! assert_eq!(clean, "helloworld");
//!
//! // Get a fix suggestion
//! let suggestion = advisor::suggest("ModuleNotFoundError", "No module named 'flask'");
//! assert!(suggestion.is_some());
//! ```

pub mod advisor;
pub mod scanner;
pub mod sanitiser;
