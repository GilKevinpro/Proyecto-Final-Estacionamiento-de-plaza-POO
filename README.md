# Sistema de Gestión de Estacionamiento - Plaza Comercial

* **Sistema:** Sistema de Gestión de Estacionamiento de una Plaza Comercial
* **Tema:** Tema 2. Estacionamiento de una plaza comercial
* **Integrantes:**
  * Gil Isaias Kevin
  * Mateos Hernandez Sebastian
  * Robledo Julio Cristian Alonso
  * Urtado Portillon Arturo Leonardo

---

## Requisitos e Instalación

* **Versión mínima de Python:** Python 3.10 o superior.
* **Dependencias externas:** Ninguna. El sistema utiliza únicamente la biblioteca estándar de Python (`abc`, `argparse`, `datetime`, `enum`, `json`, `math`, `pathlib`, `random`, `threading`, `time`).

### Pasos de instalación

```bash
git clone https://github.com/GilKevinpro/Proyecto-Final-Estacionamiento-de-plaza-POO.git

cd Proyecto-Final-Estacionamiento-de-plaza-POO
```

---

## Cómo Ejecutar y Probar el Sistema

### 1. Ejecución normal
Inicia el sistema con la configuración base y guarda los cambios en `Datos/estado_actual.json`:

```bash
python -m Estacionamiento.Main
```

### 2. Ejecución con datos de ejemplo precargados
Para probar todas las funciones y reglas de negocio desde el inicio, ejecuta el programa indicando los archivos de ejemplo incluidos en el repositorio:

```bash
python -m Estacionamiento.Main --config Datos/config_inicial.json --estado Datos/estado_ejemplo.json
```

*(Nota: Si los archivos de código están en minúsculas, ejecuta `python -m Estacionamiento.main`).*

### 3. Secuencia de pruebas recomendada en el menú

1. **Consultar ocupación actual (Opción 5):** Muestra los 3 niveles y el detalle por tipo de cajón, reflejando los vehículos ya estacionados (`ABC-123` y `ELE-999`) y los cajones reservados por pensión (`N1-EST-01` y `N1-EST-02`).
2. **Registrar entrada válida (Opción 1):** Registrar una `camioneta` con placa `CAM-500` en la fecha `2026-11-19 11:00`. El sistema asigna el primer cajón estándar disponible del nivel más bajo sin ocupar los reservados por pensión.
3. **Caso rechazado — Vehículo duplicado (Opción 1):** Intentar registrar nuevamente la placa `ABC-123` (que ya está dentro). El sistema rechaza la entrada con un mensaje claro y continúa sin detenerse.
4. **Salida con descuento por compra >= $500 (Opción 2):** Registrar salida de `ABC-123` a las `2026-11-19 12:30` (150 minutos de estancia) indicando un ticket de compra de `$650`. Se descuentan las primeras 2 horas (120 min) y solo se cobran 30 minutos (2 bloques de $8 = `$16.00`).
5. **Salida de auto eléctrico con carga (Opción 2):** Registrar salida de `ELE-999` a las `2026-11-19 11:30` (60 minutos = 4 bloques de $8 = `$32.00`) con `10` kWh cargados (`$40.00`), resultando un total de `$72.00`.
6. **Salida con boleto perdido (Opción 2):** Registrar la salida de `CAM-500` marcando `s` en boleto perdido para verificar el cobro de la tarifa fija de `$250.00`.
7. **Pensión vigente vs. vencida (Opciones 1, 2, 3 y 4):**
   * Consultar `PEN-001` (vigente hasta `2026-12-15`): al entrar ocupa su cajón reservado `N1-EST-01` y al salir paga `$0.00`.
   * Consultar `PEN-002` (vencida el `2026-10-01`): al ingresar en noviembre se le trata y cobra como visitante normal.
   * Dar de alta o renovar una pensión con la Opción 3.
8. **Generar corte de caja (Opción 6):** Ingresar la fecha `2026-11-19` para generar el archivo `Datos/corte_2026-11-19.txt` con entradas, salidas e ingresos por concepto y tipo de vehículo.
9. **Simulación de hora pico (Opción 7):** Ingresar fecha base `2026-11-19 18:00` y `15` vehículos por puerta. Ejecuta 3 hilos de entrada y 2 de salida en paralelo y verifica al final que los conteos coincidan sin doble asignación de cajones.
10. **Caso rechazado — Archivo de configuración dañado:** Ejecutar desde la terminal:
```bash
python -m Estacionamiento.Main --config Datos/config_corrupto.json
```
    El sistema detecta el error de formato, muestra un mensaje claro y termina de forma ordenada sin *traceback*.

---

## Estructura del Proyecto

```text
Proyecto-Final-Estacionamiento-de-plaza-POO/
├── README.md                  # Guía de instalación, ejecución y pruebas
├── .gitignore                 # Archivos y carpetas excluidos del repositorio
├── Datos/                     # Archivos JSON de configuración y datos de ejemplo
│   ├── config_inicial.json
│   ├── config_corrupto.json
│   └── estado_ejemplo.json
├── Docs/                      # Documentación técnica y diagramas
│   ├── Diseño.md
│   └── Uml/
│       ├── diagrama_clases.png
│       └── diagrama_secuencia.png
└── Estacionamiento/           # Paquete principal del sistema
    ├── __init__.py
    ├── Excepciones.py         # Jerarquía de excepciones propias del dominio
    ├── Modelos.py             # Clases Vehiculo, subclases, FabricaVehiculos, Nivel, Cajon, Boleto, Pension
    ├── Tarifas.py             # Estrategias de cobro (patrón Strategy) y configuración tarifaria
    ├── Persistencia.py        # Lectura y escritura en archivos JSON (RepositorioJSON)
    ├── Gestor.py              # Lógica principal, reglas de negocio y sincronización con threading.Lock
    ├── Simulador.py           # Simulación concurrente de hora pico (3 entradas y 2 salidas)
    └── Main.py                # Interfaz de línea de comandos (menú interactivo y argparse)
```