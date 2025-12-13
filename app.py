import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import pandas as pd

# --- 1. ตั้งค่า DATABASE (หลังบ้าน) ---
DATABASE_URL = "sqlite:///./blockscam.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ScamReportDB(Base):
    __tablename__ = "scam_reports"
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True)
    description = Column(String)
    risk_level = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 2. ตั้งค่า AI (สมองกล) ---
@st.cache_resource # เทคนิคช่วยให้โหลดเร็วขึ้น
def load_ai_model():
    train_texts = [
        "คุณคือผู้โชคดีได้รับรางวัล", "เงินกู้ด่วน ดอกเบี้ยต่ำ อนุมัติไว",
        "บัญชีของท่านถูกระงับ โปรดยืนยันตัวตน", "คลิกลิงก์เพื่อรับเงินคืนทันที",
        "รับสมัครคนดูยูทูป รายได้ดี", "สวัสดีครับ วันนี้มาทำงานไหม",
        "ขอยืมสมุดจดการบ้านหน่อย", "แม่ครับ วันนี้กลับดึกนะ",
        "ประชุมพรุ่งนี้เลื่อนเป็นบ่ายสอง", "กินข้าวหรือยัง เป็นห่วงนะ"
    ]
    train_labels = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
    
    vec = CountVectorizer()
    X = vec.fit_transform(train_texts)
    model = MultinomialNB()
    model.fit(X, train_labels)
    return vec, model

vectorizer, ai_model = load_ai_model()

# --- 3. ส่วนหน้าจอ (Frontend) ---
st.set_page_config(page_title="BlockScam Cloud", page_icon="☁️")
# --- NEW: ปรับแต่ง CSS ให้เหมือนแอปมือถือ ---
st.markdown("""
<style>
    /* ซ่อนเมนูขวาบนและ Footer ที่รกๆ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ปรับขอบจอให้ชิดขึ้น (จะได้ไม่เปลืองที่) */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    
    /* เปลี่ยนปุ่มกดให้เต็มจอ (กดง่ายในมือถือ) */
    .stButton>button {
        width: 100%;
        border-radius: 20px; /* ทำขอบมนๆ */
        height: 3em;         /* เพิ่มความสูงปุ่ม */
        font-weight: bold;   /* ตัวหนา */
        box-shadow: 0px 2px 5px rgba(0,0,0,0.2); /* ใส่เงาให้ดูมีมิติ */
    }
    
    /* ปรับช่องกรอกข้อความให้ใหญ่ขึ้น */
    .stTextInput>div>div>input {
        font-size: 16px; 
    }
</style>
""", unsafe_allow_html=True)
st.title("☁️ BlockScam AI (Online Ver.)")
st.caption("ระบบตรวจสอบมิจฉาชีพ ที่ใครๆ ก็เข้าถึงได้")

menu = ["🔍 เช็กเบอร์โทร", "💬 สแกนแชต", "🔗 เช็กเว็บไซต์", "📢 แจ้งเบาะแส"]
choice = st.sidebar.selectbox("เมนูใช้งาน", menu)

db = SessionLocal() # เชื่อมต่อฐานข้อมูล

if choice == "🔍 เช็กเบอร์โทร":
    st.info("ตรวจสอบเบอร์โทรศัพท์จากฐานข้อมูล")
    phone = st.text_input("กรอกเบอร์โทรศัพท์")
    if st.button("ตรวจสอบ"):
        result = db.query(ScamReportDB).filter(ScamReportDB.phone_number == phone).first()
        if result:
            st.error(f"⚠️ เจอประวัติ! ระดับความเสี่ยง: {result.risk_level}")
            st.write(f"**รายละเอียด:** {result.description}")
        else:
            st.success("✅ ไม่พบประวัติในระบบ")

elif choice == "💬 สแกนแชต":
    st.info("ใช้ AI วิเคราะห์ประโยค")
    text = st.text_area("วางข้อความที่นี่")
    if st.button("วิเคราะห์"):
        vec_text = vectorizer.transform([text])
        pred = ai_model.predict(vec_text)[0]
        prob = ai_model.predict_proba(vec_text)[0][1] * 100
        
        if pred == 1:
            st.error(f"🔴 AI คิดว่าเป็นข้อความหลอกลวง (มั่นใจ {prob:.2f}%)")
        else:
            st.success(f"🟢 ข้อความดูปลอดภัย (มั่นใจ {100-prob:.2f}%)")

elif choice == "🔗 เช็กเว็บไซต์":
    st.info("ตรวจสอบลิงก์อันตราย")
    url = st.text_input("วางลิงก์ที่นี่").lower()
    if st.button("ตรวจสอบ"):
        fake_brands = ["kbank", "scb", "facebook", "tiktok"]
        real_domains = ["kasikornbank.com", "scb.co.th", "facebook.com", "tiktok.com"]
        
        found_fake = False
        for brand, real in zip(fake_brands, real_domains):
            if brand in url and real not in url:
                st.error(f"⛔ อันตราย! ลิงก์นี้แอบอ้าง {brand} แต่ไม่ใช่เว็บจริง")
                found_fake = True
                break
        
        if not found_fake:
            st.success("✅ โครงสร้างลิงก์ดูปกติ (แต่ต้องระวังเสมอ)")

elif choice == "📢 แจ้งเบาะแส":
    st.warning("แจ้งเบอร์มิจฉาชีพเข้าสู่ระบบส่วนกลาง")
    with st.form("report"):
        p_num = st.text_input("เบอร์มิจฉาชีพ")
        desc = st.text_area("พฤติกรรม")
        risk = st.select_slider("ความรุนแรง", ["Low", "Medium", "High"])
        if st.form_submit_button("บันทึกข้อมูล"):
            new_report = ScamReportDB(phone_number=p_num, description=desc, risk_level=risk)
            db.add(new_report)
            db.commit()
            st.success("บันทึกข้อมูลสำเร็จ! 🎈")
            st.balloons()