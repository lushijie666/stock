import streamlit as st
import hashlib
import time

# 写死的登录密钥
VALID_API_KEY = "123"

# 会话状态键名
SESSION_KEY = "authenticated"
TOKEN_KEY = "auth_token"
TOKEN_EXPIRY = "token_expiry"

# Token有效期（秒）
TOKEN_DURATION = 3600  # 1小时


def generate_token() -> str:
    """生成一个简单的token"""
    return hashlib.sha256(f"{time.time()}{VALID_API_KEY}".encode()).hexdigest()


def check_authentication() -> bool:
    """检查用户是否已认证，支持刷新后保持登录状态"""
    # 首先检查session_state中的认证状态
    if st.session_state.get(SESSION_KEY, False):
        return True
    
    # 如果session_state中没有，尝试从浏览器存储中恢复
    # 使用Streamlit的query_params API作为一种简单的跨刷新持久化方式
    try:
        # 检查URL参数中的token
        query_params = st.query_params.to_dict()
        if TOKEN_KEY in query_params and TOKEN_EXPIRY in query_params:
            token = query_params[TOKEN_KEY]
            expiry = float(query_params[TOKEN_EXPIRY])
            
            # 验证token是否过期
            if time.time() < expiry:
                # 重新设置session_state
                st.session_state[SESSION_KEY] = True
                return True
    except:
        pass
    
    return False


def authenticate(api_key: str) -> bool:
    """验证API密钥并创建持久化token"""
    if api_key == VALID_API_KEY:
        # 设置session_state
        st.session_state[SESSION_KEY] = True
        
        # 生成token和过期时间
        token = generate_token()
        expiry = time.time() + TOKEN_DURATION
        
        # 将token添加到URL参数中以支持刷新后保持登录
        st.query_params.update({
            TOKEN_KEY: token,
            TOKEN_EXPIRY: str(expiry)
        })
        
        return True
    return False


def logout():
    """登出当前用户，清除所有认证状态"""
    # 清除session_state
    if SESSION_KEY in st.session_state:
        del st.session_state[SESSION_KEY]
    
    # 清除URL参数中的token
    st.query_params.clear()


def require_auth() -> bool:
    """检查认证状态，如果未认证则重定向到登录页面"""
    return check_authentication()