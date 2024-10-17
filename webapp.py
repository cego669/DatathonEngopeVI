import streamlit as st
import pandas as pd
import numpy as np
import dill
import plotly.express as px
import matplotlib.pyplot as plt
import shap
from sklearn.model_selection import train_test_split
import pydeck as pdk

############################################################### FUNÇÕES ÚTEIS
# função que calcula diferença entre max e min
def max_min_diff(x):
    return np.max(x) - np.min(x)

# Gerar texto explicativo com base nos valores SHAP
def gerar_explicacao_textual(feature_names, shap_values, baseline, probabilidade, sorted_indices):
    explicacao = []
    explicacao.append(f"O valor base (médio) de log-odds é de {baseline:.2f}, o que corresponde a uma probabilidade inicial de degradação igual a {sigmoid(baseline):.2%}.")
    
    base = baseline
    for i in sorted_indices:
        feature = feature_names[i]
        shap_value = shap_values[i]
        impacto = "aumentou" if shap_value > 0 else "diminuiu"
        base = base + shap_value
        explicacao.append(f"A variável '{feature}' {impacto} o log-odds em {abs(shap_value):.2f} unidades, o que fez a probabilidade se tornar {sigmoid(base):.2%}.")
    
    explicacao.append(f"Assim, a probabilidade final de que a pastagem está DEGRADADA é {probabilidade:.2%}.")
    return " ".join(explicacao)

# Função para converter log-odds para probabilidade
def sigmoid(x):
    return 1 / (1 + np.exp(-x))


############################################################### CARREGANDO VARIÁVEIS ÚTEIS
    
# carregando dados de referência
dados = pd.read_excel("dados/dados_escores_processados.xlsx")
dados_completos = dados.copy()
escores = [col for col in dados.columns if col not in ["Ponto", "PontoID", "Data", "Campo", "Equipe",
                                                       "Especie01", "Avaliador"]]
dados = dados.groupby("PontoID")[escores].agg(["mean", "min", "max", max_min_diff])
dados.columns = [col + "_" + func for col, func in zip(dados.columns.get_level_values(0), dados.columns.get_level_values(1))]

# carregando dados de classe
dados_classe = pd.read_excel("dados/dados_geoloc_classe.xlsx")
dados_classe.index = dados_classe["PontoID"]
dados_classe.drop(columns="PontoID", inplace=True)

# fazendo inner join entre tabelas (incluindo apenas as linhas com PontoID que possui classe)
dados = dados.join(dados_classe, how="inner")

# fazendo left join entre tabelas para os dados completos
dados_completos.index = dados_completos["PontoID"]
dados_completos.drop(columns="PontoID", inplace=True)
dados_completos = dados_completos.join(dados_classe, on="PontoID", how="left", lsuffix='_left', rsuffix='_right')

# dados de entrada e saída do modelo
y = (~dados["CLASS_DED"].isin(["Não degradada", "Degradação Baixa"])*1).values
X = dados.drop(columns=["CLASS_DED"] + [col for col in dados.columns\
                                        if "min" in col\
                                            or "max" in col\
                                                or "Degrad" in col\
                                                    or "Manejo" in col])

# dados de treino e dados de teste
X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=.3, random_state=667)

# carregando modelo de classificação
with open("dados/melhor_modelo.pk", "rb") as file:
    bs_model = dill.load(file)



############################################################### O APLICATIVO WEB COMEÇA AQUI
# seleção da seção
section = st.sidebar.selectbox("Section:", ["Predição da Degradação de Pastagens",
                                            "Mapa Temático",
                                            "Análise Descritiva",
                                            "Análise de Discordância entre Avaliadores"])

