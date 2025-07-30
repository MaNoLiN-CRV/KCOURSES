import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime, time as dt_time
import random
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import json
import os

# --- Variables Globales ---
automation_running = False
driver = None
# Define the directory for configurations, relative to the script's location
CONFIG_DIR = "configs"

def start_automation_thread(url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars):
    """
    Inicia la automatización en un hilo separado para no bloquear la GUI.
    """
    global automation_running
    if automation_running:
        messagebox.showwarning("Advertencia", "La automatización ya está en ejecución.")
        return

    # Obtener valores de la GUI
    url = url_entry.get()
    username = user_entry.get()
    password = pass_entry.get()
    start_time_str = start_time_entry.get()
    end_time_str = end_time_entry.get()
    selected_days = [day for day, var in days_vars.items() if var.get() == 1]

    # Validaciones
    if not all([url, username, password, start_time_str, end_time_str, selected_days]):
        messagebox.showerror("Error", "Todos los campos son obligatorios.")
        return

    try:
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        messagebox.showerror("Error", "El formato de la hora debe ser HH:MM (e.g., 09:00).")
        return

    automation_running = True
    # Iniciar el hilo
    thread = threading.Thread(target=automation_logic, args=(url, username, password, start_time, end_time, selected_days), daemon=True)
    thread.start()
    messagebox.showinfo("Información", "Automatización iniciada.")


def stop_automation():
    """
    Detiene la automatización y cierra el navegador.
    """
    global automation_running, driver
    if not automation_running:
        messagebox.showwarning("Advertencia", "La automatización no está en ejecución.")
        return

    automation_running = False
    if driver:
        driver.quit()
    messagebox.showinfo("Información", "Automatización detenida.")

