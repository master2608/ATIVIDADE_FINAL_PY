import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Ensino Superior", layout="wide", page_icon="📚")


@st.cache_data
def carregar_dados(caminho_arquivo):
    # Carrega o ponteiro do arquivo Excel com eficiência
    xls = pd.ExcelFile(caminho_arquivo)

    # Filtra as abas de interesse
    abas_anos = [sheet for sheet in xls.sheet_names if "(CV)" not in sheet]

    nomes = {
        "Total": "Todas as áreas",
        "Ciência, Tecnologia, Engenharias e Matemática": "Exatas",
        "Educação, Serviços pessoais, Saúde e Bem-estar": "Humanas e Saúde",
    }

    dados_totais = []

    for ano in abas_anos:
        # Otimizado: Usar xls.parse é mais rápido que pd.read_excel dentro do loop
        df_raw = xls.parse(sheet_name=ano, header=None)

        # Seguro: Remove espaços extras antes de buscar e evita crash caso não ache
        df_raw_strings = df_raw.iloc[:, 0].astype(str).str.strip()
        filtro_brasil = df_raw[df_raw_strings == "Brasil"].index

        if len(filtro_brasil) == 0:
            continue  # Pula a aba se não encontrar a linha do Brasil, evitando quebrar o app
        start_idx = filtro_brasil[0]

        # Cada área ocupa 3 colunas (Total, Homem, Mulher)
        for i in range(1, df_raw.shape[1], 3):
            area = str(df_raw.iloc[1, i]).strip()
            if area in ["nan", "", "None"]:
                continue

            # Extrai as 4 colunas necessárias da iteração atual
            df_ano = df_raw.iloc[start_idx:, [0, i, i + 1, i + 2]].copy()
            df_ano.columns = ["Localidade", "Total", "Homem", "Mulher"]

            # Limpeza de linhas vazias na localidade
            df_ano["Localidade"] = df_ano["Localidade"].astype(str).str.strip()
            df_ano = df_ano[~df_ano["Localidade"].isin(["", "nan", "None"])]

            # Converter colunas numéricas de uma vez só (Vetorizado/Mais rápido)
            for col in ["Total", "Homem", "Mulher"]:
                df_ano[col] = pd.to_numeric(df_ano[col], errors="coerce")

            # Remove linhas que não possuem dados em "Total" (ex: notas de rodapé)
            df_ano = df_ano.dropna(subset=["Total"])

            # Adiciona metadados
            df_ano["Area"] = nomes.get(area, area)
            df_ano["Ano"] = str(ano).strip()

            dados_totais.append(df_ano)

    # CORREÇÃO CRÍTICA: Junta tudo em um único DataFrame e retorna
    if dados_totais:
        return pd.concat(dados_totais, ignore_index=True)
    return pd.DataFrame()  # Retorna dataframe vazio caso não encontre dados


    # Consolida os dados de todos os anos disponíveis
    df_completo = pd.concat(dados_totais, ignore_index=True)
    return df_completo


# Caminho do arquivo
caminho_arquivo = r"Tabela_3_Areas_gerais_de_formacao_na_graduacao.xlsx"
df = carregar_dados(caminho_arquivo)

# Tabela de sexo (bloco "Todas as áreas")
df_sexo = df[df["Area"] == "Todas as áreas"][["Localidade", "Total", "Homem", "Mulher"]]

# Tabela de áreas (uma coluna por área, com o Total de cada uma)
df_area = df.pivot_table(index="Localidade", columns="Area", values="Total").reset_index()


# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("🔍 Filtros")

generos_selecionados = st.sidebar.multiselect(
    "Selecione o sexo:",
    options=["Homem", "Mulher"],
    default=["Homem", "Mulher"],
)

areas_selecionadas = st.sidebar.multiselect(
    "Selecione as áreas:",
    options=["Exatas", "Humanas e Saúde"],
    default=["Exatas", "Humanas e Saúde"],
)

localidades_disponiveis = df["Localidade"].unique().tolist()
localidades_selecionadas = st.sidebar.multiselect(
    "Selecione as UFs:",
    options=localidades_disponiveis,
    default=[
        "Minas Gerais",
        "Espírito Santo",
        "São Paulo",
        "Paraná",
        "Mato Grosso do Sul",
    ],
)


st.title("📊 Áreas gerais de formação na graduação")
st.markdown(
    "Pessoas com nível superior completo, por áreas gerais de formação do curso graduação concluído, segundo o sexo."
)

if not localidades_selecionadas:
    st.warning("Selecione ao menos uma UF na barra lateral.")
else:

    st.subheader("📈 Pessoas por sexo")

    df_sexo_filtrado = df_sexo[df_sexo["Localidade"].isin(localidades_selecionadas)]
    st.dataframe(df_sexo_filtrado.reset_index(drop=True), use_container_width=True)

    if generos_selecionados:
        df_melted = df_sexo_filtrado.melt(
            id_vars=["Localidade"],
            value_vars=generos_selecionados,
            var_name="Sexo",
            value_name="Total de pessoas",
        )

        fig_bar = px.bar(
            df_melted,
            x="Localidade",
            y="Total de pessoas",
            color="Sexo",
            barmode="group",
            title="Pessoas por sexo",
            color_discrete_sequence=["#1f77b4", "#e377c2"],
            labels={"Total de pessoas": "Pessoas", "Localidade": "UF"},
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")


    st.subheader("Pessoas por área de formação")

    df_area_filtrado = df_area[df_area["Localidade"].isin(localidades_selecionadas)]
    st.dataframe(df_area_filtrado.reset_index(drop=True), use_container_width=True)

    if areas_selecionadas:
        df_melted_area = df_area_filtrado.melt(
            id_vars=["Localidade"],
            value_vars=areas_selecionadas,
            var_name="Área",
            value_name="Total de pessoas",
        )

        fig_area = px.bar(
            df_melted_area,
            x="Localidade",
            y="Total de pessoas",
            color="Área",
            barmode="group",
            title="Pessoas por área de formação",
            labels={"Total de pessoas": "Pessoas", "Localidade": "UF"},
        )
        st.plotly_chart(fig_area, use_container_width=True)


        st.title("Perguntas:")
        st.markdown("Como a população com nível superior está distribuída nos estados do Sudeste?")
        st.caption("Na região sudeste possuem mais mulheres com nivel superior do que homens")
        st.divider()
        st.markdown("Qual a evolução histórica dessa taxa nos estados individualmente e no total consolidado?")
        st.caption("A pesquisa não possui evolução histórica pois possui apenas 1 ano de dados")
        st.divider()
        st.markdown("Qual o percentual de mulheres ingressantes e diplomadas em Cursos de Exatas versus Cursos de Humanas (por estado e no total)?")
        st.caption("Não é possível calcular o percentual porque os dados de sexo e de área de formação estão em tabelas separadas e não se cruzam.")