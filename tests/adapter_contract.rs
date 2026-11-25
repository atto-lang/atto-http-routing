//! Rust-only *test* model of the HTTP adapter boundary, not a production router.
//! Passing here does not establish any Atto guest execution.
const MAX_RAW: usize = 4096;
const MAX_SEGMENTS: usize = 128;
const MAX_PART: usize = 128;

fn hex(b: u8) -> Option<u8> {
    match b {
        b'0'..=b'9' => Some(b - b'0'),
        b'a'..=b'f' => Some(b - b'a' + 10),
        b'A'..=b'F' => Some(b - b'A' + 10),
        _ => None,
    }
}

// Split before percent decoding; reject decoded separators and second-decode
// opportunities, preserving empty and trailing segments.
fn decode_segment(segment: &str) -> Result<String, &'static str> {
    let bytes = segment.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' {
            if i + 2 >= bytes.len() { return Err("incomplete percent escape"); }
            let a = hex(bytes[i + 1]).ok_or("invalid escape")?;
            let b = hex(bytes[i + 2]).ok_or("invalid escape")?;
            out.push((a << 4) | b);
            i += 3;
        } else {
            out.push(bytes[i]);
            i += 1;
        }
        if out.len() > MAX_PART { return Err("segment too long"); }
    }
    if out.iter().any(|&b| b < 32 || b == 127 || b == b'\\' || b == b'/' || b == b'%') {
        return Err("ambiguous decoded segment");
    }
    let s = String::from_utf8(out).map_err(|_| "invalid UTF-8")?;
    if s == "." || s == ".." { return Err("traversal segment"); }
    Ok(s)
}

fn split_checked(raw: &str) -> Result<Vec<String>, &'static str> {
    if raw.len() > MAX_RAW { return Err("request target too long"); }
    if !raw.starts_with('/') || raw.contains('?') || raw.contains('#') {
        return Err("not a path-only absolute request target");
    }
    if raw == "/" { return Ok(Vec::new()); }
    let mut parts = Vec::new();
    for part in raw[1..].split('/') {
        if parts.len() == MAX_SEGMENTS { return Err("too many segments"); }
        parts.push(decode_segment(part)?);
    }
    Ok(parts)
}

fn valid_method(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| b.is_ascii_uppercase()
        || b.is_ascii_digit() || b"!#$%&'*+-.^_|~".contains(&b) || b == 0x60)
}

fn valid_capture_name(s: &str) -> bool {
    (1..=64).contains(&s.len()) && s.as_bytes()[0].is_ascii_lowercase()
        && s.bytes().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

#[test]
fn strict_slashes_and_root() {
    assert_eq!(split_checked("/").unwrap(), Vec::<String>::new());
    assert_eq!(split_checked("/users/").unwrap(), ["users", ""]);
    assert_eq!(split_checked("/a//b").unwrap(), ["a", "", "b"]);
    assert_ne!(split_checked("/a").unwrap(), split_checked("/a/").unwrap());
}

#[test]
fn encoding_and_traversal_fail_closed() {
    assert_eq!(split_checked("/hello%20world").unwrap(), ["hello world"]);
    assert_eq!(split_checked("/caf%C3%A9").unwrap(), ["café"]);
    for path in ["/a/..", "/a/.", "/a/%2E", "/a/%2e%2e",
        "/a/%2f", "/a/%5c", "/a/%00", "/a/%0a", "/a/%7f",
        "/a/%", "/a/%2", "/a/%Q1", "/a/%C3%28",
        "/a/%252e%252e", "/a/%25", "/a\\b",
        "/a?x=1", "/a#frag", "relative", "", "http://host/a"] {
        assert!(split_checked(path).is_err(), "unsafe path accepted: {path:?}");
    }
}

#[test]
fn size_and_count_limits() {
    assert!(split_checked(&format!("/{}", "a".repeat(MAX_PART))).is_ok());
    assert!(split_checked(&format!("/{}", "a".repeat(MAX_PART + 1))).is_err());
    let max_parts = format!("/{}", vec!["a"; MAX_SEGMENTS].join("/"));
    assert!(split_checked(&max_parts).is_ok());
    assert!(split_checked(&format!("{max_parts}/a")).is_err());
    let max_bytes = format!("/{}", vec!["a".repeat(31); MAX_SEGMENTS].join("/"));
    assert_eq!(max_bytes.len(), MAX_RAW);
    assert!(split_checked(&max_bytes).is_ok());
    assert!(split_checked(&format!("{max_bytes}/")).is_err());
    assert!(split_checked(&format!("/{}", "%41".repeat(128))).is_ok());
    assert!(split_checked(&format!("/{}", "%41".repeat(1366))).is_err());
}

#[test]
fn method_and_capture_names_are_strict_ascii_tokens() {
    for m in ["GET", "POST", "M-SEARCH", "*", "X_A9"] {
        assert!(valid_method(m), "method rejected: {m:?}");
    }
    for m in ["", "get", "gEt", "GET\r\nX: bad", "GET /", "FOO:", "É"] {
        assert!(!valid_method(m), "unsafe method accepted: {m:?}");
    }
    for name in ["id", "user_id", "a9", &"a".repeat(64)] {
        assert!(valid_capture_name(name), "name rejected: {name:?}");
    }
    for name in ["", "9id", "_id", "Bad", "a-b", "a.b", "a/", "é", &"a".repeat(65)] {
        assert!(!valid_capture_name(name), "unsafe name accepted: {name:?}");
    }
}
