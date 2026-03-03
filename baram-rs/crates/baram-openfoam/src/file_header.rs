// ════════════════════════════════════════════════════════════════
//  OpenFOAM file header — standard FoamFile block
// ════════════════════════════════════════════════════════════════

pub struct FoamFileHeader {
    pub version: &'static str,
    pub format: &'static str,
    pub class: String,
    pub object: String,
}

impl FoamFileHeader {
    pub fn new(class: &str, object: &str) -> Self {
        Self {
            version: "2.0",
            format: "ascii",
            class: class.to_string(),
            object: object.to_string(),
        }
    }

    pub fn render(&self) -> String {
        format!(
            r#"FoamFile
{{
    version     {};
    format      {};
    class       {};
    object      {};
}}
"#,
            self.version, self.format, self.class, self.object,
        )
    }
}
