# Design Log 22 — Preconfigured Dataset Filters

## Background
El proyecto ya tiene un sistema de filtros geográficos e idiomas definidos en `src/utils/regions.py` con presets como 'latam', 'spanish', 'americas', 'europe', etc. El `DataCleaner` ya implementa métodos como `filter_by_preset()`, `filter_by_countries()`, y `apply_filters()`.

Sin embargo, estos filtros solo están disponibles vía CLI y no están integrados en la UI web. Los usuarios no pueden:
1. Ver qué filtros preconfigurados están disponibles
2. Aplicar filtros a datasets existentes desde la interfaz web
3. Ver qué filtros se han aplicado a un dataset

## Problem
Los usuarios necesitan poder filtrar datasets por regiones/idiomas predefinidos desde la UI web en `/browse`, y tener visibilidad de los filtros aplicados en los datasets resultantes.

## Questions and Answers
- Q: ¿Qué filtros preconfigurados deben estar disponibles?
  - A: Los definidos en `src/utils/regions.py`: regiones geográficas (latam, americas, europe, etc.) e idiomas (spanish, english, etc.)
- Q: ¿Cómo se almacena la información de filtros aplicados?
  - A: En el nombre del archivo siguiendo la convención existente: `{topic}_{source}_{filter_preset}_{start}_{end}_{timestamp}.csv`
- Q: ¿Puede un usuario aplicar múltiples filtres?
  - A: Sí, se pueden aplicar filtros secuenciales (preset + year range)
- Q: ¿Dónde se debe mostrar la información de filtros aplicados?
  - A: En el modal de detalle del dataset y en la lista de datasets (como badges)
- Q: ¿Los filtros crean nuevos datasets o modifican los existentes?
  - A: Crean nuevos datasets (fork) para preservar el original

## Design

### 1. API Endpoints

**GET /api/filters/presets**
- Retorna lista de filtros preconfigurados organizados por categoría
- Estructura: `{ categories: [{ name, filters: [{key, label, description, country_count}] }] }`

**POST /api/datasets/{id}/filter**
- Aplica filtros a un dataset existente y crea uno nuevo
- Body: `{ preset?: string, start_year?: number, end_year?: number, name?: string }`
- Retorna: `{ status, dataset_id, file_path, transformations }`

### 2. UI Changes (browse_local.html)

**Filtros en la vista de datasets:**
- Agregar columna "Filter" en la tabla que muestre el preset aplicado (si existe)
- Mostrar badge con el nombre del preset (ej: "Hispanohablante", "Latinoamérica")

**Modal de detalle del dataset:**
- Agregar sección "Apply Filters" con:
  - Dropdown para seleccionar preset (regiones/idiomas)
  - Inputs opcionales para year range
  - Botón "Apply Filter" que crea dataset filtrado
- Mostrar historial de filtros aplicados

**Toolbar de acciones:**
- Botón "Filter" en cada dataset para abrir modal de filtros

### 3. Backend Logic

**Filter Application Flow:**
1. Leer dataset original
2. Aplicar filtros usando `DataCleaner.apply_filters()`
3. Generar nombre: `{topic}_{source}_{preset}_{start}_{end}_{timestamp}.csv`
4. Guardar con `DataCleaner.save_clean_dataset()`
5. Indexar en catalog con `DatasetCatalog.index_dataset()`
6. Retornar nuevo dataset_id

### 4. Data Storage

**Convención de nombres:**
- Dataset original: `salarios_owid_global_2000_2023_20240101120000.csv`
- Dataset filtrado: `salarios_owid_spanish_2000_2023_20240101130000.csv`

**Metadatos:**
- El `indicator_id` del dataset filtrado contendrá el preset aplicado
- Se agregará campo `parent_dataset_id` para trazabilidad (future enhancement)

## Implementation Plan

### Phase 1: API Endpoints
- [ ] Crear `GET /api/filters/presets` en nuevo archivo `src/web/api/filters.py`
- [ ] Crear `POST /api/datasets/{id}/filter` en `src/web/api/datasets.py`
- [ ] Registrar rutas en `src/web/api/__init__.py`

### Phase 2: UI Components
- [ ] Agregar columna "Filter" en la tabla de datasets
- [ ] Agregar modal "Apply Filters" en browse_local.html
- [ ] Integrar dropdown de presets desde API
- [ ] Agregar botón "Filter" en toolbar de cada dataset

### Phase 3: Backend Integration
- [ ] Implementar `DatasetFilterService` clase para orquestar filtrado
- [ ] Integrar con `DataCleaner` existente
- [ ] Asegurar naming correcto con preset incluido

