# Equipe Embrapeiros: Datathon, VI ENGOPE

### 🎯 Motivação

A motivação do que preparamos para o Datathon do VI ENGOPE foi de atender ao objetivo geral de propor uma classificação de níveis de degradação (mostrando também um mapa temático para as mesmas) para as pastagens localizadas no estado de Goiás assim como de fornecer uma plataforma interativa com o qual o público possa analisar e explorar os dados disponíveis.

Assim, desenvolvemos um aplicativo web usando o pacote `streamlit` do `Python` de modo a tornar possível a requisição de predições por parte dos usuários e a disponibilidade de vários gráficos interativos, cujas variáveis podem ser alteradas conforme o desejo do usuário.

As seções incluídas no aplicativo web foram:

- **Predição da Degradação de Pastagens**: inclui informações sobre o modelo de classificação treinado sobre os dados disponíveis assim como um formulário que permite ao usuário obter as predições do modelo de acordo com diferentes valores para os escores. Com o usuário clicando em "Predizer", ele terá acesso também aos valores SHAP correspondentes (juntamente com um texto explicativo) mostrando como cada escore contribuiu para o aumento ou diminuição da probabilidade para a classe de degradação da pastagem.

- **Mapa temático das predições do modelo**: inclui um mapa mostrando como cada ponto disponível no conjunto de dados é classificado pelo modelo de predição, com verde representando pastagens não degradadas e vermelho, pastagens degradadas.

- **Análise Descritiva**: inclui formas de visualização (boxplot e scatterplot) que permitem analisar como cada escore (ou par de escores) se relaciona com as classes de degradação de pastagem.

- **Análise de Discordância entre Avaliadores**: inclui formas de visualização (boxplots principalmente) que permitem analisar quais escores apresentaram as maiores diferenças (diferença entre avaliação máxima e mínima) para os diferentes escores, destrinchando se há relação com as classes de degradação.

O aplicativo web pode ser acessado pelo seguinte site: [https://datathonengopevi.streamlit.app/](https://datathonengopevi.streamlit.app/).