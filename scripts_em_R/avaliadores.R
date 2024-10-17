library(ggplot2)
library(readxl)
library(tidyverse)
library(dplyr)
library(modeest)
library(gridExtra)
library(caret)
library(rpart)
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

# Calculando a média e o desvio padrão
resultados <- dados %>%
  group_by(PontoID, Ponto) %>%
  reframe(across(7:16, #Colunas dos Escores
                 list(media = ~ mean(.x, na.rm = TRUE), #Media
                      sd = ~ sd(.x, na.rm = TRUE)), #Desvio Padrão
                 .names = "{.col}_{.fn}")) #Nomeando as colunas

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

# Ordenando os resultados pela data
resultado_ordenado <- resultados %>%
  arrange(desc(Data))  

gf1 <-ggplot(data = resultado_ordenado,aes(x=Data,y=CobertSolo_sd))+
  geom_point()+ggtitle("Gráfico 1: DP Avaliação Cobertura do Solo X TEMPO")

gf2 <-ggplot(data = resultado_ordenado,aes(x=Data,y=EstDesenv_sd))+
  geom_point()+ggtitle("Gráfico 2: DP Avaliação Estágio de desenvolvimento X TEMPO")

gf3 <-ggplot(data = resultado_ordenado,aes(x=Data,y=Invasoras_sd))+
  geom_point()+ggtitle("Gráfico 3: DP Avaliação Invasoras X TEMPO")

gf4 <-ggplot(data = resultado_ordenado,aes(x=Data,y=Cupins_sd))+
  geom_point()+ggtitle("Gráfico 4: DP Avaliação Cupins X TEMPO")

gf5 <-ggplot(data = resultado_ordenado,aes(x=Data,y=DispForr_sd))+
  geom_point()+ggtitle("Gráfico 5: DP Avaliação Forragem da Pastagem  X TEMPO")

gf6 <-ggplot(data = resultado_ordenado,aes(x=Data,y=DispFolhVerd_sd))+
  geom_point()+ggtitle("Gráfico 6: DP Avaliação Folhas Verdes X TEMPO")

gf7 <-ggplot(data = resultado_ordenado,aes(x=Data,y=CondAtual_sd))+
  geom_point()+ggtitle("Gráfico 7: DP Avaliação Condição Atual X TEMPO")

gf8 <-ggplot(data = resultado_ordenado,aes(x=Data,y=PotProd_sd))+
  geom_point()+ggtitle("Gráfico 8: DP Avaliação Potencial Produtivo X TEMPO")

gf9 <-ggplot(data = resultado_ordenado,aes(x=Data,y=Degrad_sd))+
  geom_point()+ggtitle("Gráfico 9: DP Avaliação Degradação X TEMPO")

gf10 <-ggplot(data = resultado_ordenado,aes(x=Data,y=Manejo_sd))+
  geom_point()+ggtitle("Gráfico 10: DP Avaliação Manejo X TEMPO")

#Grid dos gráficos gerados
grid.arrange(gf1,gf2,gf3,gf4,gf5,
             gf6,gf7,gf8,gf9,gf10,ncol = 2)

