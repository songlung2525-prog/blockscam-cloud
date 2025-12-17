import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# === 1. ตั้งค่าหน้าเว็บ ===
st.set_page_config(page_title="BlockScam V4.4 Debug", page_icon="🔧")
st.title("🔧 BlockScam V4.4 (โหมดแก้ปัญหา)")
st.write("เวอร์ชันนี้จะโชว์ชื่อโมเดลและ Error ทั้งหมดเพื่อหาสาเหตุ")

# === 2. ฟังก์ชันเลือกโมเดล (พร้อมตัวแปรบอกชื่อ) ===
def get_ai_model():
    # รายชื่อโมเดลที่อยากได้
    target_models = [
        "gemini-1.5-flash",       # ตัวหลัก
        "gemini-1.5-flash-001",
        "gemini-pro"              # ตัวกันตาย
    ]
    
    try:
        available_models = [m.name.replace("models/", "") for m in genai.list_models()]
        
        # วนหาทีละตัว
        for target in target_models:
            if target in available_models:
                return genai.GenerativeModel(target), target # ส่งคืนทั้งโมเดลและชื่อ
        
        # ถ้าไม่เจอเลย เอาตัวแรกที่มีคำว่า flash
        for m in available_models:
            if "flash" in m:
                return genai.GenerativeModel(m), m
                
        return genai.GenerativeModel('gemini-pro'), "gemini-pro (Fallback)"

    except Exception as e:
        return None, f"Error finding model: {e}"

# === 3. ฟังก์ชันเชื่อมต่อ Google Sheet ===
def get_sheet_connection():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
        elif "gsheets_key" in st.secrets:
            try:
                creds = Credentials.from_service_account_info(json.loads(st.secrets["gsheets_key"]), scopes=scopes)
            except:
                import ast
                creds = Credentials.from_service_account_info(ast.literal_eval(st.secrets["gsheets_key"]), scopes=scopes)
        else:
            return None
        client = gspread.authorize(creds)
        try:
            return client.open("BlockScam_Data").worksheet("Logs")
        except:
            return client.open_by_key("1H3IC-sDGa4f2TebGTxOsc3WI_p0RNJPgEwckxgBniD4").worksheet("Logs")
    except:
        return None

def save_to_sheet(col1, col2, col3):
    try:
        sheet = get_sheet_connection()
        if sheet:
            sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), col1, col2, col3])
    except:
        pass

def check_blacklist(phone):
    try:
        sheet = get_sheet_connection()
        if sheet and phone in sheet.col_values(2): return True
    except:
        pass
    return False

# === ตั้งค่า AI Key ===
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# === เมนูหลัก ===
menu = st.sidebar.radio("เมนู:", ["🔍 เช็กเบอร์โทร", "💬 สแกนแชต", "🔗 สแกนลิงก์", "📢 รายงาน"])

# ฟีเจอร์: สแกนลิงก์ (โหมด Debug)
if menu == "🔗 สแกนลิงก์":
    st.header("🔗 สแกนลิงก์ (Debug)")
    url = st.text_input("URL:")
    if st.button("สแกน"):
        if url:
            with st.spinner("🔍 กำลังทำงาน..."):
                try:
                    # 1. โชว์ชื่อโมเดลก่อนเลย
                    model, model_name = get_ai_model()
                    st.info(f"ℹ️ ระบบกำลังใช้โมเดลชื่อ: **{model_name}**")
                    
                    if "Error" in model_name:
                        st.error(model_name)
                    else:
                        # 2. ลองยิงคำถาม (ไม่ดักจับ Error แล้ว ปล่อยให้มันฟ้องมาเลย)
                        safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
                        res = model.generate_content(f"วิเคราะห์ URL นี้ว่าอันตรายไหม: '{url}' ตอบสั้นๆ", safety_settings=safety)
                        st.success(res.text)
                        save_to_sheet(url, "Link Scan", res.text[:30])
                        
                except Exception as e:
                    # 3. โชว์ Error ตัวเต็ม
                    st.error("🚨 เกิดข้อผิดพลาดจาก Google:")
                    st.code(e) # แสดง Code Error แบบดิบๆ
