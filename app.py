# app.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials
from utils.auth import login_user, signup_user, init_auth

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Learning Coach",
    page_icon="🎓",
    layout="wide"
)

# --- Firebase Initialization ---
if not firebase_admin._apps:
    creds = credentials.Certificate(dict(st.secrets["firebase_credentials"]))
    firebase_admin.initialize_app(creds)

# --- Initialize Authentication System ---
init_auth()

# --- Session State Management ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'page' not in st.session_state:
    st.session_state['page'] = 'dashboard' # Default page after login

# --- Main App Logic ---
if st.session_state.get('logged_in', False):
    # If logged in, act as a router to show the correct page
    if st.session_state['page'] == 'quiz':
        st.switch_page("pages/2_Quiz.py")
    else: # Default to dashboard
        st.switch_page("pages/1_Dashboard.py")

else:
    # If not logged in, show the login/signup UI.
    st.title("🎓 Welcome to your AI Learning Coach")
    st.markdown("### Transform your learning with AI-powered study plans")
    
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        st.header("Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", type="primary"):
            if login_email and login_password:
                login_user(login_email, login_password)
            else:
                st.error("Please fill in all fields")

    with signup_tab:
        st.header("Sign Up")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        signup_confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
        
        if st.button("Sign Up", type="primary"):
            if signup_email and signup_password and signup_confirm_password:
                if len(signup_password) < 6:
                    st.error("Password must be at least 6 characters long")
                elif signup_password == signup_confirm_password:
                    signup_user(signup_email, signup_password)
                else:
                    st.error("Passwords do not match")
            else:
                st.error("Please fill in all fields")