# Configuración Nginx con Prefijo /misesdata

## ✅ Implementación Completada

La aplicación ahora soporta completamente el prefijo `/misesdata/` tanto en desarrollo local como detrás de nginx.

### Cambios Implementados

1. **Helper JavaScript Global** (`src/web/templates/base.html`):
   - Variable global `window.APP_PREFIX` que lee el prefijo del servidor
   - Función `apiUrl(path)` que concatena automáticamente el prefijo
   - Todas las llamadas `fetch()` ahora usan `apiUrl('/api/...')`

2. **Templates Actualizados** (47 URLs corregidas):
   - `search.html` - 4 URLs
   - `browse_local.html` - 10 URLs
   - `copilot_chat.html` - 25 URLs
   - `visualization_canvas.html` - 4 URLs
   - `visualization_pygwalker.html` - 2 URLs
   - `base.html` - 1 URL (`/auth/set-language`)

3. **Backend Flask** (ya estaba configurado):
   - `ProxyFix` middleware con `x_prefix=1`
   - Lee `SCRIPT_NAME` del entorno
   - Configura `APPLICATION_ROOT` automáticamente

## Configuración de Nginx

Edita tu archivo de configuración de nginx:

```bash
sudo nano /etc/nginx/sites-available/tu-sitio
```

Añade la siguiente configuración dentro del bloque `server`:

```nginx
# Redirigir /misesdata (sin slash final) a /misesdata/
location = /misesdata {
    return 301 /misesdata/;
}

# Proxy inverso para la aplicación
location /misesdata/ {
    # Remover el prefijo /misesdata antes de enviar a Flask
    rewrite ^/misesdata/(.*) /$1 break;
    
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    
    # Headers esenciales para Flask
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /misesdata;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

# Archivos estáticos (mejora rendimiento)
location /misesdata/static/ {
    alias /opt/data-curator/src/web/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

## Configuración del Servicio Systemd

Edita el archivo de servicio:

```bash
sudo nano /etc/systemd/system/mises-data.service
```

Añade la variable de entorno `SCRIPT_NAME`:

```ini
[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/data-curator
Environment="PATH=/opt/data-curator/.venv/bin"
Environment="FLASK_APP=src.web"
Environment="FLASK_ENV=production"
Environment="FLASK_SECRET_KEY=tu-clave-secreta-aqui"
Environment="FLASK_RUN_PORT=5000"
# IMPORTANTE: Configurar el prefijo para la aplicación
Environment="SCRIPT_NAME=/misesdata"
ExecStart=/opt/data-curator/.venv/bin/python -m src.web
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Aplicar Cambios

```bash
# 1. Recargar systemd
sudo systemctl daemon-reload

# 2. Reiniciar el servicio
sudo systemctl restart mises-data

# 3. Verificar configuración de nginx
sudo nginx -t

# 4. Recargar nginx
sudo systemctl reload nginx

# 5. Verificar estado
sudo systemctl status mises-data
sudo journalctl -u mises-data -f
```

## Verificar Funcionamiento

### Acceso Directo (localhost:5000)
```bash
# En el servidor
python -m src.web
# Acceder a: http://localhost:5000/
```

### Acceso con Nginx (/misesdata/)
```bash
# Acceder a: http://tu-dominio.com/misesdata/
```

## Solución de Problemas

### Si las URLs no funcionan:

1. Verifica que `SCRIPT_NAME` esté configurado:
   ```bash
   sudo systemctl show mises-data --property=Environment
   ```

2. Verifica los headers de nginx:
   ```bash
   sudo tail -f /var/log/nginx/access.log
   ```

3. Verifica que Flask reciba el prefijo:
   ```bash
   sudo journalctl -u mises-data -f | grep SCRIPT
   ```

### Si los archivos estáticos no cargan:

Verifica los permisos:
```bash
ls -la /opt/data-curator/src/web/static/
sudo chown -R www-data:www-data /opt/data-curator/src/web/static/
```

## Configuración Alternativa: Subdominio (Más Simple)

Si prefieres evitar el prefijo /misesdata/, usa un subdominio:

```nginx
# /etc/nginx/sites-available/misesdata.tu-dominio.com
server {
    listen 80;
    server_name misesdata.tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Con esta configuración no necesitas `SCRIPT_NAME` ni prefijos. Funciona tanto local como con nginx sin cambios adicionales.

---

## Cómo Funciona la Solución

### Flujo de Datos

1. **Usuario accede**: `https://dominio.com/misesdata/`
2. **Nginx recibe**: Añade header `X-Forwarded-Prefix: /misesdata`
3. **Flask ProxyFix**: Lee el header y establece `SCRIPT_NAME=/misesdata`
4. **Flask render**: `request.script_root` retorna `/misesdata`
5. **Template base.html**: `window.APP_PREFIX = "/misesdata"`
6. **JavaScript**: `apiUrl('/api/search')` → `/misesdata/api/search`
7. **Navegador fetch**: `GET https://dominio.com/misesdata/api/search`

### Código Clave

**backend (src/web/__init__.py)**:
```python
script_name = os.getenv('SCRIPT_NAME', '')
if script_name:
    app.config['APPLICATION_ROOT'] = script_name

app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)
```

**frontend (base.html)**:
```html
<script>
  window.APP_PREFIX = "{{ request.script_root | safe }}";
  
  function apiUrl(path) {
    return window.APP_PREFIX + path;
  }
</script>
```

**uso en templates**:
```javascript
// ❌ Antes (hardcoded):
fetch('/api/search?q=gdp')

// ✅ Ahora (con helper):
fetch(apiUrl('/api/search?q=gdp'))
```

### Escenarios Soportados

| Escenario | SCRIPT_NAME | APP_PREFIX | URL Final |
|-----------|-------------|------------|-----------|
| Local dev | (vacío) | "" | `/api/search` |
| Con env var | `/misesdata` | "/misesdata" | `/misesdata/api/search` |
| Detrás nginx | `/misesdata` | "/misesdata" | `/misesdata/api/search` |

## Testing

Ver `test_url_prefix.sh` en la raíz del proyecto para pruebas automatizadas.

```bash
# Test local
python -m src.web
# Acceder: http://localhost:5000/

# Test con prefijo
SCRIPT_NAME=/misesdata python -m src.web
# Acceder: http://localhost:5000/misesdata/

# Verificar en consola del navegador
console.log(window.APP_PREFIX)  // debe mostrar "" o "/misesdata"
```
