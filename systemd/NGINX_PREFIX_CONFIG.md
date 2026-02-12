# Configuración Nginx con Prefijo /misesdata

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
