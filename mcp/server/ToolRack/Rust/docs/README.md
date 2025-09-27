# Rust MCP Filesystem

Rust MCP Filesystem is a blazingly fast, asynchronous, and lightweight MCP (Model Context Protocol) server designed for efficient handling of various filesystem operations.  
This project is a pure Rust rewrite of the JavaScript-based **@modelcontextprotocol/server-filesystem**, offering enhanced capabilities, improved performance, and a robust feature set tailored for modern filesystem interactions.

Refer to the [quickstart](quickstart.md) guide for installation and configuration instructions.

## Features

- **⚡ High Performance**: Built in Rust for speed and efficiency, leveraging asynchronous I/O to handle filesystem operations seamlessly.
- **🔒 Read-Only by Default**: Starts with no write access, ensuring safety until explicitly configured otherwise.
- **🔍 Advanced Glob Search**: Full glob pattern matching for precise file and directory filtering (e.g., `*.rs`, `src/**/*.txt`, `logs/error-???.log`).
- **📦 ZIP Archive Support**: Tools to create ZIP archives from files or directories and extract ZIP files with ease.
- **🪶 Lightweight**: Standalone with no external dependencies (e.g., no Node.js, Python etc required), compiled to a single binary with a minimal resource footprint, ideal for both lightweight and extensive deployment scenarios.

#### Refer to &nbsp; [capabilities](capabilities.md) &nbsp; for a full list of tools and other capabilities.

## Purpose

This project aims to provide a reliable, secure, and feature-rich MCP server for filesystem management, reimagining the capabilities of **@modelcontextprotocol/server-filesystem** in a more performant and type-safe language. Whether you’re using this for file exploration, automation, or system integration, rust-mcp-filesystem offers a solid foundation.

## 🧰 Built With

The project leverages the [rust-mcp-sdk](https://github.com/rust-mcp-stack/rust-mcp-sdk) and [rust-mcp-schema](https://github.com/rust-mcp-stack/rust-mcp-schema) to build this server. check out those repositories if you’re interested in crafting your own Rust-based MCP project or converting existing ones to Rust for enhanced performance and safety.

## License

This project is licensed under the MIT License. see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Inspired by @modelcontextprotocol/server-filesystem and built with the power of Rust.
