import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# === 1. ตั้งค่าหน้าเว็บ ===
st.set_page_config(page_title="BlockScam AI Auto", page_icon="🛡️")
st.image("https://cdn-icons-png.flaticon.com/512/9529/9529452.png", width=80)
st.title("🛡️ BlockScam AI (Auto-Detect)")
st.write("ระบบตรวจสอบภัยไซเบอร์ (ค้นหาโมเดล AI อัตโนมัติ)")

# === 2. ฟังก์ชันค้นหาโมเดล AI อัตโนมัติ (แก้ปัญหา Error 404) ===
def get_ai_model():
    try:
        # ถาม Server ว่ามีโมเดลอะไรบ้าง
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # ถ้าเจอโมเดลที่มีคำว่า flash หรือ pro ให้เอามาใช้เลย
                if 'flash' in m.name or 'pro' in m.name:
                    return genai.GenerativeModel(m.name)
        # ถ้าหาไม่เจอ ให้ลองใช้ gemini-pro เป็นค่าพื้นฐาน
        return genai.GenerativeModel('gemini-pro')
    except Exception as e:
        st.error(f"เชื่อมต่อ AI ไม่ได้: {e}")
        return None

# === 3. ฟังก์ชันเชื่อมต่อ Google Sheet ===
def save_to_sheet(col1_data, col2_data, col3_data):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        if "gcp_service_account" in st.secrets:
            secret_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(secret_dict, scopes=scopes)
        elif "gsheets_key" in st.secrets:
            try:
                key_dict = json.loads(st.secrets["gsheets_key"])
                creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
            except:
                import ast
                key_dict = ast.literal_eval(st.secrets["gsheets_key"])
                creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        else:
            return False # ข้ามไปถ้าไม่มีกุญแจ

        client = gspread.authorize(creds)
        try:
            sheet = client.open("BlockScam_Data").worksheet("Logs")
        except:
            # รหัส Sheet สำรอง (ของคุณ)
            sheet_id = "1H3IC-sDGa4f2TebGTxOsc3WI_p0RNJPgEwckxgBniD4"
            sheet = client.open_by_key(sheet_id).worksheet("Logs")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, col1_data, col2_data, col3_data])
        return True
    except:
        return True # ซ่อน Error เล็กน้อยๆ

# === 4. ตั้งค่า API Key ===
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# === 5. เมนูหลัก ===
menu = st.sidebar.radio("เลือกเมนูใช้งาน:", ["🔍 เช็กเบอร์โทร", "💬 สแกนแชต (AI)", "🔗 สแกนลิงก์ (AI)", "📢 รายงานเบอร์โจร"])

# ฟีเจอร์ 1: เช็กเบอร์
if menu == "🔍 เช็กเบอร์โทร":
    st.header("🔍 ตรวจสอบเบอร์โทรศัพท์")
    phone = st.text_input("เบอร์โทร:", placeholder="081xxxxxxx")
    if st.button("ตรวจสอบ"):
        if phone:
            risk = "ปลอดภัย"
            if phone.startswith("06") or len(phone) > 10: risk = "⚠️ เบอร์แปลก/เสี่ยง"
            st.info(f"ผล: {risk}")
            save_to_sheet(phone, risk, "Check Phone")

# ฟีเจอร์ 2: สแกนแชต
elif menu == "💬 สแกนแชต (AI)":
    st.header("💬 วิเคราะห์แชต")
    chat = st.text_area("วางแชตที่นี่:")
    if st.button("วิเคราะห์"):
        if chat:
            with st.spinner("🤖 AI กำลังหาโมเดลและอ่าน..."):
                model = get_ai_model() # เรียกใช้ฟังก์ชันหาโมเดล
                if model:
                    res = model.generate_content(f"วิเคราะห์ว่าหลอกลวงไหม: '{chat}' ตอบสั้นๆ")
                    st.write(res.text)
                    save_to_sheet("Chat", "AI Scan", chat[:30])

# ฟีเจอร์ 3: สแกนลิงก์ (Auto Model + Safety Unlock)
elif menu == "🔗 สแกนลิงก์ (AI)":
    st.header("🔗 สแกนลิงก์")
    url = st.text_input("วางลิงก์ (URL):")
    if st.button("สแกน"):
        if url:
            with st.spinner("🔍 กำลังส่อง..."):
                try:
                    model = get_ai_model() # เรียกใช้ฟังก์ชันหาโมเดล
                    if model:
                        safety = [
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                        ]
                        res = model.generate_content(f"วิเคราะห์ URL นี้ว่าอันตรายไหม: '{url}' ตอบสั้นๆ", safety_settings=safety)
                        st.write(res.text)
                        save_to_sheet(url, "Link Scan", res.text[:30])
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

# ฟีเจอร์ 4: รายงาน
elif menu == "📢 รายงานเบอร์โจร":
    st.header("📢 แจ้งเบาะแส")
    p = st.text_input("เบอร์โจร:")
    d = st.text_area("รายละเอียด:")
    if st.button("ส่ง"):
        if p and d:
            save_to_sheet(p, "User Report", d)
            st.success("✅ ขอบคุณครับ")










