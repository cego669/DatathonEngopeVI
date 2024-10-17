library(ggplot2)
library(readxl)
library(tidyverse)
library(dplyr)
library(modeest)
library(gridExtra)
library(caret)
library(rpart)
library(rpart.plot)
library(xgboost)
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
#Grid das variáveis
max_grid<- expand.grid(nrounds = c(100),
                       max_depth = c(10), 
                       eta = c(0.3), 
                       gamma = c(0),
                       colsample_bytree = c(0.9),
                       min_child_weight =c(0),
                       subsample = c(0.9))

#Criando uma função para aplicação do XGBOOST com retorno da PRECISÃO
funcXGBOOST = function(data,params,indices){
  # Dividir os dados de treino e teste de acordo com os índices
  train_data = data[indices, ]
  test_data = data[-indices, ]
  
  xgb_model <- train(CLASS_DED ~ EstDesenv_media+Invasoras_media+
                       Cupins_media+CobertSolo_media+DispForr_media+
                       DispFolhVerd_media+CondAtual_media+
                       PotProd_media+Altura+Degrad_media+Manejo_media, 
                     data = train_data,
                     tuneGrid = params, #Parâmetros usados
                     method = "xgbTree")
  
  #Realizando a predição dos dados com o modelo gerado
  predicoes <- predict(xgb_model, newdata = test_data)
  confusao <- confusionMatrix(predicoes, test_data$CLASS_DED)
  xgb.plot.importance(xgb_model)
  return(confusao$overall['Accuracy'])
}

# Executar a validação cruzada
set.seed(123)
folds <- createFolds(dados.xgboost$CLASS_DED, k = 5)

# Inicializar as variáveis com escopo global
cv_precisao_predict = c()

params <- max_grid[1,]
for (fold in 1:length(folds)) {
  indices_treino <- folds[[fold]]
  
  # Envolver a função customQuantileRF em um bloco tryCatch
  tryCatch({
    # Chamar a função e obter as métricas
    metrics <- funcXGBOOST(dados.xgboost,params,indices_treino)
    
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