# texto da aba
st.sidebar.markdown("""               
Bem-vindo ao nosso aplicativo web desenvolvido para o primeiro Datathon do Engope! Aqui, você encontrará uma solução interativa e visual para análise de dados sobre a classificação de de degradação de pastagens. Nosso objetivo é proporcionar uma maneira prática e eficiente de explorar essas informações de maneira detalhada.
Utilizamos gráficos intuitivos e interativos, que facilitam a compreensão das características principais dos dados de pastagem. Além disso, disponibilizamos um mapa interativo que apresenta a posição e a classificação das pastagens, permitindo uma visualização geográfica clara e objetiva.
Outro destaque é o nosso modelo de predição, que prediz se a pastagem está degradada ou não. E para garantir a consistência das análises, incluímos uma breve avaliação da concordância entre os avaliadores, oferecendo uma visão sobre a qualidade das classificações.
Explore nosso aplicativo e descubra como esses recursos podem facilitar o entendimento e a exploração dos dados de pastagem!
""", unsafe_allow_html=True)

###################################### SEÇÃO: "Predição da Degradação de Pastagens"
if section == "Predição da Degradação de Pastagens":

    st.markdown("""
## 🌾 Predição da Degradação de Pastagens

O modelo de classificação utilizado foi o XGBoost, cujos hiperparâmetros foram otimizados usando o otimizador de Bayes e validação cruzada.
O modelo foi treinado para separar as pastagens entre a **classe positiva** (**DEGRADADA**: excluindo a classe Degradação Baixa) e a **classe negativa** (**NÃO DEGRADADA**: que agrupa as classes Degradação Baixa e Não degradada).

Como dados de entrada do modelo, foram utilizados os escores médios entre os avaliadores responsáveis pela pastagem. Foram excluídos os escores "Degrad" e "Manejo" por terem relação muito direta com a classe positiva ou negativa.

A performance do modelo nos dados de teste (30\% do total de pontos: 138 instâncias) foi:

- Classe pastagem 'DEGRADADA': Precisão = 100\%, Sensibilidade = 98.91\%, F1-score = 99.45\%
- Classe pastagem 'NÃO DEGRADADA': Precisão = 97.87\%, Sensibilidade = 100.00\%, F1-score = 98.92\%

Para testar as predições do modelo, você pode preencher o formulário abaixo e clicar em "Predizer". Após o clique, aparecerá o resultado da predição e a explicação da contribuição de cada variável para a probabilidade final da classe positiva. A explicação é baseada nos valores SHAP, provenientes da teoria dos jogos. Os valores SHAP buscam dividir a recompensa final de um "jogo" de acordo com a contribuição dos jogadores de uma mesma equipe.
    """)

    with st.form(key = "user_input"):
        st.markdown("""
        <h3 style='text-align: center;'>Dados de entrada</h3>
        """, unsafe_allow_html=True)
        
        altura = st.slider("Altura", X["Altura_mean"].min(), X["Altura_mean"].max(), X["Altura_mean"].mean(),
                                   format="%.1f", step=0.1)
        estdesenv = st.slider("EstDesenv (média entre avaliadores)", 1.0, 7.0, X["EstDesenv_mean"].mean(),
                                   format="%.1f", step=0.1)
        invasoras = st.slider("Invasoras (média entre avaliadores)", 1.0, 7.0, X["Invasoras_mean"].mean(),
                                   format="%.1f", step=0.1)
        cupins = st.slider("Cupins (média entre avaliadores)", 1.0, 7.0, X["Cupins_mean"].mean(),
                                   format="%.1f", step=0.1)
        cobertsolo = st.slider("CobertSolo (média entre avaliadores)", 1.0, 7.0, X["CobertSolo_mean"].mean(),
                                   format="%.1f", step=0.1)
        dispforr = st.slider("DispForr (média entre avaliadores)", 1.0, 7.0, X["DispForr_mean"].mean(),
                                   format="%.1f", step=0.1)
        dispfolhverd = st.slider("DispFolhVerd (média entre avaliadores)", 1.0, 7.0, X["DispFolhVerd_mean"].mean(),
                                   format="%.1f", step=0.1)
        condatual = st.slider("CondAtual (média entre avaliadores)", 1.0, 7.0, X["CondAtual_mean"].mean(),
                                   format="%.1f", step=0.1)
        potprod = st.slider("PotProd (média entre avaliadores)", 1.0, 7.0, X["PotProd_mean"].mean(),
                                   format="%.1f", step=0.1)

        predict = st.columns(5)[-1].form_submit_button("Predizer")

    if predict:
        # inicializando dados do usuário
        X_user = {}

        # inputs numéricos
        X_user["Altura_mean"] = [altura]
        X_user["EstDesenv_mean"] = [estdesenv]
        X_user["Invasoras_mean"] = [invasoras]
        X_user["Cupins_mean"] = [cupins]
        X_user["CobertSolo_mean"] = [cobertsolo]
        X_user["DispForr_mean"] = [dispforr]
        X_user["DispFolhVerd_mean"] = [dispfolhverd]
        X_user["CondAtual_mean"] = [condatual]
        X_user["PotProd_mean"] = [potprod]

        # convertendo dados do usuário para um DataFrame
        X_user = pd.DataFrame(X_user)
        
        # predizendo
        y_pred = bs_model.predict(X_user)

        if y_pred[0] == 1:
            success_text = f"A pastagem com os scores fornecidos foi predita como: DEGRADADA"
        else:
            success_text = f"A pastagem com os scores fornecidos foi predita como: NÃO DEGRADADA"

        # printando y_pred
        st.success(success_text, icon="🦉")

        # "explainer" do pacote shap (específico para árvores de decisão)
        shap_model = shap.TreeExplainer(bs_model.best_estimator_)

        # obtendo valores shap
        shap_values = shap_model.shap_values(X_user)

        # converter os shap_values para um objeto Explanation
        explainer = shap.Explanation(values=shap_values[0], base_values=shap_model.expected_value, data=X_user.iloc[0,:])

        # Calcular o valor logit final (soma do baseline com as contribuições das features)
        logit_value = explainer.base_values + sum(explainer.values)

        # Converter para probabilidade final
        probabilidade = sigmoid(logit_value)

        # gerar o waterfall_plot
        waterfall_plot = shap.waterfall_plot(explainer)

        # salvar o gráfico como uma imagem
        plt.gcf().set_size_inches(8, 6)
        plt.tight_layout()
        plt.savefig("shap_waterfall_plot.png")

        # Ordenar os índices dos valores SHAP por magnitude (impacto)
        sorted_indices = np.argsort(np.abs(shap_values[0]))

        # gerando texto explicativo junto ao plot
        st.markdown(f"""
        <h4 style='text-align: center;'>🕵️ Interpretando a predição (valores SHAP)</h4>
        
        {gerar_explicacao_textual(X_user.columns, shap_values[0], explainer.base_values, probabilidade, sorted_indices)}""", unsafe_allow_html=True)

        # mostrando imagem salva
        st.image("shap_waterfall_plot.png")

