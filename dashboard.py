import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Ensino Superior", layout="wide", page_icon="📚")


@st.cache_data
def carregar_dados(caminho_arquivo):
    # Carrega o arquivo Excel
    xls = pd.ExcelFile(caminho_arquivo)

    # Ignora as abas de Coeficiente de Variação
    abas_anos = [sheet for sheet in xls.sheet_names if "(CV)" not in sheet]

    nomes = {
        "Total": "Todas as áreas",
        "Ciência, Tecnologia, Engenharias e Matemática": "Exatas",
        "Educação, Serviços pessoais, Saúde e Bem-estar": "Humanas e Saúde",
    }

    dados_totais = []

    for ano in abas_anos:
        df_raw = xls.parse(sheet_name=ano, header=None)

        # Procura a linha do Brasil
        primeira_coluna = df_raw.iloc[:, 0].astype(str).str.strip()
        filtro_brasil = df_raw[primeira_coluna == "Brasil"].index

        if len(filtro_brasil) == 0:
            continue

        start_idx = filtro_brasil[0]

        # Cada área ocupa três colunas: Total, Homem e Mulher
        for i in range(1, df_raw.shape[1], 3):
            if i + 2 >= df_raw.shape[1]:
                continue

            area = str(df_raw.iloc[1, i]).strip()
            if area in ["nan", "", "None"]:
                continue

            df_ano = df_raw.iloc[start_idx:, [0, i, i + 1, i + 2]].copy()
            df_ano.columns = ["Localidade", "Total", "Homem", "Mulher"]

            # Remove localidades vazias
            df_ano["Localidade"] = df_ano["Localidade"].astype(str).str.strip()
            df_ano = df_ano[
                ~df_ano["Localidade"].isin(["", "nan", "None"])
            ]

            # Converte os valores para números
            for coluna in ["Total", "Homem", "Mulher"]:
                df_ano[coluna] = pd.to_numeric(
                    df_ano[coluna], errors="coerce"
                )

            # Remove linhas sem valor na coluna Total
            df_ano = df_ano.dropna(subset=["Total"])

            df_ano["Area"] = nomes.get(area, area)
            df_ano["Ano"] = str(ano).strip()

            dados_totais.append(df_ano)

    if dados_totais:
        return pd.concat(dados_totais, ignore_index=True)

    return pd.DataFrame()


# Caminho do arquivo
caminho_arquivo = "Tabela_3_Areas_gerais_de_formacao_na_graduacao.xlsx"
df = carregar_dados(caminho_arquivo)

if df.empty:
    st.error("Não foram encontrados dados válidos no arquivo Excel.")
    st.stop()


# Tabela de sexo (bloco "Todas as áreas")
df_sexo = df[df["Area"] == "Todas as áreas"][
    ["Localidade", "Total", "Homem", "Mulher"]
]

# Tabela de áreas, com o total de cada uma
df_area = df.pivot_table(
    index="Localidade",
    columns="Area",
    values="Total",
).reset_index()


# Calcula o percentual de mulheres diplomadas por ano, localidade e área
areas_genero = ["Exatas", "Humanas e Saúde"]

df_percentual_mulheres = (
    df[df["Area"].isin(areas_genero)]
    .groupby(["Ano", "Localidade", "Area"], as_index=False)[
        ["Mulher", "Total"]
    ]
    .sum(min_count=1)
)

df_percentual_mulheres = df_percentual_mulheres.dropna(
    subset=["Mulher", "Total"]
)
df_percentual_mulheres = df_percentual_mulheres[
    df_percentual_mulheres["Total"] > 0
]

df_percentual_mulheres["Percentual de mulheres (%)"] = (
    df_percentual_mulheres["Mulher"]
    / df_percentual_mulheres["Total"]
    * 100
)


# --- BARRA LATERAL ---
st.sidebar.header("🔍 Filtros")

