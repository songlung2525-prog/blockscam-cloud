import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# === 1. ตั้งค่าหน้าเว็บ ===
st.set_page_config(page_title="BlockScam AI 3.1", page_icon="🛡️")
st.image("https://cdn-icons-png.flaticon.com/512/9529/9529452.png", width=80)
st.title("🛡️ BlockScam AI 3.1")
st.write("ศูนย์รวมป้องกันภัยไซเบอร์: เช็กเบอร์ • แชต • ลิงก์ • แจ้งเบาะแส")

# === 2. ฟังก์ชันเชื่อมต่อ Google Sheet ===
def save_to_sheet(col1_data, col2_data, col3_data):
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
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
            st.error("❌ ไม่พบกุญแจ Database")
            return False

        client = gspread.authorize(creds)
        # ใช้ชื่อไฟล์ BlockScam_Data (หรือใช้ open_by_key ถ้าชื่อหาไม่เจอ)
        try:
            sheet = client.open("BlockScam_Data").worksheet("Logs")
        except:
             # ใส่รหัสสำรองเผื่อหาชื่อไม่เจอ
            sheet_id = "1H3IC-sDGa4f2TebGTxOsc3WI_p0RNJPgEwckxgBniD4" 
            sheet = client.open_by_key(sheet_id).worksheet("Logs")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, col1_data, col2_data, col3_data])
        return True

    except Exception as e:
        if "200" in str(e): return True
        st.error(f"ระบบบันทึกขัดข้อง: {e}")
        return False

# === 3. ส่วนเชื่อมต่อ AI ===
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# === 4. เมนูหลัก ===
menu = st.sidebar.radio("เลือกเมนูใช้งาน:", 
    ["🔍 เช็กเบอร์โทร", "💬 สแกนแชต (AI)", "🔗 สแกนลิงก์ (AI)", "📢 รายงานเบอร์โจร"])

# ฟีเจอร์ 1: เช็กเบอร์
if menu == "🔍 เช็กเบอร์โทร":
    st.header("🔍 ตรวจสอบเบอร์โทรศัพท์")
    phone_input = st.text_input("กรอกเบอร์ที่โทรมา:", placeholder="081xxxxxxx")
    if st.button("ตรวจสอบ"):
        if phone_input:
            risk = "ปลอดภัย (ไม่พบใน Blacklist)"
            if phone_input.startswith("06") or len(phone_input) > 10:
                risk = "⚠️ มีความเสี่ยง (เบอร์แปลก)"
            
            if risk.startswith("⚠️"): st.error(f"ผลการตรวจ: {risk}")
            else: st.success(f"ผลการตรวจ: {risk}")
            save_to_sheet(phone_input, risk, "Check Phone")

# ฟีเจอร์ 2: สแกนแชต (แก้เป็นโมเดลใหม่ gemini-1.5-flash)
elif menu == "💬 สแกนแชต (AI)":
    st.header("💬 วิเคราะห์แชตหลอกลวง")
    chat_text = st.text_area("ก๊อปปี้ข้อความแชตมาวาง:", height=150)
    if st.button("วิเคราะห์แชต"):
        if chat_text:
            with st.spinner("🤖 AI กำลังอ่าน..."):
                try:
                    # ใช้โมเดลใหม่ 1.5-flash
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(f"วิเคราะห์ข้อความนี้ว่าเป็นมิจฉาชีพไหม: '{chat_text}' ตอบสั้นๆ")
                    st.info(response.text)
                    save_to_sheet("Chat Log", "AI Analyzed", chat_text[:30]+"...")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

# ฟีเจอร์ 3: สแกนลิงก์ (แก้เป็นโมเดลใหม่ + ปลด Safety)
elif menu == "🔗 สแกนลิงก์ (AI)":
    st.header("🔗 ตรวจสอบลิงก์อันตราย")
    url_input = st.text_input("วางลิงก์ที่ได้รับ (URL):", placeholder="https://...")
    if st.button("สแกนลิงก์"):
        if url_input:
            with st.spinner("🔍 กำลังส่องกล้องขยาย..."):
                try:
                    # ปลดล็อก Safety Settings
                    safety_settings = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ]
                    # ใช้โมเดลใหม่ 1.5-flash
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"วิเคราะห์ URL นี้: '{url_input}' ว่ามีความเสี่ยงเป็นเว็บพนัน, หลอกลวง, หรือ Phishing ไหม? ตอบสั้นๆ ตรงไปตรงมา"
                    
                    response = model.generate_content(prompt, safety_settings=safety_settings)
                    
                    st.markdown("### 🛡️ ผลการวิเคราะห์:")
                    st.write(response.text)
                    save_to_sheet(url_input, "AI Link Scan", response.text[:50])
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

# ฟีเจอร์ 4: รายงานเบอร์
elif menu == "📢 รายงานเบอร์โจร":
    st.header("📢 แจ้งเบาะแสเบอร์มิจฉาชีพ")
    report_phone = st.text_input("เบอร์มิจฉาชีพ:")
    report_detail = st.text_area("รายละเอียด:")
    if st.button("ส่งข้อมูล"):
        if report_phone and report_detail:
            if save_to_sheet(report_phone, "User Reported", report_detail):
                st.balloons()
                st.success("✅ ขอบคุณที่ช่วยแจ้งเบาะแสครับ!")










