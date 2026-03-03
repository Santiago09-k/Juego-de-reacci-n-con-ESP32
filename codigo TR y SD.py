from machine import Pin, mem32 # Importa el manejo de pines y acceso a memoria de 32 bits
import time # Importa funciones para el manejo del tiempo
import random # Importa funciones para generar numeros aleatorios

# REGISTROS GPIO ESP32
GPIO_OUT_W1TS = 0x3FF44008 # Direccion del registro para poner en ALTO (ON) los pines
GPIO_OUT_W1TC = 0x3FF4400C # Direccion del registro para poner en BAJO (OFF) los pines

def led_on(pin):
    mem32[GPIO_OUT_W1TS] = (1 << pin) # Enciende el pin desplazando un bit a su posicion en memoria

def led_off(pin):
    mem32[GPIO_OUT_W1TC] = (1 << pin) # Apaga el pin desplazando un bit a su posicion en memoria

def apagar_todo():
    for pin in Salidas: # Recorre la lista de pines configurados como salidas
        led_off(pin) # Apaga cada pin de la lista

# ANTIREBOTE POR SOFTWARE
def leer_boton(boton):
    if boton.value(): # Si el boton detecta una pulsacion (valor 1)
        time.sleep_ms(20) # Espera 20 milisegundos para ignorar el ruido electrico
        if boton.value(): # Si despues del tiempo sigue presionado
            while boton.value(): # Mientras el boton se mantenga presionado
                pass # No hace nada, espera a que el usuario lo suelte
            return True # Retorna verdadero indicando una pulsacion valida
    return False # Retorna falso si no hubo pulsacion

# CONFIGURAR SALIDAS
Pin(2, Pin.OUT) # Configura el pin GPIO 2 como salida
Pin(4, Pin.OUT) # Configura el pin GPIO 4 como salida
Pin(5, Pin.OUT) # Configura el pin GPIO 5 como salida
Pin(18, Pin.OUT) # Configura el pin GPIO 18 como salida

Salidas = [2, 4, 5, 18] # Lista que agrupa los numeros de los pines de salida
apagar_todo() # Asegura que todos los pines inicien apagados

botonesp1 = [
    Pin(12, Pin.IN, Pin.PULL_DOWN), # Boton 1 del Jugador 1 en pin 12 con pull-down
    Pin(13, Pin.IN, Pin.PULL_DOWN), # Boton 2 del Jugador 1 en pin 13 con pull-down
    Pin(14, Pin.IN, Pin.PULL_DOWN), # Boton 3 del Jugador 1 en pin 14 con pull-down
    Pin(27, Pin.IN, Pin.PULL_DOWN)  # Boton 4 del Jugador 1 en pin 27 con pull-down
]

botonesp2 = [
    Pin(26, Pin.IN, Pin.PULL_DOWN), # Boton 1 del Jugador 2 en pin 26 con pull-down
    Pin(25, Pin.IN, Pin.PULL_DOWN), # Boton 2 del Jugador 2 en pin 25 con pull-down
    Pin(33, Pin.IN, Pin.PULL_DOWN), # Boton 3 del Jugador 2 en pin 33 con pull-down
    Pin(32, Pin.IN, Pin.PULL_DOWN)  # Boton 4 del Jugador 2 en pin 32 con pull-down
]

btn_start = Pin(23, Pin.IN, Pin.PULL_DOWN) # Pin 23 configurado como boton de inicio
btn_stop  = Pin(22, Pin.IN, Pin.PULL_DOWN) # Pin 22 configurado como boton de parada
btn_simon = Pin(21, Pin.IN, Pin.PULL_DOWN) # Pin 21 configurado como boton de Simon Dice

print("+"*50) # Imprime linea decorativa
print("\n             COMBBOY BEBOP GAME         \n") # Imprime titulo del juego
print("+"*50) # Imprime linea decorativa
print("\n\nEsperando inicio...\n") # Mensaje de espera inicial

# ---------------- Señal para Simón Dice (IRQ simple) ----------------
# El handler solo marca la petición; la ejecución se hace en el bucle principal.
simon_requested = False
_last_simon_irq = 0  # para anti-rebote de IRQ (ms)
SIMON_IRQ_DEBOUNCE_MS = 300

def _simon_irq_handler(pin):
    global simon_requested, _last_simon_irq
    now = time.ticks_ms()
    if time.ticks_diff(now, _last_simon_irq) > SIMON_IRQ_DEBOUNCE_MS:
        _last_simon_irq = now
        # Toggle behavior: if we're inside Simón (simon_active) then set request to exit,
        # otherwise set request to start Simón. We'll use the same flag for both.
        simon_requested = True

