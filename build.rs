use std::{
    fs,
    path::PathBuf,
};

fn main() {
    let out_dir = PathBuf::from(std::env::var("OUT_DIR").unwrap());
    let proto_dir = out_dir.join("generated_protobuf_code/");
    fs::create_dir_all(&proto_dir).unwrap();
    protobuf_codegen_pure::Codegen::new()
        .out_dir(&proto_dir)
        .input("protobuf_definitions/message.proto")
        .include("protobuf_definitions")
        .run()
        .expect("Error generating code");
    fs::write(out_dir.join("generated_protobuf_code.rs"), format!("#[path = r#\"{}\"#] mod message;", proto_dir.join("message.rs").display())).unwrap();
}