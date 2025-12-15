import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# === 1. ตั้งค่าหน้าเว็บ ===
st.set_page_config(page_title="BlockScam AI", page_icon="🛡️")
st.image("https://cdn-icons-png.flaticon.com/512/9529/9529452.png", width=100)
st.title("🛡️ BlockScam AI 2.0")
st.write("ระบบตรวจสอบเบอร์และแชตมิจฉาชีพ (เชื่อมต่อฐานข้อมูล)")

# === 2. ฟังก์ชันเชื่อมต่อ Google Sheet (ฉบับสมบูรณ์) ===
def save_to_sheet(phone, risk, note):
    try:
        # กำหนดสิทธิ์ให้ชัดเจน (แก้ Error 403)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # ตรวจสอบกุญแจและเชื่อมต่อ
        if "gcp_service_account" in st.secrets:
            # แบบใหม่ (Table Format)
            secret_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(secret_dict, scopes=scopes)
        elif "gsheets_key" in st.secrets:
            # แบบเก่า (JSON String)
            try:
                key_dict = json.loads(st.secrets["gsheets_key"])
                creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
            except:
                # กรณีใช้ ' (Single Quote) ใน Secrets
                import ast
                key_dict = ast.literal_eval(st.secrets["gsheets_key"])
                creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        else:
            st.error("❌ ไม่พบกุญแจ Database ใน Secrets")
            return False

        # เชื่อมต่อ Client
        client = gspread.authorize(creds)

        #  open_by_key 
        sheet_id =    "1H3IC-sDGa4f2TebGTxOsc3WI_p0RNJPgEwckxgBniD4"
        sheet = client.open_by_key(sheet_id).worksheet("Logs")
        
    

        
        # บันทึกข้อมูล
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, phone, risk, note])
        return True

    except Exception as e:
        st.error(f"❌ บันทึกไม่สำเร็จ: {e}")
        return False

# === 3. ส่วนเชื่อมต่อ AI ===
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.warning("⚠️ ไม่พบกุญแจ AI")

# === 4. เมนูหลัก ===
menu = st.radio("เลือกเมนูใช้งาน:", ["🔍 เช็กเบอร์โทร", "💬 สแกนแชต (AI)"], horizontal=True)

# --- ฟีเจอร์: เช็กเบอร์ ---
if menu == "🔍 เช็กเบอร์โทร":
    st.subheader("ตรวจสอบเบอร์โทรศัพท์")
    phone_input = st.text_input("กรอกเบอร์ที่โทรมา:", placeholder="เช่น 0812345678")
    
    if st.button("ตรวจสอบเบอร์"):
        if phone_input:
            # จำลองผลการตรวจ
            risk_score = "ไม่พบใน Blacklist"
            if phone_input.startswith("06") or len(phone_input) > 10: 
                 risk_score = "เสี่ยงสูง (เบอร์แปลก)"
            
            st.info(f"ผลการตรวจ: {risk_score}")
            
            # บันทึกลง Sheet
            if save_to_sheet(phone_input, risk_score, "ตรวจสอบผ่านแอป"):
                st.toast("✅ บันทึกข้อมูลเรียบร้อย!", icon="💾")
            else:
                st.warning("⚠️ บันทึกข้อมูลไม่สำเร็จ (แต่ตรวจสอบได้ปกติ)")
        else:
            st.warning("กรุณากรอกเบอร์โทรครับ")

# --- ฟีเจอร์: สแกนแชต ---
elif menu == "💬 สแกนแชต (AI)":
    st.subheader("วิเคราะห์บทสนทนา")
    chat_text = st.text_area("วางข้อความแชต:", height=150)
    
    if st.button("วิเคราะห์ความเสี่ยง"):
        if chat_text:
            with st.spinner("🤖 AI กำลังคิด..."):
                try:
                    # หาโมเดลอัตโนมัติ
                    target_model = 'gemini-pro'
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            if 'flash' in m.name: target_model = m.name; break
                    
                    model = genai.GenerativeModel(target_model)
                    
                    response = model.generate_content(f"วิเคราะห์ความเสี่ยงของข้อความนี้: '{chat_text}' สั้นๆ เข้าใจง่าย")
                    
                    st.markdown("### 🛡️ ผลการวิเคราะห์:")
                    st.write(response.text)
                    
                    # บันทึกลง Sheet
                    save_to_sheet("Chat Scan", "AI Analyzed", chat_text[:50]+"...")
                    st.toast("✅ บันทึกประวัติแล้ว", icon="💾")
                    
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
    

        