###################################### SEÇÃO: "Mapa Temático"
elif section == "Mapa Temático":

    y_pred = bs_model.predict(dados[[escore + "_mean" for escore in escores if "Degrad" not in escore and "Manejo" not in escore]])#DC0D2F
    dados["y_pred"] = y_pred
    dados["y_pred_class"] = dados["y_pred"].map({1: "DEGRADADA", 0: "NÃO DEGRADADA"})
    dados["color"] = dados["y_pred"].map({1: [255, 0, 0], 0: [0, 255, 0]})

    st.markdown(f"""
        <h4 style='text-align: center;'>🗺️ Mapa temático das predições do modelo</h4>
        
        O mapa temático mostrando a posição, identificação e o estado de degradação das pastagens conforme predito pelo modelo de classificação treinado está mostrado logo abaixo.""", unsafe_allow_html=True)

    # Crie um Layer de Scatterplot usando pydeck
    layer = pdk.Layer(
        'ScatterplotLayer',
        dados,
        get_position='[LON, LAT]',
        get_color='color',
        get_radius=1000,
        pickable=True,
    )

    # Configurações da visualização
    view_state = pdk.ViewState(
        latitude=dados['LAT'].mean(),
        longitude=dados['LON'].mean(),
        zoom=5.5,
        pitch=0,
    )

    # Renderize o mapa com pydeck
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"html": "<b>ID:</b> {Ponto} <br/> <b>Predição:</b> {y_pred_class}"}
    ))


