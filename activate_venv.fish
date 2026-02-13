# Fish Shell - Auto Virtual Environment Activation
# 
# Este script detecta automáticamente entornos virtuales de Python (.venv)
# al cambiar de directorio y los activa/desactiva según corresponda.
#
# Instalación:
# cp activate_venv.fish ~/.config/fish/functions/__auto_activate_venv.fish
#
# O agregar al final de ~/.config/fish/config.fish:
# source /ruta/a/activate_venv.fish

function __auto_activate_venv --on-variable PWD --description "Auto activate/deactivate virtualenv when changing directories"
    # Evitar ejecución en subshells o comandos
    status --is-command-substitution; and return
    
    # Obtener el directorio actual
    set current_dir (pwd -P)
    
    # Caso 1: Salimos de un directorio con venv activo
    if test -n "$VIRTUAL_ENV"
        # Verificar si el venv activo sigue siendo válido
        if not test -d "$VIRTUAL_ENV"
            deactivate 2>/dev/null
            return
        end
        
        # Verificar si estamos fuera del directorio del proyecto
        set venv_dir (dirname "$VIRTUAL_ENV")
        if not string match -r "^$venv_dir" "$current_dir"
            deactivate 2>/dev/null
            return
        end
    end
    
    # Caso 2: Buscar .venv en el directorio actual o superior
    set search_dir "$current_dir"
    set found_venv ""
    
    while test -n "$search_dir"
        set potential_venv "$search_dir/.venv"
        if test -d "$potential_venv"
            set found_venv "$potential_venv"
            break
        end
        
        # Subir un nivel
        set parent_dir (dirname "$search_dir")
        if test "$parent_dir" = "$search_dir"
            # Llegamos al root
            break
        end
        set search_dir "$parent_dir"
    end
    
    # Caso 3: Activar el venv encontrado
    if test -n "$found_venv"
        # Evitar activar el mismo venv múltiples veces
        if test "$VIRTUAL_ENV" != "$found_venv"
            source "$found_venv/bin/activate.fish" 2>/dev/null
        end
    end
end

# Activar inmediatamente si estamos en un proyecto con .venv
__auto_activate_venv