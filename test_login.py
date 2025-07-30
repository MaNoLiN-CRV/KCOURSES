#!/usr/bin/env python3
"""
Script de prueba para verificar el login
"""
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

def test_login():
    # Configurar el navegador con opciones anti-detección
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    
    service = ChromeService(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Ejecutar script para ocultar webdriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        # Navegar a la página de login
        login_url = "https://centrovirtual.grupo2000.es/login/index.php"
        print(f"Navegando a: {login_url}")
        driver.get(login_url)
        
        wait = WebDriverWait(driver, 20)
        
        # Esperar a que la página cargue completamente
        print("Esperando que la página cargue completamente...")
        time.sleep(3)
        
        current_url = driver.current_url
        print(f"URL actual: {current_url}")
        
        # Buscar el token de login
        try:
            logintoken_element = wait.until(EC.presence_of_element_located((By.NAME, "logintoken")))
            logintoken = logintoken_element.get_attribute("value")
            print(f"Token encontrado: {logintoken}")
        except TimeoutException:
            print("ERROR: No se pudo encontrar el token de login")
            return False
        
        # Pedirle al usuario las credenciales
        username = input("Ingrese el usuario: ")
        password = input("Ingrese la contraseña: ")
        
        # Rellenar el formulario
        try:
            username_field = wait.until(EC.element_to_be_clickable((By.ID, "username")))
            username_field.clear()
            username_field.send_keys(username)
            print(f"Usuario ingresado: {username}")
            
            password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
            password_field.clear() 
            password_field.send_keys(password)
            print("Contraseña ingresada")
            
        except TimeoutException:
            print("ERROR: No se pudieron encontrar los campos de usuario/contraseña")
            return False
        
        # Hacer click en el botón de login
        try:
            login_button = wait.until(EC.element_to_be_clickable((By.ID, "loginbtn")))
            print("Haciendo click en el botón de login...")
            
            # Usar JavaScript para hacer click
            driver.execute_script("arguments[0].click();", login_button)
            
            # Esperar y monitorear la redirección
            print("Monitoreando redirección...")
            max_wait_time = 30
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                current_url = driver.current_url
                print(f"URL actual: {current_url}")
                
                if "login/index.php" not in current_url:
                    print("¡LOGIN EXITOSO! - Redirección detectada")
                    print(f"Nueva URL: {current_url}")
                    return True
                
                # Verificar errores
                try:
                    error_elements = driver.find_elements(By.CSS_SELECTOR, ".alert-danger, .error, .loginerrors, .text-danger")
                    if error_elements:
                        error_text = " ".join([elem.text for elem in error_elements if elem.text.strip()])
                        if error_text:
                            print(f"ERROR EN LA PÁGINA: {error_text}")
                            return False
                except:
                    pass
                
                time.sleep(2)
            
            print("TIMEOUT: No se detectó redirección")
            return False
            
        except TimeoutException:
            print("ERROR: No se pudo encontrar el botón de login")
            return False
        
    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        return False
    
    finally:
        # Mantener el navegador abierto para inspección manual
        input("Presione Enter para cerrar el navegador...")
        driver.quit()

if __name__ == "__main__":
    success = test_login()
    if success:
        print("✓ Test de login exitoso")
        sys.exit(0)
    else:
        print("✗ Test de login falló")
        sys.exit(1)
