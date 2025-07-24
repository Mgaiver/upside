import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import re
import io
import plotly.express as px

# --- FUNÇÕES DE PROCESSAMENTO E LIMPEZA ---

def clean_value(text_value):
    """Converte um valor monetário em texto (ex: 'R$ 1.275,34') para float."""
    if isinstance(text_value, str):
        text_value = text_value.replace('R$', '').strip()
        text_value = text_value.replace('.', '').replace(',', '.')
        try:
            return float(text_value)
        except (ValueError, TypeError):
            return 0.0
    return float(text_value)

def process_portfolio_image(image_file):
    """
    Usa OCR para extrair dados da imagem da carteira e retorna um DataFrame.
    """
    try:
        image = Image.open(image_file)
        # Configuração para OCR em português para melhor reconhecimento
        custom_config = r'--oem 3 --psm 6 -l por'
        text = pytesseract.image_to_string(image, config=custom_config)

        lines = text.strip().split('\n')
        
        portfolio_data = []
        # Regex para capturar as colunas principais: Ativo, Última Cotação, Posição
        # Este regex é robusto o suficiente para lidar com espaços variáveis
        line_regex = re.compile(r'([A-Z0-9]+)\s+.*\s+(R\$\s*[\d,\.]+)\s+(R\$\s*[\d,\.]+)')

        for line in lines:
            match = line_regex.search(line)
            if match and len(match.groups()) == 3:
                ativo, ultima_cotacao, posicao = match.groups()
                
                # Validação para evitar falsos positivos (como o cabeçalho)
                if ativo not in ["Ativo", "AURE3S", "BBAS3S"]:
                    portfolio_data.append({
                        'Ticker': ativo,
                        'Última Cotação': clean_value(ultima_cotacao),
                        'Posição (R$)': clean_value(posicao)
                    })

        if not portfolio_data:
            st.error("Nenhum dado de portfólio pôde ser extraído da imagem. Tente uma imagem mais nítida ou verifique a estrutura.")
            return pd.DataFrame()

        return pd.DataFrame(portfolio_data)
        
    except Exception as e:
        st.error(f"Erro ao processar a imagem: {e}")
        return pd.DataFrame()

def load_recommendations_from_excel(excel_file):
    """
    Carrega as recomendações de um arquivo Excel.
    Esta é uma função de simulação. Você precisará ajustá-la para o seu arquivo real.
    """
    try:
        # Tenta ler a planilha 'Recomendações'. Mude se o nome da aba for outro.
        reco_df = pd.read_excel(excel_file, sheet_name='Recomendações', engine='openpyxl')
        
        expected_cols = ['Ticker', 'Empresa', 'Setor', 'Recomendação', 'Preço Alvo (R$)']
        if not all(col in reco_df.columns for col in expected_cols):
            st.warning(f"A planilha 'Recomendações' não contém todas as colunas esperadas. Usando dados de simulação.")
            raise ValueError("Colunas não encontradas")
            
        return reco_df

    except Exception:
        st.info("Usando dados de simulação para a tabela de recomendações, pois o arquivo Excel não pôde ser lido ou não tem a estrutura esperada.")
        data = {
            'Ticker': ['AURE3', 'BBAS3', 'BBDC4', 'CPLE6', 'CXSE3', 'ITSA4', 'PETR4', 'PRIO3', 'VALE3', 'CSNA3', 'WEGE3', 'SIMH3', 'HASH11', 'IVVB11'],
            'Empresa': ['Auren Energia', 'Banco do Brasil', 'Bradesco', 'Copel', 'Caixa Seguridade', 'Itaúsa', 'Petrobras', 'Prio', 'Vale', 'CSN', 'WEG', 'Simpar', 'Hashdex Nasdaq Crypto', 'iShares S&P 500'],
            'Setor': ['Utilities Elétricas', 'Financeiro', 'Financeiro', 'Utilities Elétricas', 'Financeiro', 'Petróleo e Gás', 'Petróleo e Gás', 'Mineração', 'Mineração', 'Bens de Capital', 'Consumo Cíclico', 'Ativos Digitais', 'Internacional (ETF)'],
            'Recomendação': ['Compra', 'Compra', 'Neutro', 'Compra', 'Compra', 'Compra', 'Compra', 'Compra', 'Compra', 'Venda', 'Neutro', 'Compra', 'N/A', 'N/A'],
            'Preço Alvo (R$)': [15.00, 30.00, 18.00, 14.00, 16.00, 13.50, 40.00, 60.00, 80.00, 12.00, 40.00, 12.00, 100.00, 450.00]
        }
        return pd.DataFrame(data)

