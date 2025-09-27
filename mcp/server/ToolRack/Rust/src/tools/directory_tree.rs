use std::path::Path;

use rust_mcp_schema::{schema_utils::CallToolError, CallToolResult};
use rust_mcp_sdk::macros::{mcp_tool, JsonSchema};
use serde_json::json;

use crate::fs_service::FileSystemService;

#[mcp_tool(
    name = "directory_tree",
    description = concat!("FAST & LIGHTWEIGHT: Generates a basic recursive directory structure as JSON. ",
"⚡ USE WHEN: You need quick directory exploration without file analysis. ",
"📊 OUTPUTS: Simple JSON with just file/directory names and types - no content analysis. ",
"🚀 PERFORMANCE: Very fast for large directories since it only reads directory structure, not file contents. ",
"❌ LIMITATIONS: No token counting, no complexity analysis, no file content examination. ",
"✅ IDEAL FOR: Quick structure overview, performance-critical tasks, basic directory mapping. ",
"IMPORTANT: Requires absolute paths only (e.g., D:\\data\\folder). Restricted to pre-configured directories."),
    destructive_hint = false,
    idempotent_hint = false,
    open_world_hint = false,
    read_only_hint = true
)]
#[derive(::serde::Deserialize, ::serde::Serialize, Clone, Debug, JsonSchema)]
pub struct DirectoryTreeTool {
    /// The **absolute root path** for which to generate the directory tree (e.g., `D:\\data\\folder` or `/srv/project_files`).
    pub path: String,
}
impl DirectoryTreeTool {
    pub async fn run_tool(
        params: Self,
        context: &FileSystemService,
    ) -> std::result::Result<CallToolResult, CallToolError> {
        let entries = context
            .list_directory(Path::new(&params.path))
            .await
            .map_err(CallToolError::new)?;

        let json_tree: Vec<serde_json::Value> = entries
            .iter()
            .map(|entry| {
                json!({
                    "name": entry.file_name().to_str().unwrap_or_default(),
                    "type": if entry.path().is_dir(){"directory"}else{"file"}
                })
            })
            .collect();
        let json_str =
            serde_json::to_string_pretty(&json!(json_tree)).map_err(CallToolError::new)?;
        Ok(CallToolResult::text_content(json_str, None))
    }
}
