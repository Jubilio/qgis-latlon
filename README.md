# QGIS LatLon Plugin

**QGIS LatLon Plugin** é uma ferramenta leve e poderosa para capturar coordenadas clicadas no mapa dentro do QGIS. O plugin registra informações detalhadas como latitude, longitude, sistema de referência (EPSG), e a camada sob o ponto clicado, se existir.

## 🔧 Funcionalidades

- Captura coordenadas de cliques no mapa
- Armazena as coordenadas em uma camada vetorial de pontos
- Exibe popup com:
  - Latitude/Longitude
  - Coordenadas em DMS (graus, minutos, segundos)
  - Código EPSG do projeto
  - Nome da camada sob o clique (se houver)
- Copia coordenadas para a área de transferência
- Exporta pontos para CSV
- Exporta pontos para Shapefile ou GeoPackage (GPKG)
- Permite usar uma camada vetorial de pontos existente

## 📦 Instalação

1. Compacte a pasta `qgis-latlon` como um `.zip`, contendo:
   - `__init__.py`
   - `qgis_latlon.py`
   - `metadata.txt`
   - `icons/icon.png`

2. No QGIS, vá em:
   - `Plugins > Manage and Install Plugins > Install from ZIP`

3. Selecione o `.zip` e clique em `Install Plugin`

## 🚀 Como usar

1. Após instalar, clique no ícone `LatLon Click Capture` na barra de ferramentas
2. Clique no mapa para capturar coordenadas
3. Use o menu `Plugins > LatLon Plugin` para:
   - 📋 Copiar última coordenada para a área de transferência
   - 📄 Exportar para CSV
   - 🗂️ Exportar para Shapefile ou GeoPackage
   - 🔁 Selecionar camada existente para adicionar os próximos pontos

## 📂 Atributos salvos na camada

| Campo         | Descrição                                             |
|---------------|--------------------------------------------------------|
| `id`          | ID incremental do ponto                                |
| `lat`         | Latitude (graus decimais)                              |
| `lon`         | Longitude (graus decimais)                             |
| `epsg`        | Código EPSG do sistema de coordenadas do projeto       |
| `source_layer`| Nome da camada clicada (se aplicável)                 |

## 💡 Sugestões futuras (contribuições bem-vindas)

- Exportar como KML
- Visualização estilo tabela com edição direta
- Suporte a múltiplas capturas simultâneas

---

Criado por: Jubilio Mausse  
Licença: MIT  
Compatível com: QGIS 3.x ou superior