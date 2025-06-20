import streamlit as st
import os
import io
import json
import zipfile
import tempfile
from PyPDF2 import PdfReader
import google.generativeai as genai

# ========== API 설정 ==========
genai.configure(api_key="AIzaSyA3vGCeQzNDsBvXjO32ZHYB8Sy3CHqAd-0")
model = genai.GenerativeModel("gemini-1.5-flash")

# ========== UI 타이틀 ==========
st.title("📚 멀티 포맷 논문 분석 시스템")

# ========== 파일 업로더 ==========
uploaded = st.file_uploader(
    label="PDF, TXT, JSON 파일 혹은 JSON이 담긴 ZIP 파일을 업로드하세요",
    type=["pdf", "txt", "json", "zip"],
    accept_multiple_files=True
)

question = st.text_input("AI에게 물어볼 질문을 입력하세요:")
ask = st.button("질문하기")

if uploaded and question and ask:
    try:
        context_list = []

        def process_json_stream(stream):
            text = stream.read().decode("utf-8")
            data = json.loads(text)
            sections = data.get("packages", {}).get("gpt", {}).get("sections", {})
            return (
                f"📄 제목: {sections.get('title','')}\n"
                f"[초록]\n{sections.get('abstract','')}\n"
                f"[방법론]\n{sections.get('methodology','')}\n"
                f"[결과]\n{sections.get('results','')}\n"
            )

        def process_txt_stream(stream):
            return f"📄 텍스트 파일 내용:\n{stream.read().decode('utf-8')}\n"

        def process_pdf_stream(stream):
            reader = PdfReader(stream)
            pages = [p.extract_text() or "" for p in reader.pages]
            return "📄 PDF 파일 내용:\n" + "\n---\n".join(pages) + "\n"

        # 업로드된 각 파일 처리
        for uploaded_file in uploaded:
            name = uploaded_file.name.lower()

            if name.endswith(".zip"):
                # ZIP 내부 파일들 처리
                with tempfile.TemporaryDirectory() as tmpdir:
                    z = zipfile.ZipFile(io.BytesIO(uploaded_file.read()))
                    z.extractall(tmpdir)
                    for root, _, files in os.walk(tmpdir):
                        for fn in files:
                            path = os.path.join(root, fn.lower())
                            with open(os.path.join(root, fn), "rb") as f:
                                if fn.endswith(".json"):
                                    context_list.append(process_json_stream(f))
                                elif fn.endswith(".txt"):
                                    context_list.append(process_txt_stream(f))
                                elif fn.endswith(".pdf"):
                                    context_list.append(process_pdf_stream(f))

            else:
                # 직접 업로드된 JSON, TXT, PDF 파일 처리
                bytestream = uploaded_file.read()
                stream = io.BytesIO(bytestream)
                if name.endswith(".json"):
                    context_list.append(process_json_stream(stream))
                elif name.endswith(".txt"):
                    context_list.append(process_txt_stream(stream))
                elif name.endswith(".pdf"):
                    context_list.append(process_pdf_stream(stream))

        if not context_list:
            st.error("유효한 파일이 없습니다. PDF, TXT, JSON 또는 ZIP 안의 JSON/TXT/PDF를 업로드해주세요.")
        else:
            # 전체 컨텍스트 합치기
            full_context = "\n\n===\n\n".join(context_list)

            # AI에 보낼 프롬프트 구성
            prompt = f"""
다음은 업로드된 파일들에서 추출한 핵심 내용입니다. 이 내용을 바탕으로 아래 질문에 답해주세요.

{full_context}

[질문]
{question}
"""

            # AI 호출 및 출력
            response = model.generate_content(prompt)
            st.subheader("🧠 AI의 응답:")
            st.write(response.text)

    except Exception as e:
        st.error(f"오류 발생: {e}")
