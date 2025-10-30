import streamlit as st

# Set page configuration for a wide layout and a professional look
st.set_page_config(
    page_title="Comms911DocTools",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Header Section ---
st.title("Comms911DocTools")
st.markdown("### Essential Documentation and Resources for 911 Communications")

# Separator
st.markdown("---")

# --- Welcome Section ---
st.header("Welcome")
st.markdown(
    """
    Welcome to the Comms911 Document Tools suite! This application is designed to provide
    essential documentation and resources for 911 communications professionals, ensuring
    you have quick access to the critical information needed for high-stakes, real-time operations.
    """
)
st.markdown("---")

# --- Tools List Section ---
st.header("🚒 Current Tools Available")

# TERT Tool
st.info(
    """
    **TERT (Telecommunicator Emergency Response Taskforce) Documentation**
    \nAccess guidelines, deployment protocols, and resource lists for TERT operations.
    """
)

# NG-911 Tool
st.info(
    """
    **NG-911 (Next Generation 911) Resources**
    \nComprehensive guides and updates on the transition to and utilization of NG-911 systems.
    """
)

# --- Coming Soon Footer ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style='text-align: center; border-top: 2px dashed #f97316; padding-top: 20px;'>
        <h3 style='color: #f97316;'>⚠️ More is Coming Soon!</h3>
        <p style='color: #6b7280;'>
            We are actively developing and integrating more critical tools to support your mission. 
            Check back soon for exciting updates!
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
