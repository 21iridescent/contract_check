import streamlit as st
import pandas as pd
import time
import random
import fitz  # PyMuPDF
from openai import OpenAI
import os
from openai import OpenAI
from os import getenv
import io

# 设置页面标题
st.set_page_config(
    page_title="My Streamlit App",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

# Custom CSS to improve the visual aspect and change fonts
st.markdown(
    """
    <style>
    .reportview-container {
        background-color: white;
        color: #000000;  /* Black color for text */
    }
    .sidebar .sidebar-content {
        background-color: #F2F2F7;  /* Light gray for sidebar */
    }
    .stButton>button {
        color: white;
        background-color: #007AFF;  /* Apple blue for buttons */
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
        font-weight: 500;
        border-radius: 8px;
        padding: 10px 20px;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .stTextInput>div>div>input {
        border: 1px solid #007AFF;
        border-radius: 8px;
    }
    .stFileUploader>div>div>input {
        border: 1px solid #007AFF;
        border-radius: 8px;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
        font-weight: 600;
        color: #007AFF;  /* Change this to your desired color */
    }
    h1 {
        font-size: 2.5em;
    }
    h2 {
        font-size: 2em;
    }
    .expander-pass {
        background-color: #E8F5E9;
        color: #1E8E3E;
    }
    .expander-fail {
        background-color: #FFEBEE;
        color: #D32F2F;
    }
    .stTabs [role="tab"] {
        font-size: 1em;
        border: none;
        padding: 12px 24px;
        margin-right: 8px;
        border-radius: 20px;
        color: #007AFF;
        background-color: #F2F2F7;
        transition: all 0.3s ease;
    }
    .stTabs [role="tab"]:hover {
        background-color: #E5E5EA;
    }
    .stTabs [aria-selected="true"] {
        background-color: #007AFF;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    ::selection {
        background-color: #007AFF;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)



# 初始化 session state
if 'review_points' not in st.session_state:
    st.session_state.review_points = pd.DataFrame(
        [
            {"审查点名称": "审查点1", "审查描述": "描述1", "审查要点": "要点1", "备注": "备注1"}
        ]
    )

if 'review_results' not in st.session_state:
    st.session_state.review_results = []
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "审查要点"
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

# 标题
st.title("文档审查", help="欢迎使用文档审查工具")
st.markdown("""
    <style>
        .stTitle {
            color: #007AFF;
        }
    </style>
    """, unsafe_allow_html=True)
# API Key 输入
st.session_state.api_key = st.text_input("请输入 API Key", value=st.session_state.api_key, type="password")

# 验证 API Key
if st.session_state.api_key:
    # 设置环境变量
    os.environ['OPENROUTER_API_KEY'] = st.session_state.api_key
    
    # Initialize OpenAI client with OpenRouter API
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    
else:
    st.warning("请输入有效的 API Key")

# 模型选择
model_options = {
    "Claude 3 Haiku": "anthropic/claude-3-haiku:beta",
    "Claude 3.5 Sonnet": "anthropic/claude-3.5-sonnet",
    "GPT-4": "openai/gpt-4",
    "GPT-4 Turbo": "openai/gpt-4-turbo",
    "Qwen2-72b-instruct": "qwen/qwen-2-72b-instruct",

}
selected_model = st.selectbox("选择模型", list(model_options.keys()))
model = model_options[selected_model]

# 文件上传
uploaded_file = st.file_uploader("请选择一个PDF文件上传", type="pdf")

def extract_text_from_pdf(file):
    pdf_document = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text += page.get_text()
    return text

if uploaded_file is not None:
    st.write(f"已上传文件: {uploaded_file.name}")
    #st.write("文件已成功上传，准备审查。")
    pdf_text = extract_text_from_pdf(uploaded_file)

# 创建标签页
tabs = st.tabs(["审查要点", "审查结果"])
tab1, tab2 = tabs[0], tabs[1]

def generate_prompt(review_point, contract_content):
    #review_point = review_point[0]
    xml_template = f"""
    <role>
你是一名专业的中国合同律师，你的任务是按照我给出的审查要点，审查合同文书或者协议，并根据中国法律和商业惯例提供专业意见。
</role>

<instructions>
1. 审查要点(你应当参照这个思路来完成审查)：
   <review_criteria>
      <name>{review_point[0]}</name>
      <rules>{review_point[1]}</rules>
      <notes>{review_point[2]}</notes>
      <other information>{review_point[3]}</other information>
   </review_criteria>

2. 额外指示：
   - 请确保您的回答符合中国最新的法律法规和商业惯例。
   - 如果合同中存在任何潜在的法律风险或不明确之处，请特别指出并提供相应的改进建议。
   - 在提供修改建议时，请考虑平衡双方利益，特别是要保护披露方的权益。
   - 如果在"条款修改建议"中，没有"原文": "原始条款内容" 或者 "修改建议": "建议修改后的条款内容"，请输出暂无。
   -  <important>你的输出请严格遵循标准的 JSON 格式，不要输出任何其他文字或符号。</important>

3. 最终输出格式(请严格遵循)：
   {{
     "审查要点": "要点名称",
     "具体理由": "简要说明理由",
     "专业意见": "提供改进建议或专业观点",
     "条款修改建议": {{
       "原文": "原始条款内容",
       "修改建议": "建议修改后的条款内容"
     }},
     "审查结果": "通过/未通过"
   }}
</instructions>

<contract>
以下是合同：
{contract_content}
</contract>
    """
    return xml_template

import json

def fake_api_call(review_point, pdf_text, test_mode=False, model=model, api_key=st.session_state.api_key):
    if test_mode:
        return {
            "审查要点": "很重要的一个要点",
            "具体理由": "这是测试模式下的具体理由",
            "专业意见": "这是测试模式下的专业意见",
            "条款修改建议": {"原文": "这是测试模式下的原文", "修改建议": "这是测试模式下的修改建议"},
            "审查结果": "通过" if random.choice([True, False]) else "不通过"
        }

    input_prompt = generate_prompt(review_point, pdf_text)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": input_prompt,
            },
        ],
    )
    response_content = completion.choices[0].message.content

    try:
        response_json = json.loads(response_content)
        result = {
            "审查要点": response_json.get("审查要点", review_point[0]),
            "具体理由": response_json.get("具体理由", "无具体理由"),
            "专业意见": response_json.get("专业意见", "无专业意见"),
            "条款修改建议": response_json.get("条款修改建议", {"原文": "无原文", "修改建议": "无修改建议"}),
            "审查结果": response_json.get("审查结果", "不通过")
        }
    except json.JSONDecodeError:
        import re
        try:
            # Try to extract JSON-like content using regex
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                response_json = json.loads(json_match.group())
                result = {
                    "审查要点": response_json.get("审查要点", review_point[0]),
                    "具体理由": response_json.get("具体理由", "无具体理由"),
                    "专业意见": response_json.get("专业意见", "无专业意见"),
                    "条款修改建议": response_json.get("条款修改建议", {"原文": "无原文", "修改建议": "无修改建议"}),
                    "审查结果": response_json.get("审查结果", "不通过")
                }
            else:
                raise ValueError("No JSON-like content found")
        except (json.JSONDecodeError, ValueError):
            result = {
                "审查要点": review_point[0],
                "具体理由": "无法解析的响应内容",
                "专业意见": "改进建议",
                "条款修改建议": {"原文": "无原文", "修改建议": "无修改建议"},
                "审查结果": "不通过"
            }

    return result

with tab1:
    edited_df = st.data_editor(
        st.session_state.review_points,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )

    # Ensure the DataFrame structure remains fixed
    if not edited_df.equals(st.session_state.review_points):
        edited_df = edited_df.reindex(columns=st.session_state.review_points.columns)

    st.session_state.review_points = edited_df

    if st.button("审查"):
        if uploaded_file is None:
            st.error("请先上传PDF文件")
        elif not st.session_state.api_key:
            st.error("请输入 API Key")
        else:
            st.session_state.review_results = []
            review_points_list = [list(review_point) for _, review_point in edited_df.iterrows()]
            for review_point in review_points_list:
                with st.spinner(f"正在审查 {review_point[0]}..."):
                    #print(review_points_list)
                    #print("-----------------")
                    #print(review_point)
                    #print(len(review_points_list))
                    result = fake_api_call(review_point, pdf_text, test_mode=False, model=model)
                    st.session_state.review_results.append(result)
                    st.success(f"{review_point[0]} 审查完成")
            st.session_state.current_tab = "审查结果"
            
            st.info('审查完成，切换到审查结果查看')


with tab2:
    if st.session_state.review_results:
        for result in st.session_state.review_results:
            status_class = "expander-pass" if result['审查结果'] == "通过" else "expander-fail"
            with st.expander(f"{result['审查要点']} - {result['审查结果']}", expanded=True):
                st.markdown(f"""
                <div class='{status_class}'>
                    <strong>审查结果:</strong> {result['审查结果']}<br>
                    <strong>具体理由:</strong> {result['具体理由']}<br>
                    <strong>专业意见:</strong> {result['专业意见']}<br>
                    <strong>条款修改建议:</strong> 原文: {result['条款修改建议']['原文']}, 修改建议: {result['条款修改建议']['修改建议']}
                </div>
                """, unsafe_allow_html=True)
        
        # Create a DataFrame from the review results
        df = pd.DataFrame(st.session_state.review_results)
        
        # Convert the DataFrame to an Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='审查结果')
        
        # Generate a timestamp for the filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        
        # Create a download button
        st.download_button(
            label="下载审查结果",
            data=output.getvalue(),
            file_name=f"审查结果_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("暂无审查结果，请先进行审查")
