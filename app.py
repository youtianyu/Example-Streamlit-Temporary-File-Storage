import streamlit as st
import os
import json
import random
import string
import time
import shutil
import zipfile
import io

# 设置页面标题和布局
st.set_page_config(page_title="文件临时存储系统", layout="wide")

# 初始化session_state
if 'upload_success' not in st.session_state:
    st.session_state.upload_success = False
if 'retrieval_success' not in st.session_state:
    st.session_state.retrieval_success = False
if 'retrieval_code' not in st.session_state:
    st.session_state.retrieval_code = ""
if 'error_message' not in st.session_state:
    st.session_state.error_message = ""

# 确保data文件夹存在
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 生成取件码函数
def generate_code():
    # 获取总存储次数
    storage_count = len([d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]) + 1
    # 生成四位随机数
    random_digits = ''.join(random.choices(string.digits, k=4))
    # 组合成取件码
    return f"{storage_count}{random_digits}"

# 清理过期文件函数
def clean_expired_files():
    current_time = int(time.time())
    for folder in os.listdir(DATA_DIR):
        folder_path = os.path.join(DATA_DIR, folder)
        if os.path.isdir(folder_path):
            try:
                # 从文件夹名称中提取到期时间
                parts = folder.split('_')
                if len(parts) >= 3:
                    expiry_time = int(parts[2])
                    if current_time > expiry_time:
                        shutil.rmtree(folder_path)
                        print(f"已删除过期文件夹: {folder}")
            except Exception as e:
                print(f"清理过期文件时出错: {e}")