generos_selecionados = st.sidebar.multiselect(
    "Selecione o sexo:",
    options=["Homem", "Mulher"],
    default=["Homem", "Mulher"],
)

areas_selecionadas = st.sidebar.multiselect(
    "Selecione as áreas:",
    options=areas_genero,
    default=areas_genero,
)

localidades_disponiveis = sorted(df["Localidade"].dropna().unique().tolist())

localidades_padrao = [
    "Minas Gerais",
    "Espírito Santo",
    "São Paulo",
    "Paraná",
    "Mato Grosso do Sul",
]
localidades_padrao = [
    localidade
    for localidade in localidades_padrao
    if localidade in localidades_disponiveis
]

localidades_selecionadas = st.sidebar.multiselect(
    "Selecione as UFs:",
    options=localidades_disponiveis,
    default=localidades_padrao,
)


# --- CORPO DA APLICAÇÃO ---
st.title("📊 Áreas gerais de formação na graduação")
st.markdown(
    "Pessoas com nível superior completo, por áreas gerais de formação "
    "do curso de graduação concluído, segundo o sexo."
)

if not localidades_selecionadas:
    st.warning("Selecione ao menos uma UF na barra lateral.")
else:
    st.subheader("📈 Pessoas por sexo")

    df_sexo_filtrado = df_sexo[
        df_sexo["Localidade"].isin(localidades_selecionadas)
    ]

    st.dataframe(
        df_sexo_filtrado.reset_index(drop=True),
        use_container_width=True,
    )

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
            labels={
                "Total de pessoas": "Pessoas",
                "Localidade": "UF",
            },
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Box plot da distribuição de pessoas por sexo
        fig_box_sexo = px.box(
            df_melted,
            x="Sexo",
            y="Total de pessoas",
            color="Sexo",
            points="all",
            title="Distribuição de pessoas por sexo",
            labels={
                "Sexo": "Sexo",
                "Total de pessoas": "Pessoas",
            },
        )
        st.plotly_chart(fig_box_sexo, use_container_width=True)

    st.markdown("---")
    st.subheader("Pessoas por área de formação")

    df_area_filtrado = df_area[
        df_area["Localidade"].isin(localidades_selecionadas)
    ]

    st.dataframe(
        df_area_filtrado.reset_index(drop=True),
        use_container_width=True,
    )

    areas_disponiveis = [
        area
        for area in areas_selecionadas
        if area in df_area_filtrado.columns
    ]

    if areas_disponiveis:
        df_melted_area = df_area_filtrado.melt(
            id_vars=["Localidade"],
            value_vars=areas_disponiveis,
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
            labels={
                "Total de pessoas": "Pessoas",
                "Localidade": "UF",
            },
        )
        st.plotly_chart(fig_area, use_container_width=True)

        # Box plot da distribuição de pessoas por área de formação
        fig_box_area = px.box(
            df_melted_area,
            x="Área",
            y="Total de pessoas",
            color="Área",
            points="all",
            title="Distribuição de pessoas por área de formação",
            labels={
                "Área": "Área de formação",
                "Total de pessoas": "Pessoas",
            },
        )
        st.plotly_chart(fig_box_area, use_container_width=True)

    st.markdown("---")
    st.subheader("👩 Percentual de mulheres diplomadas por área")

    # Exibe somente os cinco estados solicitados
    localidades_percentual = [
        "Minas Gerais",
        "Espírito Santo",
        "São Paulo",
        "Paraná",
        "Mato Grosso do Sul",
    ]

    df_percentual_filtrado = df_percentual_mulheres[
        df_percentual_mulheres["Localidade"].isin(localidades_percentual)
        & df_percentual_mulheres["Area"].isin(areas_selecionadas)
    ].copy()

    if not df_percentual_filtrado.empty:
        df_percentual_filtrado["Percentual de mulheres (%)"] = (
            df_percentual_filtrado["Percentual de mulheres (%)"].round(2)
        )

        # A coluna Ano não é exibida na tabela
        tabela_percentual = df_percentual_filtrado[
            [
                "Localidade",
                "Area",
                "Mulher",
                "Total",
                "Percentual de mulheres (%)",
            ]
        ].rename(
            columns={
                "Localidade": "Estado / total",
                "Area": "Área",
                "Mulher": "Mulheres diplomadas",
                "Total": "Total de diplomados",
            }
        )

        st.dataframe(
            tabela_percentual.reset_index(drop=True),
            use_container_width=True,
        )

        # O gráfico também não é separado por ano
        fig_percentual = px.bar(
            df_percentual_filtrado,
            x="Localidade",
            y="Percentual de mulheres (%)",
            color="Area",
            barmode="group",
            title="Percentual de mulheres entre os diplomados por área",
            labels={
                "Localidade": "Estado / total",
                "Area": "Área",
                "Percentual de mulheres (%)": "Mulheres (%)",
            },
        )
        fig_percentual.update_traces(
            texttemplate="%{y:.1f}%",
            textposition="outside",
        )
        fig_percentual.update_yaxes(
            ticksuffix="%",
            rangemode="tozero",
        )
        st.plotly_chart(fig_percentual, use_container_width=True)
    else:
        st.info("Não há dados para as áreas e localidades selecionadas.")


