
import streamlit as st
import pandas as pd
import numpy as np
import pickle
from fpdf import FPDF
from datetime import datetime
import altair as alt

st.set_page_config(page_title="Smart Crop Advisor", page_icon="🌾")

# 🌼 Styling
st.markdown("""
<style>
.stApp {
    background-image: url("https://wallpaperaccess.com/full/3006252.jpg");
    background-size: cover;
    background-attachment: fixed;
}
.sidebar .sidebar-content {
    background-color: rgba(255,255,255,0.95);
}
hr {
    border: none;
    border-top: 2px solid #66bb6a;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# 🚜 Functions
def fertilizer(N, P, K):
    return [tip for tip in [
        "Add nitrogen-rich fertilizer" if N < 50 else None,
        "Add phosphorus-rich fertilizer" if P < 25 else None,
        "Add potassium-rich fertilizer" if K < 30 else None
    ] if tip] or ["NPK levels are sufficient."]

def soil_score(N, P, K, ph, rain):
    return 5 - sum([N<60, P<30, K<35, ph<6.0 or ph>8.0, rain<75 or rain>350])

def micronutrient(soil):
    return {
        "Red": ["Iron deficiency risk", "Grow lentils or spinach"],
        "Laterite": ["Iron deficiency risk", "Grow lentils or spinach"],
        "Desert": ["Iron deficiency risk", "Grow lentils or spinach"],
        "Black": ["Zinc deficiency possible", "Try maize or millets"],
        "Alluvial": ["Zinc deficiency possible", "Try maize or millets"]
    }.get(soil, ["No major micronutrient risks"])

def sanitize(text):
    return ''.join(c for c in str(text) if ord(c) < 256)

def create_pdf(crop, N, P, K, temp, hum, ph, rain, area, profit, rev, tips, score, micro):
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.set_text_color(34,139,34)
    pdf.set_x(10); pdf.multi_cell(190, 10, sanitize("Crop Advisory Report"), align='C')
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 12)

    details = [
        f"Crop: {crop}", f"Land Area: {area} ha", f"Profit/ha: Rs {profit:.2f}",
        f"Total Revenue: Rs {rev:.2f}", f"NPK Levels: {N},{P},{K}",
        f"Climate: {temp}°C, {hum}% Humidity, pH {ph}, Rainfall {rain}mm",
        f"Soil Health Score: {score}/5"
    ]
    for line in details: pdf.cell(0, 10, sanitize(line), ln=True)

    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, sanitize("Fertilizer Tips"), ln=True)
    pdf.set_font("Arial", '', 12)
    for tip in tips: pdf.multi_cell(0, 8, sanitize(tip))

    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, sanitize("Micronutrient Advisory"), ln=True)
    pdf.set_font("Arial", '', 12)
    for m in micro: pdf.multi_cell(0, 8, sanitize(m))

    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, sanitize("Useful Links"), ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 8, sanitize("Mandi Prices: https://agmarknet.gov.in/"))
    pdf.multi_cell(0, 8, sanitize("Crop Research: https://sri.csir.org.gh/"))
    pdf.cell(0, 10, sanitize(f"Date: {datetime.now().strftime('%d-%m-%Y')}"), ln=True)

    return pdf.output(dest='S').encode('latin1')

# The rest of your code can be added here...
# 📦 Load Model
model = pickle.load(open("crop_model.pkl", "rb"))

@st.cache_data
def load_default_data():
    return pd.read_csv("commodity_price.csv")

# 📤 Upload CSV
uploaded_file = st.sidebar.file_uploader("📥 Upload crop_prices.csv", type="csv")
data = load_default_data() 
# 🧪 Sidebar Inputs
st.sidebar.title("🌿 Soil & Climate Inputs")
soil = st.sidebar.selectbox("🧱 Soil Type", ["Alluvial","Black","Red","Laterite","Desert","Mountain"])
default_N, default_P, default_K = {
    "Alluvial": (80,40,40), "Black": (60,30,50), "Red": (50,25,30),
    "Laterite": (40,20,25), "Desert": (30,15,20), "Mountain": (60,25,30)
}[soil]
N = st.sidebar.slider("Nitrogen", 0, 200, default_N)
P = st.sidebar.slider("Phosphorus", 0, 200, default_P)
K = st.sidebar.slider("Potassium", 0, 200, default_K)
temp = st.sidebar.slider("Temperature (°C)", 0.0, 50.0, 25.0)
hum = st.sidebar.slider("Humidity (%)", 0.0, 100.0, 60.0)
ph = st.sidebar.slider("Soil pH", 3.0, 10.0, 6.5)
rain = st.sidebar.slider("Rainfall (mm)", 0.0, 400.0, 100.0)
area = st.sidebar.slider("Land Area (ha)", 0.1, 100.0, 1.0)


# 🌾 App Title
st.markdown("""
<div style='background-color: #dcedc8; padding: 15px; border-radius: 10px; text-align: center; border-left: 5px solid #66bb6a;'>
<h2 style='color: #33691e;'>🌱 Smart Crop Recommendation System</h2>
</div>
""", unsafe_allow_html=True)
st.markdown("""
<div style='height: 40px;'></div>
""", unsafe_allow_html=True)
#Recommend crop 
if st.button("🚀 Recommend Best Crop"):
    crop = model.predict([[N, P, K, temp, hum, ph, rain]])[0].capitalize()
    # Clean crop names in CSV and match loosely
    data["Commodity_clean"] = data["Commodity"].str.strip().str.lower()
    crop_clean = crop.strip().lower()
    st.write("🔍 Predicted crop:", crop)
    st.write("🧾 Available crops in CSV:", data["Commodity_clean"].unique())

    match = data[data["Commodity_clean"].str.contains(crop_clean)]

    if not match.empty:
        price = match.iloc[0]["MarketPricePerKg"]
        yield_ = match.iloc[0]["YieldPerHectare"]
        profit = price * yield_
        rev = profit * area
    else:
        price = yield_ = profit = rev = 0
        st.warning("⚠️ No matching crop found in CSV. Showing ₹0.00 until updated.")

    tips = fertilizer(N, P, K)
    score = soil_score(N, P, K, ph, rain)
    micro = micronutrient(soil)
    pdf = create_pdf(crop, N, P, K, temp, hum, ph, rain, area, profit, rev, tips, score, micro)

    # 📦 Side-by-Side Layout
    left_col, _, right_col = st.columns([1, 0.05, 1])  # extra spacing between columns

    with left_col:
        st.markdown("### 🌾 Recommended Crop Summary")
        st.markdown(f"""
        <div style='background-color: #f1f8e9; padding: 20px; border-radius: 12px; border-left: 5px solid #43a047;'>
            <h3 style='color:#33691e;'>{crop}</h3>
            <ul style='list-style:none; padding-left:0; font-size:16px;'>
                <li><strong>Price/kg:</strong> ₹{price:.2f}</li>
                <li><strong>Yield/ha:</strong> {yield_:,.0f} kg</li>
                <li><strong>Profit/ha:</strong> ₹{profit:,.2f}</li>
                <li><strong>Total Revenue:</strong> ₹{rev:,.2f}</li>
            </ul>
            <br>
            <strong>📄 Download Your Advisory:</strong>
        </div>
        """, unsafe_allow_html=True)

        st.download_button("📄 Download PDF", pdf, file_name=f"{crop}_advisory.pdf", mime="application/pdf")

    with right_col:
        st.markdown("### 🌿 Advisory Panel")
        st.markdown("""
        <div style='background-color: #fff9c4; padding: 15px; border-radius: 10px; border-left: 5px solid #fbc02d;'>
        <h4 style='color: #f57f17;'>Insights & Tips</h4>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🧪 Fertilizer Tips"):
            for tip in tips:
                st.markdown(f"✔️ {tip}")

        with st.expander("🧬 Micronutrient Advisory"):
            for m in micro:
                st.markdown(f"🩺 {m}")

        with st.expander("🌱 Soil Health Score"):
            st.markdown(f"📊 Score: **{score}/5**")


# 🧮 Calculate Top 5 Profitable Crops
profit_table = data.copy()
profit_table["ProfitPerHa"] = data["MarketPricePerKg"] * data["YieldPerHectare"]
top5 = profit_table.sort_values(by="ProfitPerHa", ascending=False).head(5)

# 📊 Prepare Chart Data
chart_data = top5[["Commodity", "ProfitPerHa"]]
chart = alt.Chart(chart_data).mark_bar(color="#66bb6a").encode(
    x=alt.X("Crop", sort="-y"),
    y="ProfitPerHa",
    tooltip=["Commodity", "ProfitPerHa"]
).properties(title="Top 5 Crop Profit Comparison")

# 🔲 Layout with gap and expandable dropdowns
col1, spacer, col2 = st.columns([1, 0.1, 1])

with col1:
    with st.expander("📈 Top 5 Profitable Crops"):
        st.table(top5[["Commodity", "ProfitPerHa"]].style.format({"ProfitPerHa": "₹{:,.2f}"}))

with col2:
    with st.expander("📉 Profit Comparison Chart"):
        st.altair_chart(chart, use_container_width=True)
