import os
import time
import streamlit as st
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_community.document_loaders import PyPDFLoader

# ----------------- 0. 动态路径获取 (本地与云端自适应核心) -----------------
# 自动获取当前 web_ui.py 所在的文件夹目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ----------------- 1. 环境自适应配置 -----------------
st.set_page_config(page_title="波音 OPT 全局智能专家", page_icon="✈️", layout="wide")


# ----------------- 🔒 驾驶舱密码门 (全局使用授权) -----------------
def check_password():
    """核对全局授权码"""

    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 请输入系统接入授权码：", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 请输入系统接入授权码：", type="password", on_change=password_entered, key="password")
        st.error("❌ 授权码错误，拒绝接入数据链！")
        return False
    else:
        return True


if not check_password():
    st.stop()


# ----------------- 2. 核心大模型链路 (长文本缓存模式) -----------------
@st.cache_resource
def load_full_document():
    """读取保存在本地的完整手册纯文本"""
    # 🚨 动态拼接路径：无论是 Windows 还是 Linux 都能精准定位
    doc_path = os.path.join(BASE_DIR, "docs", "opt_full_manual.txt")
    if os.path.exists(doc_path):
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def get_chat_chain():
    # 🧠 大脑连接 (直连 DeepSeek，利用其强大的长文本和自动缓存能力)
    MY_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
    llm = ChatOpenAI(model="deepseek-chat", api_key=MY_API_KEY, base_url="https://api.deepseek.com", temperature=0.1)

    # 🗣️ 专属 Prompt：直接携带完整书籍的上帝视角
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("""你是一个专业的波音 OPT (Onboard Performance Tool) 软件支持专家与系统管理员。
        我已经把一整本《波音 OPT 管理员指南》完整地提供给你了。请你利用你的全局视野，精准解答机长的问题。

        【🚨 核心要求】：
        1. 全局整合：你可以自由跨章节联系上下文，给出最完整的答案。
        2. 操作步骤：如果是安装、配置或排错，请务必使用有序列表 (1, 2, 3) 清晰输出。
        3. 代码规范：涉及 XML 文件配置或系统路径，必须使用 Markdown 代码块包裹。
        4. 严守边界：所有的回答必须严格基于我提供给你的这本手册。如果手册里确实没写，请直接回答“这本手册中未提供相关信息”，绝不允许凭空编造。

        【📚 完整的 OPT 管理员指南内容如下】：
        {document}
        """),
        HumanMessagePromptTemplate.from_template("{input}")
    ])

    return prompt | llm


# ----------------- 3. 极简的解析逻辑 (整书提取) -----------------
def process_new_pdf(uploaded_file):
    # 保存临时 PDF
    safe_name = f"{int(time.time())}_{uploaded_file.name}"
    # 🚨 动态拼接存储路径
    temp_dir = os.path.join(BASE_DIR, "docs")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, safe_name)

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # 暴力提取整书文本
    loader = PyPDFLoader(temp_path)
    pages = loader.load()

    # 将所有页面拼接成一个超级巨大的字符串
    full_text = "\n\n".join([page.page_content for page in pages])

    # 将这本“纯文本巨著”直接存放在本地
    txt_path = os.path.join(temp_dir, "opt_full_manual.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    return len(pages)


# ----------------- 4. 侧边栏与主界面 -----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/books.png", width=60)
    st.title("系统管理控制台")

    st.divider()

    # 🚨 管理员专属权限校验逻辑
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.markdown("### 🔒 底层数据维护")
        admin_pwd = st.text_input("请输入管理员密码解锁上传：", type="password")
        if admin_pwd:
            if admin_pwd == st.secrets.get("ADMIN_PASSWORD", "admin123"):
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("❌ 密码错误，无权操作！")
    else:
        st.markdown("### 🔓 管理员已解锁")
        if st.button("退出管理员模式"):
            st.session_state.admin_authenticated = False
            st.rerun()

        uploaded_file = st.file_uploader("📂 上传波音 OPT Admin Guide 进行全局记忆", type="pdf")
        if uploaded_file is not None:
            if st.button("🚀 开始注入大模型记忆"):
                with st.spinner("正在提取整本书籍并构建全局记忆..."):
                    pages_count = process_new_pdf(uploaded_file)
                    st.success(f"记忆注入成功！共吸收 {pages_count} 页手册内容。")
                    st.cache_resource.clear()
                    st.rerun()

    st.divider()
    st.markdown("### 系统状态")
    st.info("🧠 架构：上帝视角 + 长文本自动缓存\n\n🛡️ 权限：已启用双层安全隔离")

st.title("✈️ 波音 OPT 全局智能专家 (上帝视角版)")

# 尝试加载整本书籍
full_document_text = load_full_document()

if full_document_text is None:
    st.warning("⚠️ 全局记忆为空！请联系管理员在左侧控制台解锁并上传 OPT Admin Guide 进行首次注入。")
else:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant",
             "content": "我已经把整本 OPT 说明书装进脑子里了！随便问，我能联系整本书的上下文回答你。"}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("请输入问题..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("思考全局手册内容中... (首次提问可能需要10-20秒以建立缓存)"):
                try:
                    # 获取聊天链条
                    chain = get_chat_chain()
                    # 传入整书内容和用户问题
                    result = chain.invoke({"document": full_document_text, "input": user_input})

                    st.markdown(result.content)
                    st.session_state.messages.append({"role": "assistant", "content": result.content})
                except Exception as e:
                    st.error(f"❌ 通讯异常: {e}")