def generate_recommendation_text(analysis_df):
    """Gera um texto de recomendação personalizado para o cliente."""
    
    total_value = analysis_df['Posição (R$)'].sum()
    sector_allocation = analysis_df.groupby('Setor')['Posição (R$)'].sum().sort_values(ascending=False)
    sector_percent = (sector_allocation / total_value) * 100

    # Início do texto
    text = "Olá! Tudo bem?\n\n"
    text += "Fiz uma análise da sua carteira de investimentos com base nas nossas recomendações mais recentes e na alocação atual. Seguem os principais pontos:\n\n"

    # 1. Análise de Alocação Setorial
    text += "📊 **Alocação Setorial:**\n"
    top_sectors = sector_percent.head(3)
    for sector, percent in top_sectors.items():
        text += f"- **{sector}:** {percent:.1f}%\n"
    
    if top_sectors.iloc[0] > 35: # Alerta de concentração
        text += f"\nSua carteira apresenta uma concentração um pouco maior no setor de **{top_sectors.index[0]}**. Podemos avaliar estratégias para diversificar e mitigar riscos, se estiver de acordo com seu perfil.\n"

    text += "\n"

    # 2. Ativos com Recomendação de Compra
    compra_df = analysis_df[analysis_df['Recomendação'] == 'Compra'].sort_values(by='Potencial (%)', ascending=False)
    if not compra_df.empty:
        text += "👍 **Pontos Fortes e Oportunidades (Recomendação de Compra):**\n"
        for _, row in compra_df.iterrows():
            if row['Potencial (%)'] > 0:
                text += f"- **{row['Ticker']} ({row['Setor']}):** Mantemos uma visão positiva para o ativo, com um potencial de valorização de **{row['Potencial (%)']:.2f}%** em relação ao nosso preço-alvo de R$ {row['Preço Alvo (R$)']:.2f}.\n"
    
    text += "\n"

    # 3. Ativos para Reavaliar (Neutro ou Venda)
    reavaliar_df = analysis_df[analysis_df['Recomendação'].isin(['Neutro', 'Venda'])]
    if not reavaliar_df.empty:
        text += "⚠️ **Pontos de Atenção (Recomendação Neutra ou Venda):**\n"
        for _, row in reavaliar_df.iterrows():
            text += f"- **{row['Ticker']} ({row['Setor']}):** Nossa recomendação atual é **{row['Recomendação']}**. Seria interessante conversarmos sobre a possibilidade de realocar essa posição para ativos com maior potencial de crescimento no setor ou em outros setores estratégicos.\n"

    text += "\n"

    # 4. Sugestão Final
    text += "💡 **Próximos Passos:**\n"
    text += "Com base nesta análise, sugiro agendarmos uma conversa para discutirmos esses pontos e alinharmos a estratégia da sua carteira com seus objetivos e nosso cenário de mercado.\n\n"
    text += "Qualquer dúvida, estou à disposição.\n\n"
    text += "Abraço!"
    
    return text

# --- INTERFACE DO STREAMLIT ---

st.set_page_config(layout="wide", page_title="Analisador de Carteira de Clientes")

st.title("👨‍💼 Analisador de Carteira de Clientes")
st.markdown("Faça o upload da imagem da carteira do cliente e do Stock Guide em Excel para uma análise setorial e de recomendações.")

# --- Upload dos Arquivos ---
col1, col2 = st.columns(2)
with col1:
    image_file = st.file_uploader("1. Envie o Print da Carteira", type=['png', 'jpg', 'jpeg'])

with col2:
    excel_file = st.file_uploader("2. Envie o Stock Guide (Excel)", type=['xlsm', 'xlsx'])

if image_file and excel_file:
    # --- Processamento e Análise ---
    portfolio_df = process_portfolio_image(image_file)
    reco_df = load_recommendations_from_excel(excel_file)

    if not portfolio_df.empty and not reco_df.empty:
        analysis_df = pd.merge(portfolio_df, reco_df, on='Ticker', how='left')
        analysis_df['Setor'] = analysis_df['Setor'].fillna('Não Classificado')

        analysis_df['Preço Alvo (R$)'] = analysis_df['Preço Alvo (R$)'].fillna(0)
        analysis_df['Potencial (%)'] = ((analysis_df['Preço Alvo (R$)'] / analysis_df['Última Cotação']) - 1) * 100
        analysis_df['Potencial (%)'] = analysis_df['Potencial (%)'].where(analysis_df['Última Cotação'] > 0, 0)
        analysis_df['Potencial (%)'] = analysis_df['Potencial (%)'].fillna(0)

        st.header("📊 Análise da Carteira")

        total_portfolio_value = analysis_df['Posição (R$)'].sum()
        sector_allocation = analysis_df.groupby('Setor')['Posição (R$)'].sum().reset_index()
        sector_allocation['Percentual'] = (sector_allocation['Posição (R$)'] / total_portfolio_value) * 100

        fig = px.pie(sector_allocation, values='Posição (R$)', names='Setor', title='<b>Alocação Setorial da Carteira</b>',
                     hole=.3, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📄 Detalhamento por Ativo e Recomendações")

        for index, row in analysis_df.iterrows():
            st.markdown(f"---")
            ticker = row['Ticker']
            setor = row['Setor']
            
            posicao_formatada = f"R$ {row['Posição (R$)']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            cols_ativo = st.columns([1, 2, 2, 2])
            with cols_ativo[0]:
                st.markdown(f"### {ticker}")
            with cols_ativo[1]:
                st.metric("Posição na Carteira", posicao_formatada)
            with cols_ativo[2]:
                recomendacao = row.get('Recomendação', 'N/A')
                st.metric("Recomendação XP", recomendacao)
            with cols_ativo[3]:
                potencial = row.get('Potencial (%)', 0)
                st.metric("Potencial de Valorização", f"{potencial:.2f}%" if potencial and row['Preço Alvo (R$)'] > 0 else "N/A")

            if setor != 'Não Classificado' and setor != 'Ativos Digitais' and setor != 'Internacional (ETF)':
                oportunidades_df = reco_df[(reco_df['Setor'] == setor) & (reco_df['Ticker'] != ticker)].copy()

                if not oportunidades_df.empty:
                    with st.expander(f"Ver outras oportunidades no setor de **{setor}**"):
                        st.write(f"Comparando **{ticker}** com outros ativos recomendados pela XP no mesmo setor:")
                        st.table(oportunidades_df[['Ticker', 'Recomendação', 'Preço Alvo (R$)']])
        
        # --- Seção do Texto de Recomendação ---
        st.markdown("---")
        st.header("✉️ Texto de Recomendação para o Cliente")
        
        recommendation_text = generate_recommendation_text(analysis_df)
        
        st.text_area("Você pode copiar e ajustar o texto abaixo:", recommendation_text, height=450)
