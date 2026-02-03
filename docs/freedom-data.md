# Freedom Data

## 1. Resumen
Se propone el desarrollo de una plataforma web interna de inteligencia de datos para el **Instituto Mises Cono Sur**, destinada a automatizar y profesionalizar el flujo completo de trabajo analítico del equipo. 

Actualmente, el proceso de producción de gráficos y análisis se basa en una secuencia manual: descarga de bases de datos desde fuentes externas, limpieza en hojas de cálculo, migración a software estadístico y posterior generación de visualizaciones. Este modelo es intensivo en tiempo, difícil de reproducir y vulnerable a errores operativos.

La iniciativa busca reemplazar este esquema manual por un sistema integrado que permita, desde un único entorno:
- Conectarse directamente a fuentes oficiales mediante APIs.
- Limpiar y validar datos de forma sistemática.
- Ejecutar análisis estadísticos y económicos.
- Generar visualizaciones narrativas reutilizables.
- Producir de manera continua contenidos tipo *Dato de la Semana*.

El objetivo estratégico es transformar a **Freedom Data** desde un equipo que produce gráficos puntuales hacia una **unidad institucional de inteligencia empírica**, con procesos estandarizados, trazabilidad metodológica y capacidad de escalar su producción sin aumentar proporcionalmente los costos humanos. La plataforma está orientada a maximizar la productividad del equipo técnico y consolidar una base empírica permanente al servicio del ecosistema **Hegemonik**.

---

## 2. Mandato Institucional
Freedom Data es el módulo de datos y visualización del ecosistema Hegemonik del Instituto Mises Cono Sur, cuyo propósito no es únicamente informar, sino **formar criterio económico, político e institucional** a partir de evidencia empírica clara, defendible y pedagógicamente trabajada.

Este mandato implica que el trabajo del equipo no se limita a producir gráficos, sino a construir un sistema permanente de generación de evidencia. Desde esta perspectiva, la unidad es analítica y transversal, articulada con los equipos de educación, guiones y producción.

El desarrollo de esta plataforma interna responde directamente a este mandato: permite pasar de una producción fragmentada y artesanal a una infraestructura metodológica estable, alineada con la misión de transformar datos oficiales en insumos pedagógicos y narrativos al servicio de la batalla cultural por la libertad.

---

## 3. Diagnóstico Operativo Actual

### 3.1 Flujo de trabajo vigente
En su estado actual, la producción se apoya en un proceso mayormente manual:
1. Identificación de fuentes externas confiables.
2. Descarga individual de bases de datos.
3. Corrección de estructuras y formatos.
4. Limpieza preliminar en hojas de cálculo.
5. Migración a software estadístico.
6. Generación de gráficos e integración en materiales.

### 3.2 Principales fricciones
El modelo actual presenta cuatro limitaciones estructurales:
- **a) Alto consumo de tiempo técnico:** Gran parte del esfuerzo se destina a tareas mecánicas en detrimento del análisis sustantivo.
- **b) Riesgo elevado de errores operativos:** La manipulación manual aumenta la probabilidad de inconsistencias y transformaciones no documentadas.
- **c) Baja reproducibilidad metodológica:** Los pasos intermedios no quedan sistematizados, dificultando auditar o replicar análisis.
- **d) Escalabilidad limitada:** El volumen de producción depende directamente de la capacidad humana disponible.

---

## 4. Objetivo de la Plataforma
Desarrollar una plataforma web interna de alto rendimiento que concentre, automatice y estandarice el flujo completo de trabajo analítico. El sistema ejecutará de forma continua:
- Conexión directa con fuentes oficiales y académicas.
- Ingestión y estandarización automática de datasets.
- Limpieza y validación metodológica sistemática.
- Análisis estadístico y económico reproducible.
- Generación de visualizaciones narrativas reutilizables.
- Soporte estructurado a la producción editorial (*Dato de la Semana*).

### Transformaciones clave:
- **De operación manual a proceso industrializado:** Uso de pipelines estables y documentados.
- **De producción puntual a capacidad institucional:** Los análisis se convierten en parte de una infraestructura permanente.
- **De dependencia individual a conocimiento colectivo:** Procedimientos formalizados y reutilizables por todo el equipo.

---

## 5. Soporte Tecnológico

### 5.1 Conexión a Fuentes mediante APIs (Enfoque API-first)
- Extracción automatizada de datasets (CSV, JSON, Parquet).
- Programación de actualizaciones periódicas.
- Registro de metadatos (fuente, fecha, versión).
- **Rol técnico (Python):** Uso de clientes HTTP y normalización de respuestas.

### 5.2 Librerías Analíticas: Base del Procesamiento
- **Limpieza y transformación:** `pandas`, `polars` y formato `Parquet` para almacenamiento eficiente.
- **Validación y control de calidad:** `pandera` o `Great Expectations` para definir reglas de consistencia.
- **Análisis estadístico y econométrico:** `statsmodels` y `linearmodels` para regresiones y modelos de panel.
- **Visualización:** `plotly` (interactivos) y `altair` (declarativa) para gráficos narrativos.

### 5.3 Arquitectura Modular
1. **Módulo de Ingesta:** Conectores a APIs externas.
2. **Módulo de Curación:** Limpieza, validación y versionado.
3. **Módulo de Análisis:** Modelos estadísticos y comparativos.
4. **Módulo de Visualización:** Plantillas gráficas institucionales.
5. **Módulo Editorial:** Selección temática y empaquetado.

---

## 6. Equipo
Responsables del proyecto:
- **Francisco San Martín**
- **Lucas González**

## Conclusión
Esta plataforma transforma a **Freedom Data** en una unidad de inteligencia empírica capaz de convertir datos en impacto institucional siguiendo el flujo: 
**Datos → Evidencia → Microlearning → Impacto Institucional.**