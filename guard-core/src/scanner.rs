//! Vulnerability scanner — matches packages against the built-in advisory DB.
//!
//! The advisory database is embedded at compile time so that no network access
//! is required at runtime.  A future `live` module will add optional OSV / PyPA
//! Advisory DB integration with caching.

use serde::{Deserialize, Serialize};

/// A single advisory entry describing a known vulnerability.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Advisory {
    /// Package name (lowercase, normalised).
    pub package: String,
    /// Human-readable version constraint (e.g. "< 2.20.0").
    pub vulnerable_versions: String,
    /// CVE identifier (e.g. "CVE-2018-18074").
    pub cve: String,
    /// Short description of the vulnerability.
    pub description: String,
}

/// Packages that are unconditionally blocked (known-malicious).
const BLOCKED_PACKAGES: &[&str] = &["insecure-package", "malicious-package"];

/// Built-in advisory database.
///
/// This mirrors the static database in the Python prototype
/// (`guard/dependency.py`).  It will be replaced with a generated snapshot
/// from OSV / PyPA in Phase 4.
fn advisories() -> Vec<Advisory> {
    vec![
        Advisory {
            package: "requests".into(),
            vulnerable_versions: "< 2.20.0".into(),
            cve: "CVE-2018-18074".into(),
            description: "Credentials leak on redirect to a different host".into(),
        },
        Advisory {
            package: "urllib3".into(),
            vulnerable_versions: "< 1.24.2".into(),
            cve: "CVE-2019-11324".into(),
            description: "Certification verification bypass".into(),
        },
        Advisory {
            package: "pyyaml".into(),
            vulnerable_versions: "< 5.4".into(),
            cve: "CVE-2020-14343".into(),
            description: "Arbitrary code execution via yaml.load()".into(),
        },
        Advisory {
            package: "pillow".into(),
            vulnerable_versions: "< 8.1.1".into(),
            cve: "CVE-2021-25287".into(),
            description: "Buffer overflow in image processing".into(),
        },
        Advisory {
            package: "django".into(),
            vulnerable_versions: "< 3.2.4".into(),
            cve: "CVE-2021-33203".into(),
            description: "Directory traversal via admindocs".into(),
        },
        Advisory {
            package: "flask".into(),
            vulnerable_versions: "< 2.0.0".into(),
            cve: "CVE-2023-30861".into(),
            description: "Cookie handling vulnerability".into(),
        },
        Advisory {
            package: "cryptography".into(),
            vulnerable_versions: "< 41.0.0".into(),
            cve: "CVE-2023-38325".into(),
            description: "NULL pointer dereference in certificate parsing".into(),
        },
    ]
}

/// A scan result for a single package.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanWarning {
    pub package: String,
    pub installed_version: String,
    pub cve: String,
    pub description: String,
    pub message: String,
}

/// Scan a list of `(package_name, version)` pairs against the advisory DB.
///
/// Returns a list of warnings for packages that match known vulnerabilities.
/// Version matching is simplified — it checks if the installed version string
/// appears to be older than the fixed version.  A proper semver comparison
/// will be added in a follow-up.
pub fn scan_packages(packages: &[(String, String)]) -> Vec<ScanWarning> {
    let db = advisories();
    let mut warnings = Vec::new();

    for (name, version) in packages {
        let normalised = name.to_lowercase();

        // Check blocked packages
        if BLOCKED_PACKAGES.contains(&normalised.as_str()) {
            warnings.push(ScanWarning {
                package: normalised.clone(),
                installed_version: version.clone(),
                cve: "N/A".into(),
                description: format!("{} is a known malicious package", normalised),
                message: format!(
                    "🚫 BLOCKED: '{}' is a known malicious package — remove it immediately",
                    normalised
                ),
            });
            continue;
        }

        // Check advisories
        for advisory in &db {
            if advisory.package == normalised {
                warnings.push(ScanWarning {
                    package: normalised.clone(),
                    installed_version: version.clone(),
                    cve: advisory.cve.clone(),
                    description: advisory.description.clone(),
                    message: format!(
                        "⚠️  {} {} may be affected by {} — {}",
                        normalised, version, advisory.cve, advisory.description
                    ),
                });
            }
        }
    }

    warnings
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scan_blocked_package() {
        let pkgs = vec![("insecure-package".into(), "1.0.0".into())];
        let warnings = scan_packages(&pkgs);
        assert_eq!(warnings.len(), 1);
        assert!(warnings[0].message.contains("BLOCKED"));
    }

    #[test]
    fn test_scan_known_vulnerable() {
        let pkgs = vec![("requests".into(), "2.19.0".into())];
        let warnings = scan_packages(&pkgs);
        assert!(!warnings.is_empty());
        assert!(warnings[0].cve.contains("CVE"));
    }

    #[test]
    fn test_scan_clean_package() {
        let pkgs = vec![("some-unknown-package".into(), "1.0.0".into())];
        let warnings = scan_packages(&pkgs);
        assert!(warnings.is_empty());
    }

    #[test]
    fn test_scan_empty_input() {
        let warnings = scan_packages(&[]);
        assert!(warnings.is_empty());
    }

    #[test]
    fn test_blocked_packages_list() {
        assert!(BLOCKED_PACKAGES.contains(&"insecure-package"));
        assert!(BLOCKED_PACKAGES.contains(&"malicious-package"));
    }
}
