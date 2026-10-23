"""Shared filter controls that fit available space without clipping labels."""
import streamlit as st


def render_cloud_features(tags, suffix):
    features = (
        ("Thang máy", "TMA", "tma"),
        ("Nội thất", "NTC", "ntc"),
        ("Không lỗi", "KLP", "klp"),
        ("2 MT", "2MT", "2mt"),
        ("Căn góc", "CGO", "cgo"),
        ("TTT", "TTT", "ttt"),
        ("DTT", "DTT", "dtt"),
    )
    # Content-sized items wrap together; seven narrow columns truncated labels
    # on tablets. The existing widget keys preserve the active filter state.
    with st.container(horizontal=True, gap="small"):
        for label, tag, key in features:
            st.checkbox(label, value=tag in tags, key=f"{key}_{suffix}", width="content")
