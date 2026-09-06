"""
Multipage streamlit app

Has a selector set for
"""
 
import streamlit as st
 
st.set_page_config(
    page_title="HW Manager",
    layout="centered",
)
 
hw1 = st.Page(
    "HW/HW1.py",
    title="HW1",
    default=True,
)
 
hw2 = st.Page(
    "HW/HW2.py",
    title="HW2",
)
 
pg = st.navigation(
    {
        "Homework": [hw1, hw2],
    }
)
 
pg.run()
 