### Phase 4: Testing & Polish
- [ ] Tests de integración para API endpoints
- [ ] Verificar UI en diferentes datasets
- [ ] Documentar en AGENTS.md

## Examples

### ✅ Uso correcto
```javascript
// Aplicar filtro hispanohablante
POST /api/datasets/42/filter
{
  "preset": "spanish",
  "name": "Salarios - Países Hispanohablantes"
}

// Respuesta exitosa
{
  "status": "success",
  "dataset_id": 43,
  "file_path": "/data/clean/user/salarios/salarios_owid_spanish_2000_2023_20240101120000.csv",
  "transformations": [
    "Filtered to Países de habla hispana: kept 18/195 rows (177 removed)"
  ]
}
```

### ❌ Uso incorrecto
```javascript
// No especificar preset ni filtros
POST /api/datasets/42/filter
{}

// Respuesta de error
{
  "status": "error",
  "message": "No filters specified. Provide preset, countries, or year_range."
}
```

## Trade-offs

**Pros:**
- Reutiliza código existente en `DataCleaner` y `regions.py`
- No requiere cambios en el schema de la base de datos
- Flujo intuitivo: seleccionar dataset → aplicar filtro → nuevo dataset

**Cons:**
- Los datasets filtrados ocupan espacio adicional en disco
- No hay tracking automático de relación padre-hijo entre datasets
- Los filtros son predefinidos (no personalizables por el usuario)

## Implementation Results

### Files Created/Modified

**Created:**
1. `src/web/api/filters.py` - Nuevo módulo con endpoints para filtros preconfigurados
2. `src/web/api/__init__.py` - Actualizado para registrar el blueprint de filtros
3. Esta design log documenta el diseño completo

**Modified:**
4. `src/web/templates/browse_local.html` - Agregado UI para filtros en vista tabla y cards

### Cambios Implementados

#### 1. API Endpoints (`src/web/api/filters.py`)

**GET /api/filters/presets**
- Retorna lista de filtros preconfigurados disponibles
- 4 filtros incluidos: `spanish`, `america`, `europe`, `oecd`
- Cada preset incluye metadata descriptiva

**POST /api/datasets/<id>/filter**
- Aplica filtro preconfigurado o personalizado a un dataset
- Soporta filtros: `preset`, `countries` (lista), `year_range`
- Crea nuevo dataset en `data/user/<topic>/`
- Genera nombre de archivo siguiendo convención: `{original_name}_{filter_id}_{timestamp}.csv`
- Guarda metadatos con información del filtro aplicado

#### 2. UI en Browse Local (`src/web/templates/browse_local.html`)

**Vista de Tabla:**
- Nueva columna "Filter" con botón 🔽 que abre modal
- Modal muestra presets disponibles y permite aplicar filtro
- Input para nombre opcional del dataset filtrado
- Preview de países incluidos en cada preset

**Vista de Cards:**
- Agregado botón "Filter Dataset" junto a "Edit dataset"
- Mismo modal que en vista tabla para consistencia

**Modal de Filtro:**
- Carga presets dinámicamente desde API
- Muestra descripción y preview de países
- Input para nombre personalizado del nuevo dataset
- Estados de loading y error manejados

#### 3. Integración con Sistema Existente

**Reutilización de código:**
- Usa `DataCleaner` existente para filtrar por países
- Usa funciones de `regions.py` para obtener listas de países
- Respeta convenciones de nomenclatura de archivos
- Guarda datasets en estructura de directorios existente

**UX Mejorada:**
- Después de aplicar filtro exitosamente, automáticamente abre el preview del nuevo dataset
- Usuario ve inmediatamente los resultados del filtro aplicado
- Transición suave con delay de 300ms para permitir que el modal se cierre

**Extensibilidad:**
- Fácil agregar nuevos presets en `filters.py`
- API permite filtros personalizados (lista de países arbitraria)
- Estructura preparada para filtros avanzados (años, columnas)

### API Endpoints Summary

```
GET  /api/filters/presets          → Lista filtros disponibles
POST /api/datasets/<id>/filter     → Aplicar filtro a dataset
```

### Testing

- ✅ Sintaxis Python validada sin errores
- ⚠️ Prueba end-to-end pendiente (servidor 502 en producción)

### Next Steps

1. Desplegar cambios al servidor
2. Verificar integración con base de datos real
3. Test de usabilidad con usuarios
4. Considerar agregar filtros adicionales según feedback

## Future Enhancements
- [ ] Filtros personalizados (usuario define lista de países)
- [ ] Pipeline de filtros (aplicar múltiples filtres en secuencia)
- [ ] Visualización de datasets filtrados como "vistas" del original
- [ ] Tracking de lineage (árbol de datasets derivados)
