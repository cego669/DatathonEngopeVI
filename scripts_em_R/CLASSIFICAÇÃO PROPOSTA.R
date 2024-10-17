library(ggplot2)
library(readxl)
library(tidyverse)
library(dplyr)
library(modeest)
library(gridExtra)
library(caret)
library(factoextra)

# Defina o diretório de trabalho
setwd("C:/Users/luisd/OneDrive/Área de Trabalho/DATATHON")

# Carregar os dados
dados <- read_xlsx("dados_escores_processados.xlsx")
dados.geologicos <- read.csv("dados_geoloc_classe.csv")
#Omitindo linhas com NA
dados <- na.omit(dados)
dados.geologicos<-na.omit(dados.geologicos)
# Convertendo a coluna Altura para character para obter a moda(correção de erro na construção dos dados)
dados$Altura <- as.character(dados$Altura)


# Função para calcular a moda
Mode <- function(x) {
  ux <- unique(x)
  ux[which.max(tabulate(match(x, ux)))]
}

#Substituindo as alturas pela respectiva moda
resultados_moda <- dados %>%
  group_by(PontoID, Ponto) %>%
  mutate(Altura = Mode(Altura))

#Calculando as médias e desvios
resultados <- resultados_moda %>%
  group_by(PontoID, Ponto) %>%
  reframe(across(7:16, 
                 list(media = ~ mean(.x, na.rm = TRUE), 
                      sd = ~ sd(.x, na.rm = TRUE)), 
                 .names = "{.col}_{.fn}"))

info_alturas <- resultados_moda %>% select(Ponto,Altura,PontoID)  %>% 
  distinct()

resultados <- inner_join(resultados, info_alturas, by = c("Ponto","PontoID"))

#observando a respectiva Espécie de acordo com os ID's
especie <- dados %>%
  select(PontoID,Ponto, Especie01) %>%
  distinct()

# Adicionando a coluna de espécies
resultados <- resultados %>%
  left_join(especie, by = c("Ponto","PontoID"))

resultados <- resultados %>% select(-PontoID)

#Observando a data respectiva para cada variável ID Ponto
df <- dados[,c(1,3)] %>%
  distinct(Ponto, .keep_all = TRUE)

# Fazendo o join dos resultados e a data
resultados <- inner_join(resultados, df, by = "Ponto")

#Definindo como data
resultados$Data <- as.Date(resultados$Data)

#Juntando o conjunto de dados com os dados de geolocalização
info_classe <- dados.geologicos %>% select(Ponto,CLASS_DED,PontoID)  %>% 
  distinct()

dados.xgboost <- inner_join(resultados, info_classe, by = c("Ponto"))
table(is.na(dados.xgboost))
dados.xgboost <- na.omit(dados.xgboost)
dados.xgboost$CLASS_DED <- as.factor(dados.xgboost$CLASS_DED)
dados.xgboost$Altura <- as.numeric(dados.xgboost$Altura)

dados.class<- dados.xgboost[,c(1,2,4,6,8,10,12,14,16,18,20,22)]
table(is.na(dados.class))

#Normalizando os dados
dados.class.padrao <- data.frame(Ponto = dados.class[,1],
                                 scale(dados.class[,-1]))

fviz_nbclust(dados.class.padrao[,-1], kmeans, method = "silhouette")

# Aplicar PCA
pca_result <- prcomp(dados.class.padrao[,-1], center = TRUE, scale. = TRUE)

# Explorar os resultados
summary(pca_result)  # Mostra a variância explicada por cada componente

#Número de componentes que explicam 90% dos dados
num_comps <- 5

# Extrair os componentes principais
pca_dados <- data.frame(pca_result$x[, 1:num_comps])

dados.pca <-data.frame(dados.xgboost$Ponto,pca_dados)

# Método do Cotovelo para encontrar o número ideal de clusters
fviz_nbclust(pca_dados, kmeans, method = "wss")

#5 variáveis
k <- 5
kmeans_result <- kmeans(pca_dados, centers = k, nstart = 25)

dados_clusterizado <- pca_dados %>%
  mutate(Cluster = kmeans_result$cluster)

#Testando a clusterização
dados.proposto <- data.frame(cluster = dados_clusterizado$Cluster,
                             dados.xgboost[,c(1,2,4,6,8,10,12,14,16,18,20,22)])

dados.proposto$cluster <- as.factor(dados.proposto$cluster)

#Grid das variáveis
max_grid<- expand.grid(nrounds = c(100,200,500),
                       max_depth = c(10,30), 
                       eta = c(0.1,0.3,0.6), 
                       gamma = c(0,1),
                       colsample_bytree = c(0.6,0.9),
                       min_child_weight =c(0,1),
                       subsample = c(0.6,0.9))

#Criando uma função para aplicação do XGBOOST com retorno da PRECISÃO
funcXGBOOST = function(data,params,indices){
  # Dividir os dados de treino e teste de acordo com os índices
  train_data = data[indices, ]
  test_data = data[-indices, ]
  
  xgb_model <- train(cluster ~ EstDesenv_media+Invasoras_media+
                       Cupins_media+CobertSolo_media+DispForr_media+
                       DispFolhVerd_media+CondAtual_media+
                       PotProd_media+Altura+Degrad_media+Manejo_media, 
                     data = train_data,
                     tuneGrid = params, #Parâmetros usados
                     method = "xgbTree")
  
  #Realizando a predição dos dados com o modelo gerado
  predicoes <- predict(xgb_model, newdata = test_data)
  confusao <- confusionMatrix(predicoes, test_data$cluster)
  print(varImp(xgb_model))
  return(confusao$overall['Accuracy'])
}

# Executar a validação cruzada
set.seed(123)
folds <- createFolds(dados.proposto$cluster, k = 5)

# Inicializar as variáveis com escopo global
cv_precisao_predict = c()

params <- max_grid[1,]

for (fold in 1:length(folds)) {
  indices_treino <- folds[[fold]]
  
  # Envolver a função customQuantileRF em um bloco tryCatch
  tryCatch({
    # Chamar a função e obter as métricas
    metrics <- funcXGBOOST(dados.proposto,params,indices_treino)
    
    # Armazenar os resultados se não houver erro
    cv_precisao_predict <<- c(cv_precisao_predict, metrics)
    
    
  }, error = function(e) {
    # Tratar erros: exibir a mensagem de erro e continuar
    cat("Erro na iteração do fold:", fold)
    cat("Mensagem de erro:", e$message, "\n")
    
    # Preencher as métricas com um valor padrão em caso de erro
    cv_precisao_predict <- c(cv_precisao_predict, NA)
  })
  
}
mean(cv_precisao_predict)


