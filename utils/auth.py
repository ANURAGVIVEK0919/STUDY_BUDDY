import streamlit as st
import firebase_admin
from firebase_admin import auth, firestore
import time
import hashlib
import base64

def get_session_key():
    """Generate a simple session key based on browser session"""
    # Use Streamlit's session state to create a persistent key
    if 'session_key' not in st.session_state:
        # Create a unique session key when first accessed
        import uuid
        st.session_state.session_key = str(uuid.uuid4())
    return st.session_state.session_key

def save_user_session(user_id, email):
    """Save user session in a more persistent way"""
    session_key = get_session_key()
    
    # Store in Streamlit's session state
    st.session_state['logged_in'] = True
    st.session_state['user_id'] = user_id
    st.session_state['user_email'] = email
    st.session_state['auth_timestamp'] = time.time()
    
    # Also save to browser localStorage equivalent using secrets
    session_data = {
        'user_id': user_id,
        'email': email,
        'timestamp': time.time()
    }
    
    # Encode session data
    import json
    session_str = base64.b64encode(json.dumps(session_data).encode()).decode()
    st.session_state['persistent_session'] = session_str
    
    return True

def restore_user_session():
    """Restore user session if it exists"""
    try:
        # Check if we have a persistent session
        session_data_str = st.session_state.get('persistent_session')
        if not session_data_str:
            return False
        
        # Decode session data
        import json
        session_data = json.loads(base64.b64decode(session_data_str.encode()).decode())
        
        # Check if session is still valid (within 24 hours)
        current_time = time.time()
        session_time = session_data.get('timestamp', 0)
        
        # Session expires after 24 hours
        if current_time - session_time > 86400:  # 24 hours
            return False
        
        # Verify user still exists in database
        db = firestore.client()
        user_doc = db.collection('users').document(session_data['user_id']).get()
        
        if user_doc.exists:
            # Restore session
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = session_data['user_id']
            st.session_state['user_email'] = session_data['email']
            st.session_state['auth_timestamp'] = current_time
            return True
        
        return False
        
    except Exception as e:
        # If anything goes wrong, just return False
        return False

def login_user(email, password):
    """Handle user login with persistent session"""
    try:
        # Note: Firebase Admin SDK doesn't directly authenticate users with password
        # For demo purposes, we'll check if user exists in Firestore
        db = firestore.client()
        
        # Check if user exists in Firestore
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1)
        docs = list(query.stream())
        
        if docs:
            user_doc = docs[0]
            user_id = user_doc.id
            
            # Save session
            if save_user_session(user_id, email):
                st.success("Login successful!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Failed to create session. Please try again.")
        else:
            st.error("User not found. Please sign up first.")
            
    except Exception as e:
        st.error(f"Login failed: {str(e)}")

def signup_user(email, password):
    """Handle user signup"""
    try:
        if len(password) < 6:
            st.error("Password must be at least 6 characters long")
            return
            
        # Create user in Firebase Auth
        user = auth.create_user(
            email=email,
            password=password
        )
        
        # Store user data in Firestore
        db = firestore.client()
        db.collection('users').document(user.uid).set({
            'email': email,
            'created_at': firestore.SERVER_TIMESTAMP,
            'plans': [],
            'quiz_scores': []
        })
        
        st.success("Account created successfully! Please login with your credentials.")
        
    except auth.EmailAlreadyExistsError:
        st.error("Email already exists. Please use a different email or login.")
    except Exception as e:
        st.error(f"Signup failed: {str(e)}")

def logout_user():
    """Handle user logout and clear session"""
    try:
        # Clear all session data
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['user_email'] = None
        st.session_state['persistent_session'] = None
        st.session_state['auth_timestamp'] = None
        st.session_state['page'] = 'dashboard'
        
        st.success("Logged out successfully!")
        time.sleep(1)
        st.rerun()
        
    except Exception as e:
        st.error(f"Logout failed: {str(e)}")

def require_auth():
    """Require user to be authenticated to access the page"""
    # First try to restore session if not logged in
    if not st.session_state.get('logged_in', False):
        if not restore_user_session():
            st.error("Please login first")
            st.stop()
        
def init_auth():
    """Initialize authentication system - call this in main app"""
    # Initialize session state variables if they don't exist
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'user_email' not in st.session_state:
        st.session_state['user_email'] = None
    
    # Try to restore session if not logged in
    if not st.session_state.get('logged_in', False):
        restore_user_session()