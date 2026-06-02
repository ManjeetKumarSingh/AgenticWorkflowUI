# ui/dashboard.py

import streamlit as st
from graph.workflow import graph, WorkflowState


def render_dashboard():

    st.title(
        "Agentic AI Platform"
    )

    request = st.text_input(
        "Enter Request",
        key="user_request"
    )

    if st.button("Execute"):

        result = graph.invoke({
            "request": request
        })
        st.write(result)

    # Display workflow graph dynamically
    st.subheader("Workflow Graph")

    try:
        # Get the graph structure dynamically
        graph_obj = graph.get_graph()
        
        # Build mermaid diagram from actual graph structure
        workflow_diagram = "%%{init: {'flowchart': {'curve': 'linear', 'useMaxWidth': true}}}%%\n"
        workflow_diagram += "graph TD\n"
        
        # Add nodes
        node_emojis = {
            "planner": "🔍",
            "dependency": "📋",
            "risk": "⚠️",
            "governance": "✅",
            "action": "⚡",
            "evaluator": "📊"
        }
        
        for node_id, node in graph_obj.nodes.items():
            emoji = node_emojis.get(node_id, "📌")
            node_label = f"{emoji} {node.name}"
            if node_id == "__start__":
                workflow_diagram += f'    start([Start]):::first\n'
            elif node_id == "__end__":
                workflow_diagram += f'    end([End]):::last\n'
            else:
                workflow_diagram += f'    {node_id}["{node_label}"]\n'
        
        # Add edges
        for edge in graph_obj.edges:
            source, target = edge
            if source != "__start__" and target != "__end__":
                workflow_diagram += f'    {source} --> {target}\n'
            elif source == "__start__":
                workflow_diagram += f'    start --> {target}\n'
            elif target == "__end__":
                workflow_diagram += f'    {source} --> end\n'
        
        # Add styling
        workflow_diagram += """
    classDef default fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef first fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef last fill:#ffccbc,stroke:#d84315,stroke-width:2px,color:#000
"""
        
        st.markdown(f"```mermaid\n{workflow_diagram}\n```", unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error rendering graph: {str(e)}")
        st.info("Falling back to static diagram view")