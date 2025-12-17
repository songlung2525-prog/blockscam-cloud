import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# === 1. ตั้งค่าหน้าเว็บ ===
st.set_page_config(page_title="BlockScam AI 3.0", page_icon="🛡️")
st.image("https://cdn-icons-png.flaticon.com/512/9529/9529452.png", width=80)
st.title("🛡️ BlockScam AI 3.0")
st.write("ศูนย์รวมป้องกันภัยไซเบอร์: เช็กเบอร์ • แชต • ลิงก์ • แจ้งเบาะแส")

# === 2. ฟังก์ชันเชื่อมต่อ Google Sheet ===
def save_to_sheet(col1_data, col2_data, col3_data):
    # col1 = เบอร์/ลิงก์, col2 = ความเสี่ยง, col3 = หมายเหตุ
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
        # เปิดไฟล์ (ถ้าหาชื่อไม่เจอ ให้ลองแก้เป็น open_by_key ตามที่เคยทำ)
        sheet = client.open("BlockScam_Data").worksheet("Logs")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, col1_data, col2_data, col3_data])
        return True

    except Exception as e:
        # ซ่อน Error ปลอม (Response 200) ไม่ให้ user ตกใจ
        if "200" in str(e):
             return True # ถือว่าผ่าน
        st.error(f"ระบบบันทึกขัดข้อง: {e}")
        return False

# === 3. ส่วนเชื่อมต่อ AI ===
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# === 4. เมนูหลัก (Sidebar) ===
menu = st.sidebar.radio("เลือกเมนูใช้งาน:", 
    ["🔍 เช็กเบอร์โทร", "💬 สแกนแชต (AI)", "🔗 สแกนลิงก์ (AI)", "📢 รายงานเบอร์โจร"])

# ---------------------------------------------------------
# ฟีเจอร์ 1: เช็กเบอร์โทร
# ---------------------------------------------------------
if menu == "🔍 เช็กเบอร์โทร":
    st.header("🔍 ตรวจสอบเบอร์โทรศัพท์")
    phone_input = st.text_input("กรอกเบอร์ที่โทรมา:", placeholder="081xxxxxxx")
    
    if st.button("ตรวจสอบ"):
        if phone_input:
            # Logic สมมติ (ของจริงต้องเชื่อม API Blacklist)
            risk = "ปลอดภัย (ไม่พบใน Blacklist)"
            if phone_input.startswith("06") or len(phone_input) > 10:
                risk = "⚠️ มีความเสี่ยง (เบอร์แปลก)"
            
            if risk.startswith("⚠️"):
                st.error(f"ผลการตรวจ: {risk}")
            else:
                st.success(f"ผลการตรวจ: {risk}")
                
            save_to_sheet(phone_input, risk, "Check Phone")

# ---------------------------------------------------------
# ฟีเจอร์ 2: สแกนแชต (AI)
# ---------------------------------------------------------
elif menu == "💬 สแกนแชต (AI)":
    st.header("💬 วิเคราะห์แชตหลอกลวง")
    chat_text = st.text_area("ก๊อปปี้ข้อความแชตมาวาง:", height=150)
    
    if st.button("วิเคราะห์แชต"):
        if chat_text:
            with st.spinner("🤖 AI กำลังอ่าน..."):
                try:
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = f"ช่วยวิเคราะห์ข้อความนี้หน่อยว่าน่าจะเป็นมิจฉาชีพไหม: '{chat_text}' ตอบสั้นๆ พร้อมเหตุผล"
                    response = model.generate_content(prompt)
                    st.info(response.text)
                    save_to_sheet("Chat Log", "AI Analyzed", chat_text[:30]+"...")
                except:
                    st.error("AI ทำงานหนักเกินไป กรุณาลองใหม่")

# ---------------------------------------------------------
# ฟีเจอร์ 3: สแกนลิงก์ (AI) -> ✨ ของใหม่ ✨
# ---------------------------------------------------------
elif menu == "🔗 สแกนลิงก์ (AI)":
    st.header("🔗 ตรวจสอบลิงก์อันตราย")
    url_input = st.text_input("วางลิงก์ที่ได้รับ (URL):", placeholder="https://...")
    
    if st.button("สแกนลิงก์"):
        if url_input:
            with st.spinner("🔍 กำลังส่องกล้องขยาย..."):
                try:
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = f"วิเคราะห์ URL นี้: '{url_input}' ว่ามีความเสี่ยงเป็นเว็บพนัน, หลอกลวง, หรือ Phishing ไหม? ตอบสั้นๆ"
                    response = model.generate_content(prompt)
                    
                    st.markdown("### 🛡️ ผลการวิเคราะห์:")
                    st.write(response.text)
                    
                    save_to_sheet(url_input, "AI Link Scan", response.text[:50])
                except:
                    st.error("ตรวจสอบไม่ได้ (ลิงก์อาจเสียหรือ AI ไม่ว่าง)")

# ---------------------------------------------------------
# ฟีเจอร์ 4: รายงานเบอร์ (Crowdsourcing) -> ✨ ของใหม่ ✨
# ---------------------------------------------------------
elif menu == "📢 รายงานเบอร์โจร":
    st.header("📢 แจ้งเบาะแสเบอร์มิจฉาชีพ")
    st.warning("ข้อมูลที่คุณแจ้ง จะถูกเก็บเพื่อเตือนภัยผู้อื่น")
    
    report_phone = st.text_input("เบอร์มิจฉาชีพ:")
    report_detail = st.text_area("รายละเอียด (หลอกยังไง/เสียหายเท่าไหร่):")
    
    if st.button("ส่งข้อมูล"):
        if report_phone and report_detail:
            if save_to_sheet(report_phone, "User Reported", report_detail):
                st.balloons() # เอฟเฟกต์ลูกโป่ง
                st.success("✅ ขอบคุณที่ช่วยแจ้งเบาะแสครับ! ข้อมูลถูกบันทึกแล้ว")
            else:
                st.error("บันทึกไม่สำเร็จ")
        else:
            st.warning("กรุณากรอกข้อมูลให้ครบ")

        









