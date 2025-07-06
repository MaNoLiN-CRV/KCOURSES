import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime, time as dt_time
import random
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

# --- Variables Globales ---
automation_running = False
driver = None

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
        login_url = "https://centrovirtual.grupo2000.es/login/index.php"
        driver.get(login_url)
        time.sleep(2) # Espera a que la página cargue

        # Encontrar el token de login
        try:
            logintoken = driver.find_element(By.NAME, "logintoken").get_attribute("value")
        except NoSuchElementException:
            messagebox.showerror("Error de Automatización", "No se pudo encontrar el campo 'logintoken'. La estructura de la web puede haber cambiado.")
            return False

        # Rellenar formulario
        driver.find_element(By.ID, "username").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)

        # Enviar formulario
        driver.find_element(By.ID, "loginbtn").click()
        time.sleep(5) # Esperar a la redirección post-login

        # Verificar si el login fue exitoso (comprobando si seguimos en la página de login)
        if "login/index.php" in driver.current_url:
            messagebox.showerror("Error de Login", "Credenciales incorrectas o error en el inicio de sesión.")
            return False

        # Navegar a la URL final deseada
        driver.get(target_url)
        return True

    except Exception as e:
        messagebox.showerror("Error Crítico en Login", f"Ha ocurrido un error inesperado durante el login: {e}")
        return False


def automation_logic(url, username, password, start_time, end_time, selected_days):
    """
    Lógica principal de la automatización.
    """
    global automation_running, driver

    try:
        # Configuración de Selenium
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        screen_width, screen_height = pyautogui.size()

        # 1. Realizar el login
        if not login(url, username, password):
            automation_running = False
            messagebox.showinfo("Información", "La automatización se ha detenido debido a un fallo en el login.")
            return

        # 2. Bucle principal de automatización
        while automation_running:
            now = datetime.now()
            current_time = now.time()
            # Días de la semana: Lunes (0) a Domingo (6)
            current_weekday = now.weekday()
            day_map = {"L": 0, "M": 1, "X": 2, "J": 3, "V": 4, "S": 5, "D": 6}
            
            # Comprobar si estamos en el horario y día correctos
            is_scheduled_day = any(current_weekday == day_map[day] for day in selected_days)
            is_in_time_range = start_time <= current_time <= end_time

            if is_scheduled_day and is_in_time_range:
                # --- ACCIONES PROGRAMADAS ---
                
                # Refrescar página
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Refrescando la página...")
                driver.refresh()
                time.sleep(5) # Espera a que recargue

                # Mover el cursor aleatoriamente
                rand_x = random.randint(0, screen_width - 1)
                rand_y = random.randint(0, screen_height - 1)
                pyautogui.moveTo(rand_x, rand_y, duration=0.5)
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Cursor movido a ({rand_x}, {rand_y}).")
                
                # Esperar 5 minutos
                print("Esperando 5 minutos para el próximo ciclo...")
                
                # Bucle de espera que verifica si la automatización debe detenerse
                for _ in range(300): # 300 segundos = 5 minutos
                    if not automation_running:
                        break
                    time.sleep(1)
            else:
                # Fuera de horario, esperar un poco antes de volver a comprobar
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Fuera de horario. Esperando para re-evaluar...")
                for _ in range(60): # Esperar 1 minuto
                    if not automation_running:
                        break
                    time.sleep(1)
        
    except Exception as e:
        messagebox.showerror("Error en Automatización", f"Ha ocurrido un error: {e}")
    finally:
        if driver:
            driver.quit()
        automation_running = False
        print("El navegador se ha cerrado y la automatización ha finalizado.")


def create_gui():
    """
    Crea la interfaz gráfica de usuario con Tkinter.
    """
    root = tk.Tk()
    root.title("Automatización Web con Selenium")
    root.geometry("450x450")

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

    # --- Configurar expansión de columnas ---
    frame.columnconfigure(1, weight=1)
    
    root.mainloop()

if __name__ == "__main__":
    create_gui()