# 保存上传的内容
def save_upload(text, files, expiry_hours):
    # 生成取件码
    code = generate_code()
    # 计算当前时间和到期时间
    current_time = int(time.time())
    expiry_time = current_time + int(expiry_hours) * 3600
    
    # 创建存储文件夹
    folder_name = f"{code}_{current_time}_{expiry_time}"
    folder_path = os.path.join(DATA_DIR, folder_name)
    files_path = os.path.join(folder_path, "files")
    
    os.makedirs(folder_path, exist_ok=True)
    os.makedirs(files_path, exist_ok=True)
    
    # 保存文字内容
    if text:
        with open(os.path.join(folder_path, "text.json"), "w", encoding="utf-8") as f:
            json.dump({"text": text}, f, ensure_ascii=False)
    
    # 保存文件
    if files:
        for file in files:
            file_path = os.path.join(files_path, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
    
    return code

# 根据取件码获取内容
def retrieve_by_code(code):
    # 清理过期文件
    clean_expired_files()
    
    # 查找对应的文件夹
    for folder in os.listdir(DATA_DIR):
        if folder.startswith(code + "_") and os.path.isdir(os.path.join(DATA_DIR, folder)):
            folder_path = os.path.join(DATA_DIR, folder)
            files_path = os.path.join(folder_path, "files")
            
            # 获取文字内容
            text = ""
            text_file = os.path.join(folder_path, "text.json")
            if os.path.exists(text_file):
                with open(text_file, "r", encoding="utf-8") as f:
                    try:
                        text_data = json.load(f)
                        text = text_data.get("text", "")
                    except:
                        text = "文本内容解析错误"
            
            # 获取文件列表
            files = []
            if os.path.exists(files_path):
                files = [f for f in os.listdir(files_path) if os.path.isfile(os.path.join(files_path, f))]
            
            # 提取到期时间
            parts = folder.split('_')
            expiry_time = int(parts[2]) if len(parts) >= 3 else 0
            current_time = int(time.time())
            remaining_time = max(0, expiry_time - current_time)
            
            return {
                "found": True,
                "text": text,
                "files": files,
                "folder_path": folder_path,
                "files_path": files_path,
                "remaining_hours": round(remaining_time / 3600, 1)
            }
    
    return {"found": False}

# 创建ZIP文件并返回下载链接
def create_zip_download(folder_path, files_path):
    # 创建一个内存中的ZIP文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 添加文本文件
        text_file = os.path.join(folder_path, "text.json")
        if os.path.exists(text_file):
            with open(text_file, "r", encoding="utf-8") as f:
                try:
                    text_data = json.load(f)
                    text = text_data.get("text", "")
                    if text:
                        zip_file.writestr("文本内容.txt", text)
                except:
                    pass
        
        # 添加其他文件
        if os.path.exists(files_path):
            for file in os.listdir(files_path):
                file_path = os.path.join(files_path, file)
                if os.path.isfile(file_path):
                    zip_file.write(file_path, file)
    
    # 重置缓冲区位置
    zip_buffer.seek(0)
    return zip_buffer

# 主界面
st.title("📦 文件临时存储系统")

# 创建两个选项卡
tab1, tab2 = st.tabs(["📤 存储文件", "📥 取回文件"])

# 存储文件选项卡
with tab1:
    
    # 文件上传区域
    uploaded_files = st.file_uploader("选择要上传的文件（可选）", accept_multiple_files=True)
    
    # 文字输入区域
    text_input = st.text_area("输入要存储的文字（可选）", height=150)
    
    # 存储时间选择
    col1, col2 = st.columns([1, 2])
    with col1:
        expiry_hours = st.number_input("存储时间（小时）", min_value=1, max_value=168, value=24)
    
    # 提交按钮
    if st.button("生成取件码"):
        if not text_input and not uploaded_files:
            st.error("请至少输入文字或上传文件！")
        else:
            # 保存上传的内容并获取取件码
            code = save_upload(text_input, uploaded_files, expiry_hours)
            st.session_state.upload_success = True
            st.session_state.retrieval_code = code
    
    # 显示上传成功信息和取件码
    if st.session_state.upload_success:
        # 计算具体到期时间
        expiry_timestamp = int(time.time()) + expiry_hours * 3600
        expiry_datetime = time.strftime("%Y年%m月%d日%H时%M分", time.localtime(expiry_timestamp))
        st.info(f"上传成功！您的取件码是：{st.session_state.retrieval_code}；到期时间：{expiry_datetime}")

# 取回文件选项卡
with tab2:
    # 取件码输入
    col1, col2 = st.columns([1, 3])
    with col1:
        retrieval_code = st.text_input("请输入取件码")
    
    # 查询按钮
    if st.button("查询"):
        if not retrieval_code:
            st.error("请输入取件码！")
        else:
            # 根据取件码获取内容
            result = retrieve_by_code(retrieval_code)
            if result["found"]:
                st.session_state.retrieval_success = True
                st.session_state.retrieval_result = result
            else:
                st.error("未找到对应的文件或取件码已过期！")
    
    # 显示查询结果
    if st.session_state.retrieval_success and hasattr(st.session_state, 'retrieval_result'):
        result = st.session_state.retrieval_result
        

        
        # 显示文字内容
        if result["text"]:
            st.subheader("文字内容")
            st.code(result["text"], language="text")
        
        # 显示文件列表
        if result["files"]:
            col1, col2,_ = st.columns([1, 1,5])
            with col1:
                st.subheader("文件列表")
            with col2:
                # 打包下载按钮
                if result["text"] or result["files"]:
                    zip_buffer = create_zip_download(result["folder_path"], result["files_path"])
                    st.download_button(
                        label="打包下载全部内容",
                        data=zip_buffer,
                        file_name="取件内容.zip",
                        mime="application/zip"
                    )
            
            # 显示文件下载按钮
            for file in result["files"]:
                file_path = os.path.join(result["files_path"], file)
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"下载 {file}",
                        data=f,
                        file_name=file,
                        mime="application/octet-stream"
                    )
        
        # 显示剩余时间（移至最后）
        st.info(f"文件将在 {result['remaining_hours']} 小时后过期")

# 页脚
st.markdown("---")
st.markdown("### 📦 文件临时存储系统 | 安全、便捷、高效")