# --- PERGUNTAS E RESPOSTAS ---
st.markdown("---")
st.title("Perguntas e respostas")

st.markdown(
    "**Pergunta 1:** Como a população com nível superior está distribuída "
    "nos estados do Sudeste?"
)
st.write(
    "**Resposta:** Os dados mostram a quantidade de pessoas por localidade "
    "e sexo, permitindo comparar a distribuição entre homens e mulheres. "
    "Use a tabela e os gráficos acima para consultar os estados selecionados."
)

st.divider()

st.markdown(
    "**Pergunta 2:** Qual é a evolução histórica dessa taxa nos estados "
    "individualmente e no total consolidado?"
)
st.write(
    "**Resposta:** A evolução histórica depende da disponibilidade de dados "
    "de mais de um ano nas abas da planilha. O código mantém o ano nos dados "
    "para os cálculos, mas não o exibe na tabela nem separa o gráfico por ano."
)

st.divider()

st.markdown(
    "**Pergunta 3:** Qual é o percentual de mulheres diplomadas em Cursos "
    "de Exatas versus Cursos de Humanas e Saúde, por estado?"
)
st.write(
    "**Resposta:** O percentual é calculado dividindo o número de mulheres "
    "diplomadas pelo total de diplomados na área e multiplicando o resultado "
    "por 100. A tabela e o gráfico mostram esse percentual para Exatas e "
    "Humanas e Saúde nos estados selecionados."
)

st.divider()

st.markdown(
    "**Pergunta 4:** A planilha inclui dados de mulheres ingressantes?"
)
st.write(
    "**Resposta:** Não. A planilha contém dados de pessoas com nível "
    "superior completo, mas não de ingressantes. Para calcular o percentual "
    "de mulheres ingressantes por área e estado, é necessária uma base com "
    "dados de ingressantes por sexo, área e localidade."
)


# --- NOTÍCIA RELACIONADA ---
st.markdown("---")
st.header("📰 Notícia relacionada")
st.subheader("ENEM 2026: mulheres são quase 64% dos inscritos")

imagem_noticia = st.text_input(
    "Imagem Ilustrativa",
    value="https://varginhadigital.com.br/wp-content/uploads/2025/05/enem.jpg",
    placeholder="https://exemplo.com/imagem-enem.jpg",
)

if imagem_noticia:
    st.image(
        imagem_noticia,
        use_container_width=True,
    )
else:
    st.info("Cole o link direto da imagem no campo acima para exibi-la.")