# registrar IRQ (solo marca la petición)
btn_simon.irq(trigger=Pin.IRQ_RISING, handler=_simon_irq_handler)

# MENU
def seleccionar_modo():
    print("") # Salto de linea
    print("\n=== SELECCIONAR JUGADORES ===") # Titulo del menu
    print("\n-P1 Botón 1 → 1 JUGADOR\n") # Instruccion para 1 jugador
    print("\n-P2 Botón 1 → 2 JUGADORES\n") # Instruccion para 2 jugadores
    print("="*30) # Linea separadora

    while True: # Bucle infinito hasta que se elija una opcion
        if leer_boton(botonesp1[0]): # Si el Jugador 1 presiona su primer boton
            jugadores = 1 # Establece modo 1 jugador
            break # Sale del bucle
        if leer_boton(botonesp2[0]): # Si el Jugador 2 presiona su primer boton
            jugadores = 2 # Establece modo 2 jugadores
            break # Sale del bucle

    print("\n##### SELECCIONAR DIFICULTAD #####\n") # Titulo de menu dificultad
    print("\n-P1 Botón 2 → NORMAL\n") # Instruccion para dificultad normal
    print("\n-P2 Botón 2 → DIFICIL\n") # Instruccion para dificultad dificil
    print("="*35) # Linea separadora

    while True: # Bucle infinito hasta elegir dificultad
        if leer_boton(botonesp1[1]): # Si se presiona el segundo boton de P1
            dificultad = 1 # Dificultad normal
            break # Sale del bucle
        if leer_boton(botonesp2[1]): # Si se presiona el segundo boton de P2
            dificultad = 2 # Dificultad dificil
            break # Sale del bucle

    return jugadores, dificultad # Devuelve las selecciones hechas

# SIMÓN DICE
def simon_dice():
    """
    Simón Dice ejecutado desde el bucle principal.
    Si durante Simón se presiona btn_simon (IRQ), simon_requested se vuelve True
    y aquí detectamos esa petición para salir inmediatamente y regresar al juego.
    """
    global simon_requested
    print("\n           Simón dice") # Titulo del minijuego
    valor_ronda = 1 # Contador de rondas de memoria
    secuencia_elejida = [] # Lista para almacenar la secuencia de colores/pines

    # marcar que estamos dentro de simon para que la IRQ pueda indicar salida
    while True: # Bucle del juego de memoria
        # Si se solicitó salir antes de generar la siguiente ronda, salir
        if simon_requested:
            # consumir la petición de salida y regresar
            simon_requested = False
            print("\nSimón Dice cancelado por el usuario. Regresando al modo normal...")
            apagar_todo()
            time.sleep(0.2)
            break

        eleccion = random.randint(0, len(Salidas) - 1) # Elige un indice de LED al azar
        secuencia_elejida.append(eleccion) # Lo añade a la secuencia actual

        print("\n       Ronda ", valor_ronda) # Muestra el numero de ronda

        # Mostrar secuencia
        for idx in secuencia_elejida: # Recorre la secuencia generada
            # permitir salir mientras se muestran LEDs
            if simon_requested:
                simon_requested = False
                print("\nSimón Dice cancelado por el usuario durante la reproducción. Regresando...")
                apagar_todo()
                time.sleep(0.2)
                return
            led_on(Salidas[idx]) # Enciende el LED correspondiente
            time.sleep(0.5) # Lo mantiene encendido medio segundo
            led_off(Salidas[idx]) # Lo apaga
            time.sleep(0.2) # Breve pausa entre LEDs

        secuencia_jugador = [] # Lista para almacenar la respuesta del jugador
        print("Esperando respuesta del jugador") # Mensaje de aviso

        while len(secuencia_jugador) < len(secuencia_elejida): # Mientras falten pasos por responder
            # permitir salir antes de leer botones
            if simon_requested:
                simon_requested = False
                print("\nSimón Dice cancelado por el usuario durante la entrada. Regresando...")
                apagar_todo()
                time.sleep(0.2)
                return

            boton_presionado = False # Bandera para detectar accion
            for j in range(len(botonesp1)): # Revisa los 4 botones del Jugador 1
                if botonesp1[j].value() == 1: # Si detecta que un boton se pulsa
                    # permitir salir justo antes de dar feedback
                    if simon_requested:
                        simon_requested = False
                        print("\nSimón Dice cancelado por el usuario justo antes del feedback. Regresando...")
                        apagar_todo()
                        time.sleep(0.2)
                        return

                    led_on(Salidas[j]) # Enciende el LED para dar feedback visual
                    time.sleep(0.5) # Pausa de medio segundo
                    led_off(Salidas[j]) # Apaga el LED
                    time.sleep(0.2) # Pausa de separacion

                    while botonesp1[j].value() == 1: # Espera a que el boton se suelte
                        time.sleep(0.001) # Pequeña espera para no saturar el procesador

                    print("Botón presionado ", j) # Muestra que boton se registro
                    secuencia_jugador.append(j) # Agrega el boton a la respuesta del jugador
                    boton_presionado = True # Marca que hubo una accion
                    break # Sale del for para procesar la siguiente entrada
            if not boton_presionado: # Si no se ha presionado nada
                time.sleep(0.01) # Espera minima para continuar el escaneo

        # Comparar secuencia
        iguales = True # Bandera de verificacion
        for k in range(len(secuencia_elejida)): # Recorre ambas secuencias
            if secuencia_jugador[k] != secuencia_elejida[k]: # Si un paso no coincide
                iguales = False # Marca como error

        if iguales: # Si toda la secuencia fue correcta
            valor_ronda += 1 # Aumenta la dificultad
            print("\nCorrecto!") # Mensaje de exito
            time.sleep(0.1) # Breve pausa
        else: # Si hubo un error
            print("\nIncorrecto! Juego terminado.") # Mensaje de fallo
            print("\nSecuencia correcta:", secuencia_elejida) # Muestra la respuesta que era
            time.sleep(2) # Pausa para ver el error
            print("\nRegresando al modo normal...") # Aviso de retorno
            break # Sale de la funcion Simon Dice

