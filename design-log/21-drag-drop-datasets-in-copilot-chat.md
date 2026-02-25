# Design Log #21: Drag & Drop Datasets in Copilot Chat

## Background

Los usuarios necesitan una forma intuitiva de indicar al copilot con qué datos quieren trabajar. Actualmente deben describir los datasets por nombre o ID, lo cual es propenso a errores y poco descubrible.

## Problem

- Los usuarios no pueden fácilmente referenciar datasets específicos en el chat
- No hay forma visual de ver qué datasets están disponibles mientras se escribe el prompt
- El contexto del dataset no se envía automáticamente al copilot

## Questions and Answers

**Q: ¿Dónde debe mostrarse la lista de datasets?**
A: En la sidebar izquierda, debajo de los threads. Debe ser colapsable para no ocupar espacio innecesario.

**Q: ¿Qué información del dataset se debe incluir en el contexto?**
A: ID, nombre, descripción, columnas principales, y fecha de actualización. Esto permite al copilot entender qué datos están disponibles.

**Q: ¿Cómo se inserta la referencia en el mensaje?**
A: Al soltar el dataset en el input, se inserta un marcador especial `[DATASET:id:nombre]` que el backend puede interpretar.

## Design

### User Interface

```
┌─────────────────┬──────────────────────────────────────┐
│   Threads       │     Chat Messages                    │
│   ─────────     │     ─────────────────                │
│   Thread 1      │                                      │
│   Thread 2      │   User: Analiza [DATASET:123:GDP]    │
│                 │                                      │
│   Datasets 📊   │   Copilot: Entiendo que quieres      │
│   ─────────     │   analizar el dataset GDP...         │
│   📁 GDP        │                                      │
│   📁 Health  ←──┼── Arrastra hasta el input            │
│   📁 Trade      │                                      │
│                 │   [Input con highlight al arrastrar] │
└─────────────────┴──────────────────────────────────────┘
```

### Interactions

1. **Drag Start**: Dataset card muestra efecto visual, cursor cambia
2. **Drag Over Input**: Input se resalta con borde primario
3. **Drop**: Se inserta marcador `[DATASET:id:nombre]` en cursor position
4. **Context Send**: Al enviar mensaje, el backend recibe lista de datasets referenciados

### Implementation Details

**Frontend Changes:**
- Sección "Available Datasets" en sidebar (debajo de threads)
- Dataset cards con `draggable="true"` y `@dragstart`
- Input modificada para aceptar datasets (tipo 'dataset')
- Funciones `startDraggingDataset()`, `handleInputDrop()` extendida
- Variable `droppedDatasets` para trackear datasets en el mensaje

**Data Format:**
```javascript
// Dataset drop data
event.dataTransfer.setData('application/json', JSON.stringify({
  type: 'dataset',
  id: dataset.id,
  name: dataset.name,
  description: dataset.description,
  fields: dataset.fields,
  row_count: dataset.row_count
}));

// Inserted into message
"Por favor analiza [DATASET:123:PBI Argentina] y dime tendencias"
```

**Backend Integration:**
El backend ya soporta tool calling. El mensaje con marcadores `[DATASET:...]` se envía tal cual, y el LLM puede interpretar los IDs para llamar a tools como `preview_data` o `analyze_data`.

## Implementation Plan

### Phase 1: UI Components (30 min)
1. Add "Available Datasets" section in sidebar
2. Style dataset cards with drag handles
3. Add expand/collapse toggle

### Phase 2: Drag & Drop Logic (30 min)
1. Add dragstart handler to dataset cards
2. Extend handleInputDrop to handle type='dataset'
3. Insert dataset marker at cursor position

### Phase 3: Visual Feedback (15 min)
1. Highlight input on dataset dragover
2. Show tooltip/info on dataset hover
3. Animate card on drag

## Examples

### User Flow
```
1. User sees "Available Datasets" in sidebar
2. User drags "GDP Argentina (2020-2024)" to input
3. Input shows: "Analiza [DATASET:45:GDP Argentina]"
4. User completes: "...y compara con inflación"
5. Copilot recibe contexto del dataset 45 automáticamente
```

### Code Example
```html
<!-- Dataset Card -->
<div class="dataset-card" 
     draggable="true"
     @dragstart="startDraggingDataset($event, dataset)"
     :class="{'dragging': draggingDataset === dataset.id}">
  <i class="bi bi-folder"></i>
  <span x-text="dataset.name"></span>
  <small x-text="dataset.row_count + ' rows'"></small>
</div>

<!-- Enhanced Drop Handler -->
handleInputDrop(event) {
  event.preventDefault();
  this.draggingOver = false;
  
  const data = event.dataTransfer.getData('application/json');
  if (!data) return;
  
  const dropData = JSON.parse(data);
  
  if (dropData.type === 'dataset') {
    this.insertDatasetReference(dropData, event);
  } else if (dropData.type === 'field') {
    this.insertFieldReference(dropData);
  }
}
```

## Trade-offs

**Alternative: Dropdown selector**
- ✅ Más familiar para usuarios
- ❌ Requiere clicks múltiples
- ❌ No tan fluido como drag & drop

**Alternative: @mentions (como Slack)**
- ✅ Familiar para usuarios de chat
- ❌ Requiere implementar autocomplete
- ❌ Menos visual que ver la lista

**Chosen: Drag & Drop from sidebar**
- Balance entre descubribilidad y facilidad de uso
- Aprovecha el espacio existente en la sidebar
- Consistente con el drag & drop de fields existente

## Implementation Results

### Completed (2025-02-16)

**Files Modified:**
- `src/web/templates/copilot_chat.html`

**State Variables Added:**
```javascript
showDatasets: true,           // Toggle sidebar visibility
draggingDatasetId: null,      // Tracks which dataset is being dragged
contextDatasets: [],          // Datasets dropped into prompt context
```

**Functions Implemented:**
```javascript
startDraggingDataset(event, dataset)  // Init drag with dataset data
stopDraggingDataset()                  // Clear drag state
removeContextDataset(datasetId)        // Remove dataset from context
clearContextDatasets()                 // Clear all context datasets
handleInputDrop(event)                 // Extended to handle 'dataset' type
```

**UI Changes:**
1. Dataset cards in sidebar now draggable with visual feedback
2. Input area shows "context badges" when datasets are dropped
3. Placeholder updates dynamically: "Analizar [dataset names]..."
4. Datasets injected into message as `[Context Datasets]` block

**CSS Added:**
- `.dataset-card` with hover/active effects
- `.cursor-grab` for grab cursor
- Dragging state with opacity

**User Flow:**
1. User drags dataset from sidebar → cursor shows grab
2. Drop on input → badge appears in context bar
3. Multiple datasets can be added
4. Send message → datasets included in context
5. Copilot receives dataset IDs and metadata

**Deviations from Design:**
- Instead of `[DATASET:id:nombre]` markers, datasets are sent as a `[Context Datasets]` block with full metadata
- Context datasets shown as badges above input, not inline text
- Badges can be individually removed or cleared all at once
