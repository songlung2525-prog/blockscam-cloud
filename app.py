import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# === 1. ตั้งค่าหน้าเว็บ ===
st.set_page_config(page_title="BlockScam V4.3", page_icon="🛡️")
st.image("https://cdn-icons-png.flaticon.com/512/9529/9529452.png", width=80)
st.title("🛡️ BlockScam V4.3 (Smart Select)")
st.write("ระบบตรวจสอบภัยไซเบอร์ (Smart Model Selector)")

# === 2. ฟังก์ชันเลือกโมเดล AI (ฉลาดขึ้น เลือกตัวเสถียรก่อน) ===
def get_ai_model():
    # รายชื่อโมเดลที่อยากได้ (เรียงจาก ดีสุด -> เก่าสุด)
    target_models = [
        "gemini-1.5-flash",       # เร็วและโควตาเยอะสุด
        "gemini-1.5-flash-001",   # ชื่อสำรอง 1
        "gemini-1.5-flash-002",   # ชื่อสำรอง 2
        "gemini-1.5-pro",         # ตัวฉลาด (ถ้ามี)
        "gemini-pro"              # ตัวเก่า (กันตาย)
    ]
    
    try:
        # 1. ดึงรายชื่อโมเดลทั้งหมดที่มีในบัญชีของคุณ
        available_models = [m.name.replace("models/", "") for m in genai.list_models()]
        
        # 2. วนเช็กว่าบัญชีคุณมีตัวไหนในรายการ target บ้าง
        for target in target_models:
            if target in available_models:
                return genai.GenerativeModel(target)
        
        # 3. ถ้าไม่ตรงเลย ให้เอาตัวไหนก็ได้ที่มีคำว่า flash
        for m in available_models:
            if "flash" in m:
                return genai.GenerativeModel(m)
                
        # 4. ถ้าไม่มีจริงๆ ใช้ gemini-pro เป็นไม้ตายสุดท้าย
        return genai.GenerativeModel('gemini-pro')

    except Exception as e:
        st.error(f"ระบบค้นหาโมเดลขัดข้อง: {e}")
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
    except:
        return None

# === 4. ฟังก์ชันบันทึกข้อมูล ===
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

# === 5. ฟังก์ชันตรวจสอบเบอร์จากฐานข้อมูล ===
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
            with st.spinner("ค้นหาในฐานข้อมูล..."):
                if check_blacklist(phone):
                    st.error(f"🚨 อันตราย! เบอร์ {phone} มีประวัติในระบบ")
                    save_to_sheet(phone, "อันตราย (Blacklist)", "User Checked")
                else:
                    risk = "เบอร์แปลก" if (phone.startswith("06") or len(phone) > 10) else "ไม่พบประวัติ"
                    if risk == "เบอร์แปลก": st.warning("⚠️ มีความเสี่ยง (เบอร์แปลก)")
                    else: st.success("✅ ปลอดภัย")
                    save_to_sheet(phone, risk, "User Checked")

# ฟีเจอร์ 2: สแกนแชต
elif menu == "💬 สแกนแชต (AI)":
    st.header("💬 วิเคราะห์แชต")
    chat = st.text_area("วางแชตที่นี่:")
    if st.button("วิเคราะห์"):
        if chat:
            with st.spinner("🤖 AI กำลังคิด..."):
                try:
                    model = get_ai_model() # เลือกโมเดลที่ฉลาดขึ้น
                    if model:
                        res = model.generate_content(f"วิเคราะห์ว่าหลอกลวงไหม: '{chat}' ตอบสั้นๆ")
                        st.write(res.text)
                        save_to_sheet("Chat", "AI Scan", chat[:30])
                    else:
                        st.error("ไม่พบโมเดลที่ใช้งานได้")
                except Exception as e:
                    if "429" in str(e): st.warning("🚦 คนใช้เยอะ กรุณารอ 1 นาที")
                    else: st.error(f"Error: {e}")

# ฟีเจอร์ 3: สแกนลิงก์
elif menu == "🔗 สแกนลิงก์ (AI)":
    st.header("🔗 สแกนลิงก์")
    url = st.text_input("วางลิงก์ (URL):")
    if st.button("สแกน"):
        if url:
            with st.spinner("🔍 กำลังส่อง..."):
                try:
                    model = get_ai_model() # เลือกโมเดลที่ฉลาดขึ้น
                    if model:
                        safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
                        res = model.generate_content(f"วิเคราะห์ URL นี้ว่าอันตรายไหม: '{url}' ตอบสั้นๆ", safety_settings=safety)
                        st.write(res.text)
                        save_to_sheet(url, "Link Scan", res.text[:30])
                except Exception as e:
                    if "429" in str(e): st.warning("🚦 คนใช้เยอะ กรุณารอ 1 นาที")
                    else: st.error(f"Error: {e}")

# ฟีเจอร์ 4: รายงาน
elif menu == "📢 รายงานเบอร์โจร":
    st.header("📢 แจ้งเบาะแส")
    p = st.text_input("เบอร์โจร:")
    d = st.text_area("รายละเอียด:")
    if st.button("ส่ง"):
        if p and d:
            save_to_sheet(p, "User Reported", d)
            st.balloons()
            st.success("✅ บันทึกแล้ว!")
