# ui/dashboard.py

import streamlit as st
from graph.workflow import graph, WorkflowState


def render_dashboard():

    st.title(
        "Agentic AI Platform"
    )

    request = st.text_input(
        "Enter Request"
    )

    if st.button("Execute"):

        result = graph.invoke({
            "request": request
        })
        st.write(result)