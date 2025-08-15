
# dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="中国 CO₂、气温与灾害仪表盘", layout="wide")

st.title("中国 CO₂ 排放与气温、自然灾害：概览仪表盘")
st.caption("数据来源：Gapminder / World Bank / EM-DAT — 请在下方替换为你的 GitHub Raw 链接")

# ========== 1) 数据链接（按需替换为你仓库的 RAW 链接） ==========
# 例子： https://raw.githubusercontent.com/williamgege/Envecon-105-data/main/co2_pcap_cons.csv
URL_CO2 = st.secrets.get("URL_CO2", "https://raw.githubusercontent.com/williamgege/Envecon-105-data/main/co2_pcap_cons.csv")
URL_ENERGY = st.secrets.get("URL_ENERGY", "https://raw.githubusercontent.com/williamgege/Envecon-105-data/main/EnergyUse.csv")
URL_GDP = st.secrets.get("URL_GDP", "https://raw.githubusercontent.com/williamgege/Envecon-105-data/main/GDP.csv")
URL_DISASTER = st.secrets.get("URL_DISASTER", "https://raw.githubusercontent.com/williamgege/Envecon-105-data/main/NaturalDisaster.xlsx")
URL_TEMP = st.secrets.get("URL_TEMP", "https://raw.githubusercontent.com/williamgege/Envecon-105-data/main/temperature.xlsx")

# ========== 2) 读数函数（带缓存 & 容错提示） ==========
@st.cache_data
def read_co2(url):
    df = pd.read_csv(url)
    # 期望：列包含 'country' 和一系列年份列
    year_cols = [c for c in df.columns if str(c).isdigit()]
    co2_long = df.melt(id_vars=["country"], value_vars=year_cols,
                       var_name="Year", value_name="CO2_pc")
    co2_long["Year"] = co2_long["Year"].astype(int)
    return co2_long

@st.cache_data
def read_worldbank_wide(url, country_col="Country Name"):
    df = pd.read_csv(url, skiprows=4)
    year_cols = [c for c in df.columns if str(c).isdigit()]
    long_df = df.melt(id_vars=[country_col], value_vars=year_cols,
                      var_name="Year", value_name="Value").rename(
                      columns={country_col:"country"})
    long_df["Year"] = long_df["Year"].astype(int)
    return long_df

@st.cache_data
def read_excel(url, sheet_name=0):
    return pd.read_excel(url, sheet_name=sheet_name)

# 尝试读取并给出错误提示
def try_read(func, *args, **kwargs):
    try:
        return func(*args, **kwargs), None
    except Exception as e:
        return None, str(e)

co2, e1 = try_read(read_co2, URL_CO2)
energy, e2 = try_read(read_worldbank_wide, URL_ENERGY)
gdp, e3 = try_read(read_worldbank_wide, URL_GDP)
disaster, e4 = try_read(read_excel, URL_DISASTER)
temp, e5 = try_read(read_excel, URL_TEMP)

if any([e1, e2, e3, e4, e5]):
    with st.expander("数据载入错误信息（请检查你的 RAW 链接是否正确）", expanded=True):
        for name, err in [("CO2", e1), ("Energy", e2), ("GDP", e3), ("Disaster", e4), ("Temperature", e5)]:
            if err:
                st.error(f"{name}: {err}")

# ========== 3) 侧边栏交互 ==========
with st.sidebar:
    st.header("筛选")
    # 国家可选：合并所有表里的国家名
    all_countries = set()
    for df in [co2, energy, gdp]:
        if df is not None and "country" in df.columns:
            all_countries |= set(df["country"].dropna().tolist())
    countries = sorted(list(all_countries)) if all_countries else ["China"]
    default_country = "China" if "China" in countries else countries[0]
    country = st.selectbox("选择国家", countries, index=countries.index(default_country))

    # 年份范围（从 co2 推断，否则给默认值）
    if co2 is not None:
        y_min, y_max = int(co2["Year"].min()), int(co2["Year"].max())
    else:
        y_min, y_max = 1960, 2020
    year_range = st.slider("年份范围", min_value=y_min, max_value=y_max, value=(max(y_min,1980), min(y_max,2020)))

st.markdown(f"**当前国家：** {country}　|　**年份：** {year_range[0]}–{year_range[1]}")

# ========== 4) 三个核心指标图：CO2 / Energy / GDP ==========
def lineplot(ax, x, y, title, ylab):
    ax.plot(x, y)
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylab)
    ax.grid(True, alpha=0.3)

col1, col2, col3 = st.columns(3)

with col1:
    if co2 is not None:
        c = co2[(co2["country"]==country) & (co2["Year"].between(*year_range))].copy()
        fig, ax = plt.subplots()
        lineplot(ax, c["Year"], c["CO2_pc"], f"CO₂ 人均排放（{country}）", "CO2 per capita")
        st.pyplot(fig)
    else:
        st.warning("CO2 数据未加载。")

with col2:
    if energy is not None:
        c = energy[(energy["country"]==country) & (energy["Year"].between(*year_range))].copy()
        fig, ax = plt.subplots()
        lineplot(ax, c["Year"], c["Value"], f"能源使用（{country}）", "Energy use (per capita)")
        st.pyplot(fig)
    else:
        st.warning("Energy 数据未加载。")

with col3:
    if gdp is not None:
        c = gdp[(gdp["country"]==country) & (gdp["Year"].between(*year_range))].copy()
        fig, ax = plt.subplots()
        lineplot(ax, c["Year"], c["Value"], f"GDP 增长率（{country}）", "GDP growth (%)")
        st.pyplot(fig)
    else:
        st.warning("GDP 数据未加载。")

# ========== 5) 气温与自然灾害（原始表格预览；如你已整理成年-值，可按上面方式画线） ==========
with st.expander("查看气温数据（temperature.xlsx）"):
    if temp is not None:
        st.dataframe(temp.head(100))
    else:
        st.info("未加载。")

with st.expander("查看自然灾害数据（NaturalDisaster.xlsx）"):
    if disaster is not None:
        st.dataframe(disaster.head(100))
    else:
        st.info("未加载。")

st.divider()
st.markdown("""
#### 说明
- 这个模板满足课程的 Dashboard 要求：交互 + 可视化 + 显示数据来源 URL。
- 如果你在 Notebook 里已经把温度/灾害整理成长表（Year, Value），可以仿照上面的 `lineplot` 折线做法添加图。
- 你也可以把你的主要发现/结论用 `st.markdown()` 写在这里，作为对公众的说明。
""")
