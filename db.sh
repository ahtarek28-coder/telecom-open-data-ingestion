#!/bin/bash
# Opens the DuckDB CLI directly against this project's database, for writing
# SQL by hand. Location-independent (dirname "$0"), so it keeps working
# after the project folder gets moved.
cd "$(dirname "$0")"
"$HOME/.duckdb/cli/latest/duckdb" telecom_open_data.duckdb
