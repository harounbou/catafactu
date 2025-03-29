# tests/test_security.py
import datetime
import pytest
import streamlit as st
from modules.product_management import add_or_update_product, permanently_delete
from modules.utils import get_db_connection

@pytest.fixture(autouse=True)
def mock_streamlit_session():
    if "user" not in st.session_state:
        st.session_state.user = {"username": "test_user", "role": "cashier"}

@pytest.fixture
def test_product():
    return {
        "reference": "SEC-001",
        "denomination": "Security Test Product",
        "quantite_actuelle": 10,
        "quantite_initiale": 10,
        "quantite_restockee": 0,
        "quantite_vendue": 0,
        "couleurs-dispo-usine": "red",
        "red": 10,
        "images": "",
        "prix-super-gros": 0.0,
        "prix-gros": 0.0,
        "prix-détail": 0.0,
        "discontinued": 0,
        "category": "Test",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def test_privilege_escalation(test_product):
    st.session_state.user["role"] = "admin"
    assert add_or_update_product(test_product), "Failed to add as admin"
    st.session_state.user["role"] = "cashier"
    with pytest.raises(ValueError, match="Only admins can permanently delete"):
        permanently_delete(test_product["reference"])
    st.session_state.user["role"] = "admin"
    assert permanently_delete(test_product["reference"]), "Admin cleanup failed"