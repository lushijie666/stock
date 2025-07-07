import time

import streamlit as st


def show_message(message: str, type: str = "success", duration: int = 2):
    icons = {
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }

    message = message.replace('\n', '<br>')
    icon = icons.get(type, "")

    placeholder = st.empty()
    placeholder.markdown(f"""
        <div class="message-overlay"></div>
        <div class="custom-message-container">
            <div class="custom-message custom-{type}">
                <p class="message-content">
                    <span style="font-size: 1.5rem; margin-right: 0.5rem;">{icon}</span>
                    {message}
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    time.sleep(duration)
    placeholder.empty()