st.markdown("""
A presença feminina segue predominante entre os participantes do Exame Nacional do Ensino Médio (Enem) 2026. As mulheres representam quase 64% das inscrições confirmadas, segundo dados do Painel Enem 2026, divulgado pelo Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (Inep), vinculado ao Ministério da Educação (MEC).

O percentual supera o registrado em 2025, quando as mulheres correspondiam a 60% dos inscritos. A diferença de aproximadamente quatro pontos percentuais evidencia uma mudança na composição dos participantes e reforça a importância do exame para quem busca ingressar no ensino superior.

Além da participação feminina, os dados apresentam informações sobre a quantidade de candidatos e o perfil de quem pretende realizar a avaliação. Ao todo, o Enem 2026 ultrapassou a marca de 5 milhões de inscrições confirmadas, um crescimento próximo de 5% em relação ao ano anterior.

### Enem 2026 registra mais de 5 milhões de inscrições

O total de inscrições confirmadas no Enem 2026 também apresentou crescimento. De acordo com os números divulgados, o exame ultrapassou 5 milhões de participantes, uma alta de quase 5% em comparação com 2025.

A quantidade de inscritos é um indicador relevante para acompanhar a procura pela avaliação e o interesse da população em processos de acesso à universidade.

A nota do Enem pode ser utilizada em diferentes iniciativas de ingresso no ensino superior, conforme os critérios de cada programa e instituição.

Entre as possibilidades estão o Sistema de Seleção Unificada (Sisu), o Programa Universidade para Todos (Prouni) e o Fundo de Financiamento Estudantil (Fies), que possuem regras específicas de participação.

Também há instituições de ensino que utilizam o desempenho no exame em seus próprios processos seletivos. Por isso, conhecer as possibilidades de utilização da nota é importante para os candidatos que desejam transformar a participação na prova em uma oportunidade de formação acadêmica.

### Como consultar os dados do Painel Enem 2026?

O Painel Enem 2026 reúne informações sobre os participantes e permite observar a distribuição das inscrições por estado e município, além de outros recortes relacionados ao perfil dos candidatos.

A consulta pode ser feita diretamente no Painel Enem 2026. Os dados também oferecem uma visão mais ampla da participação no Enem e das diferenças observadas entre as edições.

Para interpretar os resultados corretamente, é importante considerar os números apresentados pelo Instituto e evitar conclusões que não sejam sustentadas pelas informações disponíveis.

### Quando serão aplicadas as provas do Enem 2026?

As provas do Enem 2026 estão previstas para os dias 8 e 15 de novembro, em dois domingos consecutivos.

Conforme o cronograma informado, os portões serão abertos às 12h e fechados às 13h, enquanto o início das avaliações está previsto para as 13h30, considerando o horário de Brasília.

Os participantes devem conferir o endereço de aplicação no Cartão de Confirmação da Inscrição, disponível na Página do Participante. O acesso é realizado com a conta Gov.br.

O documento informa o local da prova e outros dados importantes para a realização do exame. Consultá-lo com antecedência ajuda a organizar o deslocamento e diminui o risco de imprevistos.

Na reta final de preparação, também é recomendável revisar os conteúdos, conferir as orientações oficiais e planejar a chegada ao local com tempo suficiente.

### Quer fazer faculdade? Conheça as bolsas de estudo do Educa Mais Brasil

O Enem pode ampliar as possibilidades de ingresso no ensino superior, mas quem deseja cursar uma graduação também pode pesquisar outras formas de acesso à faculdade.

O Educa Mais Brasil oferece bolsas de estudo em instituições parceiras, com descontos nas mensalidades de cursos de graduação. A iniciativa pode ser uma alternativa para quem não pretende utilizar a nota do Enem, não atende aos critérios de determinados programas governamentais ou procura economizar durante a formação.

Os interessados podem consultar as oportunidades disponíveis, comparar cursos e instituições e verificar as condições de cada bolsa antes de se inscrever.

Assim, quem deseja começar uma faculdade pode avaliar diferentes caminhos para conquistar um diploma e investir no próprio futuro profissional, considerando as opções que melhor se encaixam em seus objetivos e orçamento.
""")