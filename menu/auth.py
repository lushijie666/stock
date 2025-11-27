import streamlit as st
import time
from utils.auth import authenticate


def login():
    """炫酷的登录页面"""
    st.markdown("""
    <style>  
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
        }
        .stApp {
            background: none;
            max-width: 100%;
            padding: 0;
        }
        /* 表单区域 */
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.75rem 2rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-size: 1rem;
            font-weight: 600;
        }
      
        /* 动画效果 */
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes moveBackground {
            0% {
                transform: translate(0, 0) rotate(0deg);
            }
            100% {
                transform: translate(-50px, -50px) rotate(360deg);
            }
        }
        
        /* 闪烁效果 */
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% {
                opacity: 1;
            }
            50% {
                opacity: 0.7;
            }
            100% {
                opacity: 1;
            }
        }
     
    </style>
    """, unsafe_allow_html=True)
    
    # 登录容器
    st.markdown("""
    <div class="login-container">
        <div class="login-header">
            <h1 class="login-title">💰 股票量化交易</h1>
        </div>
    """, unsafe_allow_html=True)
    
    # API密钥输入框
    api_key = st.text_input(
        "👏",
        type="password",
        placeholder="👏请输入您的密钥",
        key="login_key",
        label_visibility="collapsed"
    )
    
    # 登录按钮
    if st.button("安全登录", use_container_width=True):
        if not api_key:
            st.error("🔒 请输入登录密钥", icon="⚠️")
        elif authenticate(api_key):
            # 登录成功的炫酷效果
            st.success("✅ 登录成功！正在加载系统...", icon="🎉")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ 无效的密钥，请重试", icon="🔒")
    
