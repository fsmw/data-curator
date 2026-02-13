# 📊 ANÁLISIS DE DATASETS DE MORTALIDAD - MISES DATA CURATOR

## 🎯 Datasets Disponibles

### 1. **Mortalidad por Enfermedades Cardiovasculares** (2021)
- **Cobertura**: 192 países
- **Métrica**: Tasa de mortalidad estandarizada por edad (por 100,000)
- **Rango**: 60.1 - 694.3 muertes/100k
- **Promedio global**: 248.5 muertes/100k

#### Top 5 Países con Mayor Tasa:
1. Nauru: 694.3
2. Solomon Islands: 566.1
3. Uzbekistán: 512.9
4. Vanuatu: 512.0
5. Micronesia: 500.6

---

### 2. **Muertes por Conflictos Armados Acumuladas** (hasta 2024)
- **Cobertura**: Datos globales por región
- **Total mundial acumulado**: 3,929,873 muertes
- **Distribución regional**:
  - 🔴 **África**: 2,024,624 (51.5%)
  - 🔴 **Oriente Medio**: 717,805 (18.3%)
  - 🟡 **Asia y Oceanía**: 584,840 (14.9%)
  - 🟡 **Europa**: 372,315 (9.5%)
  - 🟢 **Américas**: 230,289 (5.9%)

#### Desglose por Tipo de Conflicto (Acumulado):
- **Conflictos intraestatales**: 1,985,756 (50.5%)
- **Violencia unilateral**: 1,183,039 (30.1%)
- **Conflictos no estatales**: 381,809 (9.7%)
- **Conflictos interestatales**: 379,269 (9.7%)

---

### 3. **Muertes por Terrorismo** (2021)
- **Cobertura**: 57 países afectados
- **Total global**: 11,528 muertes
- **Distribución regional**:
  - 🔴 **Asia**: 6,488 (56.3%)
  - 🔴 **África**: 4,872 (42.3%)
  - 🟡 **Américas**: 152 (1.3%)
  - 🟢 **Europa**: 16 (0.1%)

#### Top 5 Países Afectados:
1. Afganistán: 4,337
2. Nigeria: 1,493
3. Yemen: 859
4. R.D. Congo: 689
5. Etiopía: 488

---

## 📈 GRÁFICOS RECOMENDADOS

### **Categoría 1: Enfermedades Cardiovasculares**

#### 1️⃣ Mapa de Calor Global
- **Tipo**: Mapa coroplético
- **Variable**: Tasa de mortalidad por país (2021)
- **Utilidad**: Identificar patrones geográficos de riesgo cardiovascular
- **Insightsposibles**: Correlación con desarrollo económico, sistemas de salud

#### 2️⃣ Top 20 Países - Gráfico de Barras Horizontal
- **Tipo**: Bar chart horizontal
- **Variable**: Tasa de mortalidad cardiovascular
- **Utilidad**: Comparación clara entre países de alto riesgo
- **Color**: Degradado de rojo (alto) a verde (bajo)

#### 3️⃣ Distribución de Tasas por Región
- **Tipo**: Box plot o violín plot
- **Variable**: Agrupación por región (Africa, Asia, Europa, etc.)
- **Utilidad**: Entender dispersión regional y variabilidad

---

### **Categoría 2: Conflictos Armados**

#### 4️⃣ Muertes Acumuladas por Región
- **Tipo**: Gráfico de Barras o Donut/Pie
- **Variable**: Muertes totales por región (2024)
- **Utilidad**: Mostrar peso relativo de cada región en conflictividad global
- **Insights**: África y Oriente Medio concentran ~70% de muertes

#### 5️⃣ Composición de Tipos de Conflicto
- **Tipo**: Stacked Bar o Área apilada
- **Variable**: Desglose por región (Intraestatal, Interstate, Unilateral, No-estatal)
- **Utilidad**: Identificar patrones de conflictividad por región
- **Insights**:
  - Europa: Guerra convencional (65% Interstate)
  - Oriente Medio: Conflictos internos (81% Intraestatal)
  - Américas: Conflictos no estatales (71%)

#### 6️⃣ Evolución Temporal de Conflictos
- **Tipo**: Línea temporal múltiple
- **Variable**: Muertes por tipo de conflicto (si hay datos históricos)
- **Utilidad**: Tendencias a largo plazo

---

### **Categoría 3: Terrorismo**

#### 7️⃣ Muertes por Terrorismo - Mapa de Calor
- **Tipo**: Mapa coroplético
- **Variable**: Número de muertes por terrorismo (2021)
- **Utilidad**: Visualizar concentración geográfica (Afganistán, Nigeria destacan)

#### 8️⃣ Top 15 Países Afectados por Terrorismo
- **Tipo**: Gráfico de barras horizontal
- **Variable**: Fatalities (2021)
- **Utilidad**: Identificar hotspots de terrorismo
- **Destacado**: 37.6% de muertes en Afganistán

#### 9️⃣ Distribución Terrorismo por Región - Donut
- **Tipo**: Gráfico de pastel o donut
- **Variable**: Muertes por región
- **Utilidad**: Mostrar que Asia domina (56%) el terrorismo global

---

### **Categoría 4: Comparativas Integradas**

#### 🔟 Dashboard Multidimensional
Combinar en un dashboard:
- **Arriba izq**: Muertes totales por causa (Conflictos, Terrorismo, Cardiovascular)
- **Arriba der**: Mapa regional de conflictividad
- **Abajo izq**: Top 10 países (combinando múltiples causas)
- **Abajo der**: Timeline de tendencias

#### 🔞 Escatter Plot: Desarrollo vs Mortalidad Cardiovascular
- **Eje X**: PIB per cápita o IDH (necesitarías Dataset adicional)
- **Eje Y**: Tasa cardiovascular
- **Tamaño burbuja**: Población
- **Color**: Región
- **Utilidad**: Correlación entre desarrollo y mortalidad

#### 🔢 Comparativa Regional - Heatmap
- **Eje X**: Tipo de causa (Cardiovascular, Conflictos, Terrorismo)
- **Eje Y**: Región
- **Color**: Intensidad/Tasa de mortalidad
- **Utilidad**: Identificar qué tipo de mortalidad predomina por región

---

## 🛠️ HERRAMIENTAS RECOMENDADAS

**Para gráficos estáticos/web:**
- Plotly (interactivo, fácil de usar)
- Matplotlib + Seaborn (flexible)
- D3.js (mapas interactivos avanzados)

**Para dashboards:**
- Tableau
- Power BI
- Streamlit (Python)
- Grafana

**Para mapas:**
- Leaflet + Folium (Python)
- Mapbox

---

## 💡 ANÁLISIS POSIBLES

1. **Correlación**: ¿Relacionan conflictos armados con mortalidad cardiovascular?
2. **Comparativa**: Violencia directa (conflictos + terrorismo) vs violencia indirecta (enfermedad)
3. **Clustering**: Agrupar países por patrón de mortalidad
4. **Tendencias**: Si obtienes datos históricos de conflictos
5. **Burden of Disease**: Comparar peso relativo de causas de muerte

---

## 📌 LIMITACIONES ACTUALES

- ⚠️ Datos cardiovasculares solo para 2021
- ⚠️ Datos de terrorismo solo para 2021
- ⚠️ Conflictos: datos acumulados históricos (difícil ver tendencias recientes)
- ⚠️ Falta correlación con variables económicas/sociales
- 💡 **Solución**: Buscar datasets temporales más granulares en OWID

