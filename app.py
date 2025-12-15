
import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# === ตั้งค่าหน้าเว็บ ===
st.set_page_config(page_title="BlockScam AI", page_icon="🛡️")

st.image("https://cdn-icons-png.flaticon.com/512/9529/9529452.png", width=100)
st.title("🛡️ BlockScam AI 2.0")
st.write("ระบบตรวจสอบเบอร์และแชตมิจฉาชีพ อัจฉริยะ (เชื่อมต่อฐานข้อมูล)")

# === ส่วนเชื่อมต่อ Google Sheet (ความจำ) ===
def save_to_sheet(phone, risk, note):
    try:
        # ดึงกุญแจจาก Secrets ที่เราซ่อนไว้
        if "gsheets_key" in st.secrets:
            key_dict = json.loads(st.secrets["gsheets_key"])
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
            client = gspread.authorize(creds)
            
            # เปิดไฟล์ Sheet (ต้องตรงกับชื่อไฟล์ที่คุณตั้งเป๊ะๆ)
            sheet = client.open("BlockScam_Data").worksheet("Logs")
            
            # บันทึกข้อมูล: [เวลา, เบอร์, ความเสี่ยง, หมายเหตุ]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, phone, risk, note])
            return True
        else:
            return False
    except Exception as e:
        st.error(f"บันทึกข้อมูลไม่สำเร็จ: {e}")
        return False

# === ส่วนเชื่อมต่อ AI ===
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    st.success("🟢 ระบบ AI: พร้อมทำงาน")
else:
    st.error("🔴 ไม่พบกุญแจ AI (เช็ก Secrets)")

# === เมนูหลัก ===
menu = st.radio("เลือกเมนูใช้งาน:", ["🔍 เช็กเบอร์โทร", "💬 สแกนแชต (AI)"], horizontal=True)

# --- ฟีเจอร์ 1: เช็กเบอร์ ---
if menu == "🔍 เช็กเบอร์โทร":
    st.subheader("ตรวจสอบเบอร์โทรศัพท์")
    phone_input = st.text_input("กรอกเบอร์ที่โทรมา:", placeholder="เช่น 0812345678")
    
    if st.button("ตรวจสอบเบอร์"):
        if phone_input:
            # สมมติการตรวจ (ในอนาคตอาจเชื่อมฐานข้อมูล Blacklist จริง)
            risk_score = "ไม่พบใน Blacklist"
            if phone_input.startswith("06") or len(phone_input) > 10: 
                 risk_score = "เสี่ยงสูง (เบอร์แปลก)"
            
            st.info(f"ผลการตรวจ: {risk_score}")
            
            # บันทึกลง Google Sheet
            if save_to_sheet(phone_input, risk_score, "ตรวจสอบผ่านแอป"):
                st.toast("✅ บันทึกข้อมูลลงฐานข้อมูลแล้ว!", icon="💾")
            else:
                st.warning("⚠️ ยังไม่ได้ตั้งค่า Database (แต่ตรวจสอบได้ปกติ)")
        else:
            st.warning("กรุณากรอกเบอร์โทรครับ")

# --- ฟีเจอร์ 2: สแกนแชต (AI Auto) ---
elif menu == "💬 สแกนแชต (AI)":
    st.subheader("วิเคราะห์บทสนทนา")
    chat_text = st.text_area("วางข้อความแชต:", height=150)
    
    if st.button("วิเคราะห์ความเสี่ยง"):
        if chat_text:
            with st.spinner("🤖 AI กำลังคิด..."):
                try:
                    # ค้นหาโมเดลอัตโนมัติ
                    target_model = 'gemini-pro' # ค่าเริ่มต้น
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            if 'flash' in m.name: target_model = m.name; break
                            
                    model = genai.GenerativeModel(target_model)
                    
                    # สั่งงาน AI
                    prompt = f"""วิเคราะห์ข้อความนี้: "{chat_text}"
                    1. คะแนนความเสี่ยง (0-100%)
                    2. รูปแบบการหลอกลวง
                    3. คำแนะนำสั้นๆ"""
                    
                    response = model.generate_content(prompt)
                    st.markdown("### 🛡️ ผลการวิเคราะห์:")
                    st.write(response.text)
                    
                    # บันทึกลง Sheet
                    save_to_sheet("Chat Scan", "AI Analyzed", chat_text[:50]+"...")
                    st.toast("✅ บันทึกประวัติแล้ว", icon="💾")
                    
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")



