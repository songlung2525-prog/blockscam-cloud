import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# === 1. ตั้งค่าหน้าเว็บ ===
st.set_page_config(page_title="BlockScam V5.1", page_icon="🛡️")
st.image("https://cdn-icons-png.flaticon.com/512/9529/9529452.png", width=80)
st.title("🛡️ BlockScam V5.1 (Auto-Fallback)")
st.write("เวอร์ชันเสถียร: ค้นหาโมเดลอัตโนมัติ + เชื่อมฐานข้อมูล")

# === 2. ฟังก์ชันค้นหาโมเดล AI (กลับมาใช้ท่าไม้ตายเดิม!) ===
def get_ai_model():
    try:
        # วนลูปดูรายชื่อโมเดลทั้งหมดที่ Server มี
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # ถ้าเจอตัวที่มีคำว่า flash หรือ pro ให้เอาตัวนั้นเลย
                if 'flash' in m.name or 'pro' in m.name:
                    return genai.GenerativeModel(m.name)
        
        # ถ้าหาไม่เจอจริงๆ ให้ลองเสี่ยงดวงกับ gemini-pro (ตัวกันตาย)
        return genai.GenerativeModel('gemini-pro')
    except:
        return None

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
            # รหัส Sheet สำรองของคุณ
            return client.open_by_key("1H3IC-sDGa4f2TebGTxOsc3WI_p0RNJPgEwckxgBniD4").worksheet("Logs")
    except:
        return None

def save_to_sheet(col1, col2, col3):
    try:
        sheet = get_sheet_connection()
        if sheet:
            sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), col1, col2, col3])
            return True
    except:
        return False

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
menu = st.sidebar.radio("เมนู:", ["🔍 เช็กเบอร์โทร", "💬 สแกนแชต", "🔗 สแกนลิงก์", "📢 รายงานเบอร์โจร"])

# ฟีเจอร์ 1: เช็กเบอร์
if menu == "🔍 เช็กเบอร์โทร":
    st.header("🔍 ตรวจสอบเบอร์โทรศัพท์")
    phone = st.text_input("เบอร์โทร:", placeholder="081xxxxxxx")
    if st.button("ตรวจสอบ"):
        if phone:
            with st.spinner("กำลังค้นหา..."):
                if check_blacklist(phone):
                    st.error(f"🚨 อันตราย! เบอร์ {phone} มีในบัญชีดำ")
                    save_to_sheet(phone, "อันตราย (Blacklist)", "User Checked")
                else:
                    risk = "เบอร์แปลก" if (phone.startswith("06") or len(phone) > 10) else "ปลอดภัย"
                    if risk == "เบอร์แปลก": st.warning("⚠️ เบอร์แปลก/ไม่คุ้นเคย")
                    else: st.success("✅ ไม่พบประวัติ")
                    save_to_sheet(phone, risk, "User Checked")

# ฟีเจอร์ 2: สแกนแชต
elif menu == "💬 สแกนแชต":
    st.header("💬 วิเคราะห์แชต")
    chat = st.text_area("ข้อความแชต:")
    if st.button("วิเคราะห์"):
        if chat:
            with st.spinner("🤖 AI กำลังอ่าน..."):
                try:
                    model = get_ai_model()
                    if model:
                        res = model.generate_content(f"วิเคราะห์ข้อความนี้ว่าเป็นมิจฉาชีพไหม: '{chat}' ตอบสั้นๆ")
                        st.info(res.text)
                        save_to_sheet("Chat", "AI Scan", chat[:30])
                    else:
                        st.error("ไม่พบโมเดล AI")
                except Exception as e:
                    if "429" in str(e): st.warning("🚦 คนใช้งานเยอะ กรุณารอสักครู่")
                    else: st.error(f"Error: {e}")

# ฟีเจอร์ 3: สแกนลิงก์
elif menu == "🔗 สแกนลิงก์":
    st.header("🔗 สแกนลิงก์อันตราย")
    url = st.text_input("URL:")
    if st.button("สแกน"):
        if url:
            with st.spinner("🔍 กำลังส่องกล้อง..."):
                try:
                    model = get_ai_model()
                    if model:
                        safety = [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
                        res = model.generate_content(f"วิเคราะห์ URL นี้ว่าอันตรายไหม: '{url}' ตอบสั้นๆ", safety_settings=safety)
                        st.success("✅ เรียบร้อย!")
                        st.write(res.text)
                        save_to_sheet(url, "Link Scan", res.text[:30])
                    else:
                        st.error("ไม่พบโมเดล AI")
                except Exception as e:
                    if "429" in str(e): st.warning("🚦 คนใช้งานเยอะ กรุณารอสักครู่")
                    else: st.error(f"Error: {e}")

# ฟีเจอร์ 4: รายงาน
elif menu == "📢 รายงานเบอร์โจร":
    st.header("📢 แจ้งเบาะแส")
    p = st.text_input("เบอร์โจร:")
    d = st.text_area("รายละเอียด:")
    if st.button("ส่งข้อมูล"):
        if p and d:
            save_to_sheet(p, "User Report", d)
            st.balloons()
            st.success("✅ บันทึกแล้ว ขอบคุณครับ!")