###################################### SEÇÃO: "Análise Descritiva"
elif section == "Análise Descritiva":

    st.markdown(f"""
        <h3 style='text-align: center;'>📊 Análise Descritiva das variáveis</h3>
        
        <h4 style='text-align: center;'>Boxplot dos scores agrupados por classe de pastagem</h4>
                
        Note que, para o eixo x, a variável `CLASS_DED` corresponde às classes presentes em `dados_geoloc_classe.xlsx`, enquanto que
                a variável `y_pred_class` corresponde às predições do modelo de classificação treinado.""", unsafe_allow_html=True)


    y_pred = bs_model.predict(dados[[escore + "_mean" for escore in escores if "Degrad" not in escore and "Manejo" not in escore]])#DC0D2F
    dados["y_pred"] = y_pred
    dados["y_pred_class"] = dados["y_pred"].map({1: "DEGRADADA", 0: "NÃO DEGRADADA"})

    # y_col = st.selectbox("Variável do eixo y:", [escore + "_mean" for escore in escores] +\
    #                                             [escore + "_min" for escore in escores] +\
    #                                             [escore + "_max" for escore in escores] +\
    #                                             [escore + "_max_min_diff" for escore in escores])
    y_col = st.selectbox("Variável do eixo y:", [escore + "_mean" for escore in escores])
    x_col = st.selectbox("Variável do eixo x:", ["CLASS_DED", "y_pred_class"])
    fig = px.box(dados, x=x_col, y=y_col, points="all")
    st.plotly_chart(fig)


    st.markdown(f"""
        
        <h4 style='text-align: center;'>Scatterplot dos scores coloridos por classe de pastagem</h4>
                
        Note que, para a cor, a variável `CLASS_DED` corresponde às classes presentes em `dados_geoloc_classe.xlsx`, enquanto que
                a variável `y_pred_class` corresponde às predições do modelo de classificação treinado.""", unsafe_allow_html=True)
    y_col = st.selectbox(" Variável do eixo y:", [escore + "_mean" for escore in escores])
    x_col = st.selectbox(" Variável do eixo x:", [escore + "_mean" for escore in escores[::-1]])
    color_col = st.selectbox("Variável para a cor:", ["CLASS_DED", "y_pred_class"])
    fig = px.scatter(dados, x=x_col, y=y_col, color=color_col)
    st.plotly_chart(fig)


###################################### SEÇÃO: "Análise de Discordância entre Avaliadores"
elif section == "Análise de Discordância entre Avaliadores":

    st.markdown(f"""
        <h3 style='text-align: center;'>📊 Análise de Discordância entre Avaliadores</h3>
        
        <h4 style='text-align: center;'>Boxplot da diferença entre o escores máximo e mínimo para diferentes métricas</h4>""", unsafe_allow_html=True)


    y_pred = bs_model.predict(dados[[escore + "_mean" for escore in escores if "Degrad" not in escore and "Manejo" not in escore]])
    dados["y_pred"] = y_pred
    dados["y_pred_class"] = dados["y_pred"].map({1: "DEGRADADA", 0: "NÃO DEGRADADA"})

    dados_temp = dados[dados["DispFolhVerd_max_min_diff"] <= 6].melt(id_vars=["Ponto", "y_pred_class", "CLASS_DED"], value_vars=[escore + "_max_min_diff" for escore in escores])

    fig = px.box(dados_temp, x="variable", y="value")
    st.plotly_chart(fig)


    st.markdown(f"""
        <h4 style='text-align: center;'>Boxplot da diferença entre o escores máximo e mínimo para um escore considerando as diferentes classes de pastagem</h4>""", unsafe_allow_html=True)
    y_col = st.selectbox("Variável do eixo y:", [escore + "_max_min_diff" for escore in escores])
    x_col = st.selectbox("Variável do eixo x:", ["CLASS_DED", "y_pred_class"])
    fig = px.box(dados, x=x_col, y=y_col)
    st.plotly_chart(fig)