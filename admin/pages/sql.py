"""SQL Query Runner page for ad-hoc data exploration."""

import streamlit as st
import pandas as pd

from utils.ui_helpers import load_custom_css, add_page_header
from utils.db_helpers import format_sql_error
from components.notifications import show_error, show_info
from common.db_utils import fetch_dict

load_custom_css()
add_page_header("SQL Query Runner", icon="🔍", subtitle="Execute read-only SQL queries against the database")

query = st.text_area(
    "SQL Query",
    height=200,
    placeholder="SELECT * FROM dba.timportconfig LIMIT 10",
)

if st.button("Run Query", type="primary"):
    stripped = query.strip()
    if not stripped:
        show_info("Enter a SQL query to execute.")
    elif not stripped.upper().startswith("SELECT"):
        show_error("Only SELECT queries are allowed. Mutations are not permitted from this page.")
    else:
        try:
            results = fetch_dict(stripped)
            if results:
                df = pd.DataFrame(results)
                st.caption(f"{len(df)} row(s) returned")
                st.dataframe(df, use_container_width=True)
            else:
                show_info("Query returned no results.")
        except Exception as e:
            show_error(format_sql_error(e))
