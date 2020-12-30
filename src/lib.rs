#[cfg(not(windows))]
mod generated_protobuf {
    include!(concat!(env!("OUT_DIR"), "/generated_protobuf_code/mod.rs"));
}

#[cfg(windows)]
mod generated_protobuf {
    include!(concat!(env!("OUT_DIR"), "\\generated_protobuf_code\\mod.rs"));
}

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(2 + 2, 4);
    }
}
