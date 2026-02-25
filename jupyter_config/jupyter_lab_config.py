# Jupyter Server config for Flask embedding.

c.ServerApp.ip = "127.0.0.1"
c.ServerApp.open_browser = False
c.ServerApp.token = ""
c.ServerApp.password = ""
c.ServerApp.disable_check_xsrf = True
c.ServerApp.base_url = "/jupyter/"
c.ServerApp.allow_origin = "*"

c.ServerApp.tornado_settings = {
    "headers": {
        "Content-Security-Policy": "frame-ancestors 'self' http://localhost:5000",
    }
}
