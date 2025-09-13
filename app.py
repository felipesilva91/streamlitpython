import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from matplotlib.ticker import FuncFormatter
import base64

# ============ CONFIG GOOGLE SHEETS ============
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "credenciais.json"
SHEET_ID = "1oIudf9tYyzTIhCb_TD122vKyFuwHq6Dl2M4bNt0dxmg"

creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
client = gspread.authorize(creds)

sheet_mr = client.open_by_key(SHEET_ID).worksheet("Interface MR")
sheet_dp = client.open_by_key(SHEET_ID).worksheet("Interface DP")

aba = st.sidebar.radio("Escolha o Tipo de Simulação:", ["Módulo de Resiliência", "Deformação Permanente"])

# ============ IMAGEM BASE64 PARA CENTRALIZAÇÃO ============
def carregar_imagem_base64(caminho):
    with open(caminho, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

base64_imagem = carregar_imagem_base64("imagem/DENIT.jpeg")

# ============ CSS PARA CENTRALIZAR ============
st.markdown("""
    <style>
        .image-center {
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 200px;
        }
        .titulo-principal {
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            margin-bottom: -10px;
        }
        .subtitulo {
            text-align: center;
            font-size: 24px;
            margin-top: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# Exibir imagem centralizada
st.markdown(f'<img src="data:image/png;base64,{base64_imagem}" class="image-center">', unsafe_allow_html=True)

# Títulos
st.markdown('<div class="titulo-principal">Simulação de Ensaio</div>', unsafe_allow_html=True)
if aba == "Módulo de Resiliência":
    st.markdown('<div class="subtitulo">Módulo de Resiliência</div>', unsafe_allow_html=True)
elif aba == "Deformação Permanente":
    st.markdown('<div class="subtitulo">Deformação Permanente</div>', unsafe_allow_html=True)

# ============ FUNÇÃO DE CONVERSÃO ============
def input_decimal(label, valor_inicial="0,00"):
    entrada = st.text_input(label, valor_inicial)
    try:
        return float(entrada.replace(",", "."))
    except ValueError:
        st.error(f"❌ Valor inválido para '{label}'. Use vírgula para decimais.")
        st.stop()

# ============ INTERFACE MR ============
if aba == "Módulo de Resiliência":
    ot = input_decimal("OT (%)")
    ip = input_decimal("IP")
    v25 = input_decimal("25,4 mm")
    v95 = input_decimal("9,5 mm")
    v476 = input_decimal("4,76 mm")
    v2 = input_decimal("2 mm")
    v042 = input_decimal("0,42 mm")
    v0074 = input_decimal("0,074 mm")

    if st.button("Calcular MR"):
        sheet_mr.update("A2:H2", [[ot, ip, v25, v95, v476, v2, v042, v0074]])
        dados = sheet_mr.get_all_records()
        df = pd.DataFrame(dados)

        # Conversão e formatação
        df["σ3"] = df["σ3"].astype(float) / 1000
        df["σd"] = df["σd"].astype(float) / 1000
        df["MR (MPa)"] = df["MR (MPa)"].astype(float) / 100

        df["σ3"] = df["σ3"].apply(lambda x: f"{x:.3f}".replace(".", ","))
        df["σd"] = df["σd"].apply(lambda x: f"{x:.3f}".replace(".", ","))
        df["MR (MPa)"] = df["MR (MPa)"].apply(lambda x: f"{x:.2f}".replace(".", ","))

        resultados = df[["σ3", "σd", "MR (MPa)"]]

        st.subheader("Resultados")
        st.dataframe(resultados, use_container_width=True)

        # Exportar apenas a tabela (sem gráfico)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            resultados.to_excel(writer, sheet_name='Resultados', index=False)

        st.download_button("📥 Baixar resultados (Excel)", output.getvalue(),
                           "resultados_MR.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ============ INTERFACE DP ============
elif aba == "Deformação Permanente":
    ot = input_decimal("OT (%)")
    yd = input_decimal("Yd (max)")
    p10 = input_decimal("#10 (%)")
    p40 = input_decimal("#40 (%)")
    p200 = input_decimal("#200 (%)")
    sigma3 = input_decimal("σ3")
    sigmad = input_decimal("σd")

    if st.button("Calcular DP"):
        sheet_dp.update("A2:G2", [[ot, yd, p10, p40, p200, sigma3, sigmad]])
        dados = sheet_dp.get_all_records()
        df = pd.DataFrame(dados)

        df.columns = [c.strip().lower() for c in df.columns]
        if "ciclos" not in df.columns or "dp (%)" not in df.columns:
            st.error("❌ Colunas 'Ciclos' e/ou 'DP (%)' não foram encontradas. Verifique a aba 'Interface DP'.")
            st.stop()

        df["ciclos"] = df["ciclos"].astype(int)
        df["dp (%)"] = df["dp (%)"].astype(float).round(5)
        df["dp_decimal"] = (df["dp (%)"] / 100000).round(5)

        resultados = df[["ciclos", "dp_decimal"]].rename(columns={"dp_decimal": "DP"})
        resultados["DP"] = resultados["DP"].apply(lambda x: f"{x:.5f}".replace(".", ","))

        st.subheader("Resultados")
        st.dataframe(resultados, use_container_width=True)

        fig, ax = plt.subplots()
        ax.plot(df["ciclos"], df["dp_decimal"], marker="o")
        ax.set_xlabel("Ciclos")
        ax.set_ylabel("DP")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.5f}".replace(".", ",")))
        st.pyplot(fig)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export = df[["ciclos", "dp_decimal"]].rename(columns={"dp_decimal": "DP"})
            df_export["DP"] = df_export["DP"].apply(lambda x: f"{x:.5f}".replace(".", ","))
            df_export.to_excel(writer, sheet_name='Resultados', index=False)

            workbook = writer.book
            worksheet = writer.sheets['Resultados']

            chart = workbook.add_chart({'type': 'line'})
            chart.add_series({
                'name': 'DP',
                'categories': ['Resultados', 1, 0, len(df_export), 0],
                'values': ['Resultados', 1, 1, len(df_export), 1],
                'marker': {'type': 'circle'},
            })
            chart.set_title({'name': 'Gráfico DP'})
            chart.set_x_axis({'name': 'Ciclos'})
            chart.set_y_axis({'name': 'DP'})
            worksheet.insert_chart('E2', chart)

        st.download_button("📥 Baixar resultados (Excel)", output.getvalue(),
                           "resultados_DP.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