def login(target_url, username, password):
    """
    Maneja el inicio de sesión automático en la plataforma.
    """
    global driver
    try:
        # Inicializar el navegador si no está inicializado
        if driver is None:
            options = webdriver.ChromeOptions()
            # Agregar opciones para que el navegador sea menos detectable
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            
            service = ChromeService(executable_path=ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Ejecutar script para ocultar webdriver
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        login_url = "https://centrovirtual.grupo2000.es/login/index.php"
        print(f"Navegando a: {login_url}")
        driver.get(login_url)
        
        # Usar WebDriverWait para esperar a que la página cargue
        wait = WebDriverWait(driver, 10)

        # Verificar si la página cargó correctamente
        current_url = driver.current_url
        print(f"URL actual después de cargar: {current_url}")
        
        if "login" not in current_url:
            messagebox.showerror("Error de Automatización", f"No se pudo acceder a la página de login. URL actual: {current_url}")
            return False

        # Esperar y encontrar el token de login
        try:
            logintoken_element = wait.until(EC.presence_of_element_located((By.NAME, "logintoken")))
            logintoken = logintoken_element.get_attribute("value")
            print(f"Token de login encontrado: {logintoken}")
        except TimeoutException:
            print("Timeout esperando el campo logintoken")
            messagebox.showerror("Error de Automatización", "Timeout esperando el campo logintoken. La página puede estar cargando lentamente.")
            return False
        except NoSuchElementException:
            print("No se pudo encontrar el campo logintoken")
            messagebox.showerror("Error de Automatización", "No se pudo encontrar el campo 'logintoken'. La estructura de la web puede haber cambiado.")
            return False

        # Esperar y rellenar formulario
        try:
            # Esperar y limpiar/rellenar el campo de usuario
            username_field = wait.until(EC.element_to_be_clickable((By.ID, "username")))
            username_field.clear()
            username_field.send_keys(username)
            print(f"Usuario ingresado: {username}")

            # Esperar y limpiar/rellenar el campo de contraseña
            password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
            password_field.clear()
            password_field.send_keys(password)
            print("Contraseña ingresada")

        except TimeoutException:
            print("Timeout esperando los campos de usuario/contraseña")
            messagebox.showerror("Error de Automatización", "Timeout esperando los campos de usuario/contraseña.")
            return False
        except NoSuchElementException as e:
            print(f"Error al encontrar campos de login: {e}")
            messagebox.showerror("Error de Automatización", "No se pudieron encontrar los campos de usuario o contraseña. La estructura de la web puede haber cambiado.")
            return False

        # Enviar formulario
        try:
            login_button = wait.until(EC.element_to_be_clickable((By.ID, "loginbtn")))
            print("Haciendo click en el botón de login...")
            
            # Hacer click usando JavaScript como alternativa más confiable
            driver.execute_script("arguments[0].click();", login_button)
            
            # Esperar más tiempo y usar múltiples estrategias para detectar el cambio
            print("Esperando redirección...")
            max_wait_time = 30  # 30 segundos máximo
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                current_url = driver.current_url
                print(f"URL actual: {current_url}")
                
                # Si la URL cambió y ya no contiene login/index.php, el login fue exitoso
                if "login/index.php" not in current_url:
                    print("Redirección detectada - login exitoso")
                    break
                
                # Si encontramos mensajes de error en la página
                try:
                    error_elements = driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .error, .loginerrors, .text-danger")
                    if error_elements:
                        error_text = " ".join([elem.text for elem in error_elements if elem.text.strip()])
                        if error_text:
                            print(f"Error detectado: {error_text}")
                            messagebox.showerror("Error de Login", f"Error en el login: {error_text}")
                            return False
                except:
                    pass
                
                time.sleep(1)  # Esperar 1 segundo antes de verificar de nuevo
            
            # Verificar si salimos del bucle por timeout
            if time.time() - start_time >= max_wait_time:
                print("Timeout esperando redirección después del login")
                # Intentar una vez más manualmente hacer submit del formulario
                try:
                    form = driver.find_element(By.ID, "login")
                    driver.execute_script("arguments[0].submit();", form)
                    time.sleep(5)
                    if "login/index.php" not in driver.current_url:
                        print("Submit manual exitoso")
                    else:
                        messagebox.showerror("Error de Automatización", "Timeout durante el proceso de login. El sitio puede estar bloqueando navegadores automatizados.")
                        return False
                except:
                    messagebox.showerror("Error de Automatización", "Timeout durante el proceso de login.")
                    return False
            
        except TimeoutException:
            print("Timeout esperando el botón de login")
            messagebox.showerror("Error de Automatización", "Timeout esperando el botón de login.")
            return False
        except NoSuchElementException:
            print("No se pudo encontrar el botón de login")
            messagebox.showerror("Error de Automatización", "No se pudo encontrar el botón de login. La estructura de la web puede haber cambiado.")
            return False

        # Verificar si el login fue exitoso
        current_url_after_login = driver.current_url
        print(f"URL después del login: {current_url_after_login}")
        
        if "login/index.php" in current_url_after_login:
            print("Login falló - aún en página de login")
            # Intentar obtener mensaje de error si existe
            try:
                error_element = driver.find_element(By.CSS_SELECTOR, ".alert-danger, .error, .loginerrors")
                error_message = error_element.text
                print(f"Mensaje de error en la página: {error_message}")
                messagebox.showerror("Error de Login", f"Credenciales incorrectas o error en el inicio de sesión. Mensaje: {error_message}")
            except NoSuchElementException:
                messagebox.showerror("Error de Login", "Credenciales incorrectas o error en el inicio de sesión.")
            return False

        print("Login exitoso")
        # Navegar a la URL final deseada
        print(f"Navegando a la URL objetivo: {target_url}")
        driver.get(target_url)
        time.sleep(3)  # Esperar a que cargue la página objetivo
        return True

    except Exception as e:
        print(f"Error crítico en login: {e}")
        messagebox.showerror("Error Crítico en Login", f"Ha ocurrido un error inesperado durante el login: {e}")
        return False


def automation_logic(url, username, password, start_time, end_time, selected_days):
    """
    Lógica principal de la automatización.
    """
    global automation_running, driver

    try:
        screen_width, screen_height = pyautogui.size()

        while automation_running:
            now = datetime.now()
            current_time = now.time()
            current_weekday = now.weekday()
            day_map = {"L": 0, "M": 1, "X": 2, "J": 3, "V": 4, "S": 5, "D": 6}

            # Comprobar si estamos en el horario y día correctos
            is_scheduled_day = any(current_weekday == day_map[day] for day in selected_days)
            is_in_time_range = start_time <= current_time <= end_time

            if is_scheduled_day and is_in_time_range:
                # Abrir el navegador si no está abierto
                if driver is None:
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando navegador...")
                    options = webdriver.ChromeOptions()
                    # Agregar opciones para que el navegador sea menos detectable
                    options.add_argument('--disable-blink-features=AutomationControlled')
                    options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    options.add_experimental_option('useAutomationExtension', False)
                    options.add_argument('--disable-web-security')
                    options.add_argument('--disable-features=VizDisplayCompositor')
                    
                    service = ChromeService(executable_path=ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                    
                    # Ejecutar script para ocultar webdriver
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    
                    # Hacer login tras abrir el navegador
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Intentando hacer login...")
                    if not login(url, username, password):
                        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Login falló. Deteniendo automatización.")
                        automation_running = False
                        if driver:
                            driver.quit()
                            driver = None
                        return
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Login exitoso.")
                    time.sleep(2)  # Esperar a que la página cargue tras login

                # Verificar que el driver sigue activo
                try:
                    current_url = driver.current_url
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] URL actual: {current_url}")
                except Exception as e:
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Error al verificar URL: {e}")
                    # Reiniciar el navegador si hay problemas
                    if driver:
                        driver.quit()
                    driver = None
                    continue

                # --- ACCIONES PROGRAMADAS ---
                try:
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Refrescando la página...")
                    driver.refresh()
                    time.sleep(5)  # Espera a que recargue
                    
                    # Verificar que la página se cargó correctamente
                    if "login" in driver.current_url:
                        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Sesión expiró. Necesita hacer login nuevamente.")
                        # Reintentar login
                        if not login(url, username, password):
                            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Re-login falló. Deteniendo automatización.")
                            automation_running = False
                            if driver:
                                driver.quit()
                                driver = None
                            return
                except Exception as e:
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Error al refrescar página: {e}")
                    continue

                # Mover el cursor aleatoriamente
                rand_x = random.randint(0, screen_width - 1)
                rand_y = random.randint(0, screen_height - 1)
                pyautogui.moveTo(rand_x, rand_y, duration=0.5)
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Cursor movido a ({rand_x}, {rand_y}).")

                # Esperar 5 minutos antes del próximo ciclo
                print("Esperando 5 minutos para el próximo ciclo...")
                for _ in range(300):  # 300 segundos = 5 minutos
                    if not automation_running:
                        break
                    time.sleep(1)
            else:
                # Cerrar el navegador si está fuera del horario
                if driver is not None:
                    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Fuera de horario. Cerrando navegador...")
                    driver.quit()
                    driver = None

                # Esperar 1 minuto antes de volver a comprobar
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Fuera de horario. Esperando para re-evaluar...")
                for _ in range(60):  # Esperar 1 minuto
                    if not automation_running:
                        break
                    time.sleep(1)

    except Exception as e:
        messagebox.showerror("Error en Automatización", f"Ha ocurrido un error: {e}")
    finally:
        # Asegurarse de cerrar el navegador al finalizar
        if driver:
            driver.quit()
        driver = None
        automation_running = False
        print("El navegador se ha cerrado y la automatización ha finalizado.")

# --- Funciones de Guardar/Cargar Configuración ---

def save_config(url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars):
    """
    Guarda la configuración actual de la GUI en un archivo JSON.
    """
    # Ensure the config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)

    config_data = {
        "url": url_entry.get(),
        "username": user_entry.get(),
        "password": pass_entry.get(),
        "start_time": start_time_entry.get(),
        "end_time": end_time_entry.get(),
        "selected_days": [day for day, var in days_vars.items() if var.get() == 1]
    }

    if not all(config_data.values()):
        messagebox.showwarning("Advertencia", "Algunos campos están vacíos. Guardando solo los valores presentes.")

    file_path = filedialog.asksaveasfilename(
        initialdir=CONFIG_DIR,
        defaultextension=".json",
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
        title="Guardar Configuración como"
    )
    
    if file_path:
        try:
            with open(file_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            messagebox.showinfo("Información", f"Configuración guardada en {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")

def load_config_from_file(file_path, url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars):
    """
    Carga la configuración desde un archivo JSON y actualiza la GUI.
    """
    try:
        with open(file_path, 'r') as f:
            config_data = json.load(f)
        apply_config(config_data, url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars)
        messagebox.showinfo("Información", f"Configuración '{os.path.basename(file_path)}' cargada correctamente.")
    except FileNotFoundError:
        messagebox.showerror("Error", "Archivo de configuración no encontrado.")
    except json.JSONDecodeError:
        messagebox.showerror("Error", "Error al leer el archivo JSON. Asegúrese de que sea un archivo JSON válido.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar la configuración: {e}")

def load_config(url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars):
    """
    Permite al usuario seleccionar un archivo de configuración JSON para cargar.
    """
    file_path = filedialog.askopenfilename(
        initialdir=CONFIG_DIR,
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
        title="Seleccionar Archivo de Configuración"
    )
    if file_path:
        load_config_from_file(file_path, url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars)

def apply_config(config_data, url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars):
    """
    Aplica la configuración cargada a los campos de la GUI.
    """
    url_entry.delete(0, tk.END)
    url_entry.insert(0, config_data.get("url", ""))

    user_entry.delete(0, tk.END)
    user_entry.insert(0, config_data.get("username", ""))

    pass_entry.delete(0, tk.END)
    pass_entry.insert(0, config_data.get("password", ""))

    start_time_entry.delete(0, tk.END)
    start_time_entry.insert(0, config_data.get("start_time", ""))

    end_time_entry.delete(0, tk.END)
    end_time_entry.insert(0, config_data.get("end_time", ""))

    # Reset all checkboxes first
    for var in days_vars.values():
        var.set(0)
    # Set selected checkboxes
    for day in config_data.get("selected_days", []):
        if day in days_vars:
            days_vars[day].set(1)

def create_gui():
    """
    Crea la interfaz gráfica de usuario con Tkinter.
    """
    root = tk.Tk()
    root.title("Automatización Web con Selenium")
    root.geometry("450x550") # Aumentado el tamaño para los nuevos botones

    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # --- Entradas de usuario ---
    ttk.Label(frame, text="URL de la página a refrescar:").grid(column=0, row=0, sticky=tk.W, pady=5)
    url_entry = ttk.Entry(frame, width=40)
    url_entry.grid(column=1, row=0, sticky=(tk.W, tk.E))

    ttk.Label(frame, text="Usuario:").grid(column=0, row=1, sticky=tk.W, pady=5)
    user_entry = ttk.Entry(frame, width=40)
    user_entry.grid(column=1, row=1, sticky=(tk.W, tk.E))

    ttk.Label(frame, text="Contraseña:").grid(column=0, row=2, sticky=tk.W, pady=5)
    pass_entry = ttk.Entry(frame, show="*", width=40)
    pass_entry.grid(column=1, row=2, sticky=(tk.W, tk.E))
    
    # --- Configuración de Horario ---
    time_frame = ttk.LabelFrame(frame, text="Franja Horaria (formato 24h: HH:MM)")
    time_frame.grid(column=0, row=3, columnspan=2, sticky=(tk.W, tk.E), pady=10)
    
    ttk.Label(time_frame, text="Hora Inicio:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
    start_time_entry = ttk.Entry(time_frame, width=10)
    start_time_entry.grid(column=1, row=0, padx=5)

    ttk.Label(time_frame, text="Hora Fin:").grid(column=2, row=0, sticky=tk.W, padx=5, pady=5)
    end_time_entry = ttk.Entry(time_frame, width=10)
    end_time_entry.grid(column=3, row=0, padx=5)

    # --- Días de la Semana ---
    days_frame = ttk.LabelFrame(frame, text="Días de Ejecución")
    days_frame.grid(column=0, row=4, columnspan=2, sticky=(tk.W, tk.E), pady=10)
    
    days = {"L": "Lunes", "M": "Martes", "X": "Miércoles", "J": "Jueves", "V": "Viernes", "S": "Sábado", "D": "Domingo"}
    days_vars = {day: tk.IntVar() for day in days}
    
    col = 0
    for day_short, day_full in days.items():
        ttk.Checkbutton(days_frame, text=day_full, variable=days_vars[day_short]).grid(column=col, row=0, sticky=tk.W, padx=2)
        col += 1

    # --- Botones de Control ---
    button_frame = ttk.Frame(frame)
    button_frame.grid(column=0, row=5, columnspan=2, pady=20)
    
    start_button = ttk.Button(button_frame, text="Iniciar Automatización", 
                              command=lambda: start_automation_thread(url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars))
    start_button.pack(side=tk.LEFT, padx=10)

    stop_button = ttk.Button(button_frame, text="Detener Automatización", command=stop_automation)
    stop_button.pack(side=tk.LEFT, padx=10)

    # --- Botones de Configuración (Guardar/Cargar) ---
    config_button_frame = ttk.Frame(frame)
    config_button_frame.grid(column=0, row=6, columnspan=2, pady=10)

    save_button = ttk.Button(config_button_frame, text="Guardar Configuración", 
                             command=lambda: save_config(url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars))
    save_button.pack(side=tk.LEFT, padx=10)

    load_button = ttk.Button(config_button_frame, text="Cargar Configuración", 
                             command=lambda: load_config(url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars))
    load_button.pack(side=tk.LEFT, padx=10)

    # --- Configurar expansión de columnas ---
    frame.columnconfigure(1, weight=1)
    
    # --- Cargar automáticamente la última configuración si existe o mostrar selector ---
    def on_app_start():
        if not os.path.exists(CONFIG_DIR) or not os.listdir(CONFIG_DIR):
            messagebox.showinfo("Bienvenido", "No se encontraron configuraciones guardadas. Por favor, introduce los datos o guarda una nueva configuración.")
            return

        # Offer the user to load a config
        response = messagebox.askyesno(
            "Cargar Configuración", 
            "¿Deseas cargar una configuración guardada al inicio?"
        )
        if response:
            load_config(url_entry, user_entry, pass_entry, start_time_entry, end_time_entry, days_vars)
        
    root.after(100, on_app_start) # Call after the GUI is fully drawn

    root.mainloop()

if __name__ == "__main__":
    create_gui()