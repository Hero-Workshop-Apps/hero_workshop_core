#[cfg(not(windows))]
mod generated_protobuf {
    include!(concat!(env!("OUT_DIR"), "/generated_protobuf_code/mod.rs"));
}

#[cfg(windows)]
mod generated_protobuf {
    include!(concat!(env!("OUT_DIR"), "\\generated_protobuf_code\\mod.rs"));
}

#[cxx::bridge]
mod ffi {
    extern "Rust" {
        fn protobuf_entry_point(input: Vec<u8>) -> Vec<u8>;
    }
}

pub fn protobuf_entry_point(_input: Vec<u8>) -> Vec<u8> {
    Vec::from("Hello world!")
}

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(2 + 2, 4);
    }
}