# LOOP PRINCIPAL
while True: # Bucle infinito del programa
    # Si la IRQ marcó Simón Dice fuera de partida, atenderla aquí
    if simon_requested:
        # consumir la petición de inicio Simón
        simon_requested = False
        apagar_todo()
        simon_dice()
        apagar_todo()
        print("\nEsperando inicio...\n")

    if leer_boton(btn_start): # Si se presiona el boton de inicio
        jugadores, dificultad = seleccionar_modo() # Llama al menu de configuracion
        print("\n=== JUEGO INICIADO ===") # Mensaje de juego activo

        p1_SCORE = 0 # Inicializa puntaje Jugador 1
        p2_SCORE = 0 # Inicializa puntaje Jugador 2
        p1_errores = 0 # Contador de fallos Jugador 1
        p2_errores = 0 # Contador de fallos Jugador 2

        RA = 1 # Inicializa contador de rondas (Round Activation)
        juego_activo = True # Bandera de juego en curso

        while juego_activo: # Bucle de las rondas de reaccion
            print("\nRONDA:", RA) # Muestra numero de ronda

            if jugadores == 1: # Si solo hay un jugador
                print("P1:", p1_SCORE) # Muestra puntos de P1
            else: # Si hay dos jugadores
                print("P1:", p1_SCORE, "| P2:", p2_SCORE) # Muestra puntos de ambos

            apagar_todo() # Apaga LEDs antes de empezar
            activa = random.randint(0, 3) # Selecciona el LED que se encendera al azar

            if dificultad == 1: # Configuracion dificultad Normal
                tiempo_espera = random.randint(1, 10) # Tiempo de espera largo (1-10 seg)
                penalizacion = 2 # Resta 2 puntos por error
            else: # Configuracion dificultad Dificil
                tiempo_espera = random.randint(1, 3) # Tiempo de espera corto (1-3 seg)
                penalizacion = 3 # Resta 3 puntos por error

            inicio_espera = time.ticks_ms() # Registra el tiempo actual en milisegundos

            while time.ticks_diff(time.ticks_ms(), inicio_espera) < tiempo_espera * 1000: # Durante la espera
                if leer_boton(btn_stop): # Si se presiona el boton de detener
                    juego_activo = False # Termina el juego
                    break # Sale del bucle de espera

                # Interrupción: Simón Dice (activada por IRQ)
                if simon_requested: # Si la IRQ marcó Simón Dice
                    simon_requested = False
                    apagar_todo()
                    simon_dice()
                    print("\nVolviendo al juego de reacción...\n") # Aviso al volver
                    inicio_espera = time.ticks_ms() # Reinicia el cronometro de espera
                    apagar_todo()
                    break # Salta a la siguiente fase de la ronda

                for i in range(4): # Escanea botones del P1 durante la espera
                    if leer_boton(botonesp1[i]): # Si presiona antes de tiempo
                        p1_SCORE = max(0, p1_SCORE - 5) # Resta 5 puntos (minimo 0)
                        p1_errores += 1 # Suma un error
                        print("P1 se adelantó (-5)") # Mensaje de advertencia

                if jugadores == 2: # Escanea botones del P2 si aplica
                    for i in range(4): # Recorre sus 4 botones
                        if leer_boton(botonesp2[i]): # Si presiona antes de tiempo
                            p2_SCORE = max(0, p2_SCORE - 5) # Resta 5 puntos
                            p2_errores += 1 # Suma un error
                            print("P2 se adelantó (-5)") # Mensaje de advertencia

            if not juego_activo: # Si se detuvo el juego por el boton Stop
                break # Sale del bucle de rondas

            # Activar LED
            led_on(Salidas[activa]) # Enciende el LED objetivo
            print("¡FIRE!") # Señal de disparo/reaccion

            inicio = time.ticks_ms() # Inicia cronometro de reaccion
            ganador = 0 # Variable para identificar quien gano la ronda
            tiempo_reaccion = 0 # Almacena el tiempo final
            p1_fallo = False # Registro si P1 fallo en esta ronda
            p2_fallo = False # Registro si P2 fallo en esta ronda

            # Si la IRQ marcó Simón Dice justo antes de la fase de reaccion, atenderla
            if simon_requested:
                simon_requested = False
                apagar_todo()
                simon_dice()
                apagar_todo()
                # reencender LED y reiniciar el inicio para mantener lógica simple
                led_on(Salidas[activa])
                inicio = time.ticks_ms()
                print("Reanudando reacción...")

            while ganador == 0: # Mientras nadie haya acertado
                if leer_boton(btn_stop): # Si se pulsa stop durante la reaccion
                    juego_activo = False # Detiene el juego
                    break # Sale del bucle

                # Si la IRQ marcó Simón Dice durante la reaccion, atenderla
                if simon_requested:
                    simon_requested = False
                    apagar_todo()
                    simon_dice()
                    apagar_todo()
                    # reencender LED y reiniciar el inicio para mantener lógica simple
                    led_on(Salidas[activa])
                    inicio = time.ticks_ms()
                    print("Reanudando reacción...")

                for i in range(4): # Verifica botones del Jugador 1
                    if leer_boton(botonesp1[i]): # Si P1 presiona un boton
                        if i == activa: # Si es el boton correcto
                            tiempo_reaccion = time.ticks_diff(time.ticks_ms(), inicio) # Calcula tiempo
                            ganador = 1 # P1 gana la ronda
                            p1_SCORE += 10 # Suma 10 puntos
                        else: # Si presiona el boton equivocado
                            p1_SCORE = max(0, p1_SCORE - penalizacion) # Resta puntos
                            p1_errores += 1 # Suma error
                            print("P1 incorrecto") # Aviso de fallo
                            p1_fallo = True # Marca fallo de P1

                if jugadores == 2: # Verifica botones del Jugador 2
                    for i in range(4): # Recorre sus 4 botones
                        if leer_boton(botonesp2[i]): # Si P2 presiona un boton
                            if i == activa: # Si es el correcto
                                tiempo_reaccion = time.ticks_diff(time.ticks_ms(), inicio) # Calcula tiempo
                                ganador = 2 # P2 gana la ronda
                                p2_SCORE += 10 # Suma 10 puntos
                            else: # Si presiona el equivocado
                                p2_SCORE = max(0, p2_SCORE - penalizacion) # Resta puntos
                                p2_errores += 1 # Suma error
                                print("P2 incorrecto") # Aviso de fallo
                                p2_fallo = True # Marca fallo de P2

                if jugadores == 2 and p1_fallo and p2_fallo: # Si ambos fallan el objetivo
                    print("Ambos fallaron - siguiente ronda") # Mensaje de empate por error
                    break # Pasa a la siguiente ronda

                time.sleep_ms(10)

            apagar_todo() # Apaga el LED objetivo

            if ganador == 1: # Si gano el Jugador 1
                print("PLAYER 1 | Tiempo:", tiempo_reaccion, "ms") # Muestra su tiempo
            elif ganador == 2: # Si gano el Jugador 2
                print("PLAYER 2 | Tiempo:", tiempo_reaccion, "ms") # Muestra su tiempo

            RA += 1 # Incrementa el contador de rondas
            time.sleep(2) # Pausa de 2 segundos antes de la siguiente ronda

        apagar_todo() # Asegura que todo quede apagado al finalizar
        print("\n=== FIN DEL JUEGO ===\n") # Mensaje de cierre
        print("Jugador 1:", p1_SCORE, "| Errores:", p1_errores, "\n") # Resumen P1

        if jugadores == 2: # Resumen P2 si aplica
            print("Jugador 2:", p2_SCORE, "| Errores:", p2_errores, "\n")

        print("\nEsperando nuevo inicio...\n") # Regresa al estado de espera inicial

    # pequeña espera para liberar CPU y evitar bucle ocupado
    time.sleep_ms(50)