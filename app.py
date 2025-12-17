import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# === 1. ตั้งค่าหน้าเว็บ ===
st.set_page_config(page_title="BlockScam V4.2", page_icon="🛡️")
st.image("https://cdn-icons-png.flaticon.com/512/9529/9529452.png", width=80)
st.title("🛡️ BlockScam V4.2 (Final Fix)")
st.write("ระบบตรวจสอบภัยไซเบอร์ (Auto-Model + Database)")

# === 2. ฟังก์ชันค้นหาโมเดล AI อัตโนมัติ (เอาอันที่เคย Work กลับมา!) ===
def get_ai_model():
    try:
        # วนหาโมเดลที่มีอยู่จริงในเครื่อง
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # ถ้าเจอชื่อที่มีคำว่า flash หรือ pro ให้เอาตัวนั้นเลย
                if 'flash' in m.name or 'pro' in m.name:
                    return genai.GenerativeModel(m.name)
        # ถ้าหาไม่เจอจริงๆ ให้ลองเสี่ยงดวงกับ gemini-pro
        return genai.GenerativeModel('gemini-pro')
    except:
        return None

# === 3. ฟังก์ชันเชื่อมต่อ Google Sheet ===
def get_sheet_connection():
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
            return None

        client = gspread.authorize(creds)
        try:
            return client.open("BlockScam_Data").worksheet("Logs")
        except:
            sheet_id = "1H3IC-sDGa4f2TebGTxOsc3WI_p0RNJPgEwckxgBniD4" 
            return client.open_by_key(sheet_id).worksheet("Logs")
    except Exception as e:
        return None

# === 4. ฟังก์ชันบันทึกข้อมูล (Write) ===
def save_to_sheet(col1, col2, col3):
    try:
        sheet = get_sheet_connection()
        if sheet:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, col1, col2, col3])
            return True
        return False
    except:
        return True

# === 5. ฟังก์ชันตรวจสอบเบอร์จากฐานข้อมูล (Read) ===
def check_blacklist(phone_number):
    try:
        sheet = get_sheet_connection()
        if sheet:
            all_phones = sheet.col_values(2) 
            if phone_number in all_phones:
                return True
        return False
    except:
        return False

# === ตั้งค่า AI Key ===
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# === เมนูหลัก ===
menu = st.sidebar.radio("เลือกเมนูใช้งาน:", ["🔍 เช็กเบอร์โทร", "💬 สแกนแชต (AI)", "🔗 สแกนลิงก์ (AI)", "📢 รายงานเบอร์โจร"])

# ฟีเจอร์ 1: เช็กเบอร์
if menu == "🔍 เช็กเบอร์โทร":
    st.header("🔍 ตรวจสอบเบอร์โทรศัพท์")
    phone = st.text_input("กรอกเบอร์ที่โทรมา:", placeholder="081xxxxxxx")
    
    if st.button("ตรวจสอบ"):
        if phone:
            with st.spinner("กำลังค้นหาในฐานข้อมูล..."):
                is_blacklisted = check_blacklist(phone)
                
                risk = ""
                if is_blacklisted:
                    st.error(f"🚨 อันตราย! เบอร์ {phone} มีประวัติในระบบ")
                    risk = "อันตราย (พบในฐานข้อมูล)"
                else:
                    if phone.startswith("06") or len(phone) > 10:
                        st.warning(f"⚠️ มีความเสี่ยง (เบอร์แปลก)")
                        risk = "เบอร์แปลก"
                    else:
                        st.success(f"✅ ปลอดภัย")
                        risk = "ไม่พบประวัติ"
                save_to_sheet(phone, risk, "User Checked")

# ฟีเจอร์ 2: สแกนแชต (AI)
elif menu == "💬 สแกนแชต (AI)":
    st.header("💬 วิเคราะห์แชต")
    chat = st.text_area("วางแชตที่นี่:")
    
    if st.button("วิเคราะห์"):
        if chat:
            with st.spinner("🤖 AI กำลังคิด..."):
                try:
                    # ใช้ฟังก์ชัน get_ai_model() ตัวเดิมที่เคย Work!
                    model = get_ai_model()
                    if model:
                        res = model.generate_content(f"วิเคราะห์ข้อความนี้ว่าเป็นมิจฉาชีพไหม: '{chat}' ตอบสั้นๆ")
                        st.write(res.text)
                        save_to_sheet("Chat", "AI Scan", chat[:30])
                    else:
                        st.error("ไม่พบโมเดล AI")
                except Exception as e:
                    if "429" in str(e) or "ResourceExhausted" in str(e):
                        st.warning("🚦 AI ทำงานหนักเกินไป กรุณารอสักครู่")
                    else:
                        st.error(f"ระบบขัดข้อง: {e}")

# ฟีเจอร์ 3: สแกนลิงก์ (AI)
elif menu == "🔗 สแกนลิงก์ (AI)":
    st.header("🔗 สแกนลิงก์")
    url = st.text_input("วางลิงก์ (URL):")
    if st.button("สแกน"):
        if url:
            with st.spinner("🔍 กำลังส่อง..."):
                try:
                    model = get_ai_model()
                    if model:
                        safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
                        res = model.generate_content(f"วิเคราะห์ URL นี้ว่าอันตรายไหม: '{url}' ตอบสั้นๆ", safety_settings=safety)
                        st.write(res.text)
                        save_to_sheet(url, "Link Scan", res.text[:30])
                except Exception as e:
                    st.error(f"Error: {e}")

# ฟีเจอร์ 4: รายงานเบอร์
elif menu == "📢 รายงานเบอร์โจร":
    st.header("📢 แจ้งเบาะแส")
    st.info("แจ้งเบอร์มิจฉาชีพเพื่อเตือนภัยเพื่อนๆ")
    p = st.text_input("เบอร์โจร:")
    d = st.text_area("รายละเอียด:")
    if st.button("ส่ง"):
        if p and d:
            if save_to_sheet(p, "User Reported (Blacklist)", d):
                st.balloons()
                st.success(f"✅ บันทึกแล้ว!")
