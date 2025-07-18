import streamlit as st
import google.generativeai as genai
import requests # New import for Firebase REST API
import json # New import for JSON handling

# --- Configuration for Google Gemini API ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Google API Key not found in Streamlit secrets. Please add it to .streamlit/secrets.toml")
    st.stop()

MODEL_NAME = "gemini-1.5-flash-latest" # Using the working model

try:
    gemini_model = genai.GenerativeModel(MODEL_NAME) # Renamed to avoid conflict
except Exception as e:
    st.error(f"Failed to load model '{MODEL_NAME}': {e}")
    st.info("Please check the model name or your API key/network connection.")
    st.stop()

# --- Firebase Configuration from Streamlit secrets ---
# Ensure these keys exist in .streamlit/secrets.toml
FIREBASE_API_KEY = st.secrets.get("FIREBASE_API_KEY")
FIREBASE_AUTH_DOMAIN = st.secrets.get("FIREBASE_AUTH_DOMAIN")
FIREBASE_PROJECT_ID = st.secrets.get("FIREBASE_PROJECT_ID")
FIREBASE_APP_ID = st.secrets.get("FIREBASE_APP_ID")

if not all([FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID, FIREBASE_APP_ID]):
    st.error("Missing Firebase configuration in .streamlit/secrets.toml. Please check your setup.")
    st.stop()

# Base URL for Firebase Authentication REST API
FIREBASE_AUTH_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:"


# --- Firebase Authentication Functions ---

def signup_user(email, password):
    url = f"{FIREBASE_AUTH_URL}signUp?key={FIREBASE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Signup failed: {e}")
        if response.status_code == 400: # Specific Firebase error for existing user, weak password, etc.
            error_data = response.json().get('error', {})
            st.error(f"Error: {error_data.get('message', 'Unknown Firebase error')}")
        return None

def login_user(email, password):
    url = f"{FIREBASE_AUTH_URL}signInWithPassword?key={FIREBASE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Login failed: {e}")
        if response.status_code == 400:
            error_data = response.json().get('error', {})
            st.error(f"Error: {error_data.get('message', 'Invalid credentials or Firebase error')}")
        return None

def logout_user():
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.messages = [] # Clear chat on logout
    st.rerun() # Force rerun to show login screen

# --- Language Options ---
LANGUAGES = {
    "English": "English",
    "Hindi": "Hindi",
    "Spanish": "Spanish",
    "French": "French",
    "German": "German",
    "Japanese": "Japanese",
    "Chinese (Simplified)": "Chinese (Simplified)",
    "Telugu": "Telugu",
    "Tamil": "Tamil",
    "Kannada": "Kannada",
    "Malayalam": "Malayalam",
    "Bengali": "Bengali",
    "Gujarati": "Gujarati",
    "Punjabi": "Punjabi"
}

# --- Streamlit UI ---
st.set_page_config(page_title="AI Language Translator", layout="centered")

# Initialize session state for login status
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None

# --- Main App Logic (Conditional based on login status) ---
if st.session_state.logged_in:
    # --- Authenticated User UI (Translator App) ---
    st.sidebar.title(f"Welcome, {st.session_state.user_info.get('email', 'User')}!")
    if st.sidebar.button("Logout", help="Log out of your account"):
        logout_user()

    st.title("🗣️ AI Language Translator")
    st.markdown("Powered by Google Gemini API")

    # Initialize chat history in session state if it doesn't exist
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": "Hello! I'm your AI translator. Select languages and type to translate."})

    # Language Selection controls at the top
    st.sidebar.subheader("Language Settings")
    col1_sidebar, col2_sidebar = st.sidebar.columns(2)
    with col1_sidebar:
        source_language = st.selectbox("Source Language", list(LANGUAGES.keys()), index=0, key="source_lang_select")
    with col2_sidebar:
        target_language = st.selectbox("Target Language", list(LANGUAGES.keys()), index=1, key="target_lang_select")

    st.sidebar.markdown("---")

    # Display existing chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user" and "source_lang" in message and "target_lang" in message:
                st.markdown(f"**From {message['source_lang']} to {message['target_lang']}**")
                st.markdown(message["content"])
            else:
                st.markdown(message["content"])

    # Chat input for new messages
    if prompt := st.chat_input("Type text to translate...", key="chat_input_text"):
        # Add user message to chat history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "source_lang": source_language,
            "target_lang": target_language
        })

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(f"**From {source_language} to {target_language}**")
            st.markdown(prompt)

        with st.spinner(f"Translating from {source_language} to {target_language}..."):
            try:
                translation_prompt = f"Translate the following {source_language} text to {target_language}: \"{prompt}\""
                response = gemini_model.generate_content(translation_prompt) # Use gemini_model
                translated_text = response.text

                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": translated_text})

                # Display assistant response
                with st.chat_message("assistant"):
                    st.markdown(translated_text)

            except Exception as e:
                error_message = f"An error occurred during translation: {e}"
                st.error(error_message)
                st.info("Please try again or check your API key/network connection. Quota limits might also apply.")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {error_message}"})

    st.markdown("---")

    # Clear chat history button
    if st.button("Clear Chat", help="Clear all messages from the conversation history"):
        st.session_state.messages = []
        st.session_state.messages.append({"role": "assistant", "content": "Chat cleared! How can I help you now?"})
        st.rerun()

    st.caption("Disclaimer: Translations are generated by AI and may not always be perfectly accurate. This is a demo app.")

else:
    # --- Login/Registration UI ---
    st.title("Welcome to the AI Language Translator!")
    st.subheader("Please Login or Register to continue.")

    # Tabs for Login and Register
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        st.subheader("Login")
        with st.form("login_form", clear_on_submit=False):
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            login_button = st.form_submit_button("Login")

            if login_button:
                if login_email and login_password:
                    user_data = login_user(login_email, login_password)
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.user_info = user_data
                        st.success("Logged in successfully!")
                        st.rerun() # Rerun to switch to translator UI
                else:
                    st.warning("Please enter both email and password.")

    with register_tab:
        st.subheader("Register")
        with st.form("register_form", clear_on_submit=False):
            register_email = st.text_input("Email", key="register_email")
            register_password = st.text_input("Password", type="password", key="register_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            register_button = st.form_submit_button("Register")

            if register_button:
                if register_email and register_password and confirm_password:
                    if register_password == confirm_password:
                        # Firebase requires passwords to be at least 6 characters
                        if len(register_password) >= 6:
                            user_data = signup_user(register_email, register_password)
                            if user_data:
                                st.success("Registration successful! You can now log in.")
                                # Optionally log in the user immediately after registration
                                # st.session_state.logged_in = True
                                # st.session_state.user_info = user_data
                                # st.rerun()
                        else:
                            st.error("Password must be at least 6 characters long.")
                    else:
                        st.error("Passwords do not match.")
                else:
                    st.warning("Please fill in all fields.")

st.markdown("---")
st.caption("Developed with Streamlit, Google Gemini, and Firebase.")