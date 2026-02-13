# Configuración de Servicio Systemd para Mises Data Curator

## Instalación del Servicio

### 1. Copiar el archivo de servicio

```bash
sudo cp systemd/mises-data.service /etc/systemd/system/
```

### 2. Editar configuración

Abre el archivo y modifica los valores según tu entorno:

```bash
sudo nano /etc/systemd/system/mises-data.service
```

Variables importantes a configurar:

- **`WorkingDirectory`**: Ruta absoluta donde está instalada la aplicación (`/opt/data-curator`)
- **`Environment="FLASK_SECRET_KEY`**: Genera una clave secreta segura
- **`Environment="FLASK_RUN_PORT`**: Puerto donde correrá el servidor (default: 5000)
- **`User`** y **`Group`**: Usuario que ejecutará el servicio

### 3. Configurar permisos

Si usas un usuario diferente a `www-data`:

```bash
# Crear usuario dedicado (opcional)
sudo useradd -r -s /bin/false mises-data

# Cambiar propietario del directorio
sudo chown -R mises-data:mises-data /opt/data-curator
```

### 4. Recargar systemd e iniciar servicio

```bash
# Recargar configuración de systemd
sudo systemctl daemon-reload

# Iniciar el servicio
sudo systemctl start mises-data

# Verificar estado
sudo systemctl status mises-data

# Habilitar inicio automático
sudo systemctl enable mises-data
```

## Cambiar el Puerto

Edita el archivo de servicio:

```bash
sudo nano /etc/systemd/system/mises-data.service
```

Modifica la línea:
```ini
Environment="FLASK_RUN_PORT=8080"  # Cambia 8080 por tu puerto deseado
```

Luego recarga:
```bash
sudo systemctl daemon-reload
sudo systemctl restart mises-data
```

## Comandos Útiles

```bash
# Ver estado del servicio
sudo systemctl status mises-data

# Ver logs en tiempo real
sudo journalctl -u mises-data -f

# Ver últimos logs
sudo journalctl -u mises-data --since "1 hour ago"

# Reiniciar servicio
sudo systemctl restart mises-data

# Detener servicio
sudo systemctl stop mises-data

# Iniciar servicio
sudo systemctl start mises-data

# Deshabilitar inicio automático
sudo systemctl disable mises-data
```

## Configuración con Variables de Entorno

Puedes agregar un archivo `.env` en el directorio de la aplicación:

```bash
cd /opt/data-curator
nano .env
```

Contenido del `.env`:
```bash
FLASK_SECRET_KEY=tu-clave-secreta-muy-segura-aqui
FLASK_RUN_PORT=5000
FLASK_ENV=production
```

## Configuración con Nginx (Recomendado para Producción)

Si necesitas exponer la aplicación en el puerto 80/443, usa Nginx como proxy inverso:

```bash
sudo nano /etc/nginx/sites-available/mises-data
```

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/mises-data /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Solución de Problemas

### Error: "Failed to start mises-data.service"

Verificar logs:
```bash
sudo journalctl -u mises-data -n 50 --no-pager
```

### Error de permisos

Asegurar que el usuario tenga permisos:
```bash
sudo chown -R www-data:www-data /opt/data-curator
sudo chmod -R 755 /opt/data-curator
```

### Puerto ocupado

Verificar qué proceso usa el puerto:
```bash
sudo lsof -i :5000
# o
sudo netstat -tulpn | grep 5000
```

Matar proceso si es necesario:
```bash
sudo kill -9 <PID>
```

## Seguridad

1. **Cambiar el SECRET_KEY** - Genera una clave segura:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Firewall** - Abre solo el puerto necesario:
   ```bash
   sudo ufw allow 5000/tcp
   # o si usas Nginx
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

3. **HTTPS** - Usa Let's Encrypt para SSL:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d tu-dominio.com
   ```
