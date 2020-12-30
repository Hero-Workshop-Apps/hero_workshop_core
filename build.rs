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
        .customize(protobuf_codegen_pure::Customize {
            serde_derive: Some(true),
            gen_mod_rs: Some(true),
            ..Default::default()
        })
        .run()
        .expect("Error generating code");
    // There's an error in the generated code which isn't easy to fix externally, so patch it.
    let file_names = ["message.rs"];
    for file_name in file_names.iter() {
        let file_path = proto_dir.join(file_name);
        let file_content = fs::read_to_string(&file_path).unwrap();
        let mut lines = file_content.lines().collect::<Vec<_>>();
        let version_check_index = lines.iter().enumerate().rfind(|l| l.1.contains("_PROTOBUF_VERSION_CHECK")).unwrap().0;
        lines.insert(version_check_index + 1, "use serde::{Deserialize, Serialize};");
        fs::write(file_path, lines.iter().map(|s| vec![*s, "\n"]).flatten().collect::<String>()).unwrap();
    }
}