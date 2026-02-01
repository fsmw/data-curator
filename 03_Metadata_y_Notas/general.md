# Documentación Metodológica del Dataset  
**Tema:** General – Inflación de precios al consumidor (annual %)  
**Fuente:** Our World in Data (OWID) – “Inflation of consumer prices”  
**URL original:** <https://ourworldindata.org/grapher/inflation-of-consumer-prices>  

---  

## 1. Fuente Original  

**Our World in Data (OWID)** es una plataforma de investigación sin fines de lucro que compila y visualiza datos de desarrollo y macro‑económicos a nivel global. Los indicadores que publica provienen de organismos internacionales reconocidos (p. ej., el Fondo Monetario Internacional, el Banco Mundial, la OCDE) y están sujetos a procesos de verificación y documentación pública.  

- **Reputación:** OWID es ampliamente citada en la literatura académica y en organismos de política pública por su rigor en la recopilación, estandarización y publicación de datos abiertos bajo licencia Creative Commons BY 4.0.  
- **Licencia:** Los datos están disponibles bajo la licencia CC‑BY, lo que permite su uso, distribución y adaptación siempre que se cite la fuente original.  

> Fuente: *International Monetary Fund (via World Bank) (2025) – processed by Our World in Data* – “Inflation of consumer prices” [ourworldindata.org](https://ourworldindata.org/grapher/inflation-of-consumer-prices)  

---

## 2. Variables Utilizadas  

| Variable | Tipo | Descripción |
|----------|------|-------------|
| **country** | Texto | Nombre del país (ej. “Argentina”). |
| **country_code** | Texto | Código ISO‑3 del país (ej. “ARG”). |
| **year** | Numérico (entero) | Año calendario al que corresponde la observación (2024). |
| **Inflation** | Numérico (decimal) | Tasa de inflación anual medida como variación porcentual del Índice de Precios al Consumidor (IPC) respecto al año anterior. |
| **consumer prices (annual %)** | Numérico (decimal) | Sinónimo de *Inflation*; la columna se incluye en la exportación original de OWID para mantener compatibilidad con otras series. |
| **time** | Texto / Fecha | Representación del año en formato “YYYY” (p. ej., “2024”). En la práctica es redundante con *year*. |

> La descripción oficial del indicador indica que la inflación se calcula a partir del **IPC** usando la **fórmula de Laspeyres** y refleja el cambio porcentual anual del costo de una canasta de bienes y servicios representativa del consumo de los hogares [ourworldindata.org](https://ourworldindata.org/grapher/inflation-of-consumer-prices).  

---

## 3. Cobertura Temporal y Geográfica  

| Dimensión | Detalle |
|-----------|---------|
| **Periodo** | Únicamente el año **2024** (rango temporal 2024 – 2024). |
| **Frecuencia** | Anual (una observación por país). |
| **Cobertura geográfica** | 186 filas corresponden a 186 países/territorios con datos disponibles en la base original de OWID. La cobertura incluye la mayoría de los países reconocidos por la ONU y algunos territorios con datos de inflación publicados por el FMI/World Bank. |
| **Unidad de medida** | Porcentaje anual (%). |

---

## 4. Metodología y Transformaciones  

### 4.1 Metodología de cálculo (según la fuente)  

1. **Índice de precios al consumidor (IPC)** – elaborado por la autoridad estadística nacional de cada país (p. ej., DANE en Colombia, INEGI en México).  
2. **Fórmula de Laspeyres** – el IPC se construye como un índice de ponderaciones fijas que compara los precios actuales con los precios de una canasta base.  
3. **Cálculo de la inflación** – la tasa anual se obtiene como:  

\[
\text{Inflación}_{t} = \frac{\text{IPC}_{t} - \text{IPC}_{t-1}}{\text{IPC}_{t-1}} \times 100
\]

4. **Fuente de datos primarios** – *World Development Indicators* del Banco Mundial, que a su vez recopila los datos publicados por el **International Monetary Fund (IMF)**.  

> Detalle de la metodología y procesamiento de OWID se encuentra en su página de “Sources and processing” [ourworldindata.org](https://ourworldindata.org/grapher/inflation-of-consumer-prices#sources-and-processing).  

### 4.2 Transformaciones aplicadas en este dataset  

| Transformación | Descripción | Comentario |
|----------------|-------------|------------|
| **Ninguna** | Los datos se descargaron tal cual aparecen en la tabla de OWID, sin aplicar filtros, agregaciones, ni conversiones de unidades. | La tabla conserva todas las columnas originales y la codificación de países. |

---

## 5. Advertencias y Limitaciones  

1. **Variabilidad de la canasta y ponderaciones**  
   - Cada país define su propia canasta de bienes y servicios y actualiza sus ponderaciones con distinta periodicidad (a veces cada 5‑10 años). Por ello, la comparabilidad inter‑anual dentro de un mismo país es alta, pero la comparabilidad **entre países** puede verse afectada por diferencias metodológicas.  

2. **Cobertura incompleta**  
   - Algunos países de bajo ingreso o con sistemas estadísticos débiles pueden no reportar datos o reportarlos con retraso. La ausencia de observaciones para ciertos años no implica ausencia de inflación, sino falta de información.  

3. **Uso de la fórmula de Laspeyres**  
   - La fórmula asume que las cantidades de la canasta base permanecen fijas, lo que puede sobre‑ o subestimar la inflación real cuando hay cambios estructurales en los patrones de consumo (p. ej., sustitución de productos).  

4. **Actualizaciones futuras**  
   - OWID actualiza la serie anualmente (próxima actualización prevista para enero 2026). Los usuarios deben verificar si existen revisiones posteriores a la versión descargada.  

5. **Interpretación de “consumer prices (annual %)”**  
   - Esta columna es una réplica de *Inflation* y no aporta información adicional; se recomienda usar una única variable para evitar redundancia.  

6. **Limitaciones de la fuente primaria (IMF/WDI)**  
   - Los datos del FMI provienen de reportes oficiales de los gobiernos; cualquier error de reporte o revisión posterior de los institutos nacionales se reflejará en la serie con un desfase temporal.  

### Recomendaciones para investigadores  

- **Citar siempre la fuente** con la referencia completa (OWID + IMF/World Bank).  
- **Verificar la consistencia** de la canasta y la metodología nacional cuando se realicen comparaciones entre países.  
- **Mantener la versión** del dataset (fecha de descarga) en los metadatos de cualquier análisis para reproducibilidad.  
- **Consultar la documentación original** del IPC de cada país (p. ej., DANE para Colombia, INEGI para México) si se requiere un análisis más profundo de la composición de la canasta.  

---  

*Este documento está pensado para servir como guía metodológica a economistas, analistas de datos y demás investigadores que utilicen la serie “Inflation of consumer prices” de Our World in Data.*