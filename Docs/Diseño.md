\# Documento de Diseño - Estacionamiento Plaza Comercial



\## 1. Diagramas UML



\### Diagrama de Clases

Muestra la estructura estática del sistema: la clase abstracta `Vehiculo` y sus subclases (`Motocicleta`, `Auto`, `Camioneta`), la fábrica `FabricaVehiculos`, la composición entre `Nivel` y `Cajon`, el patrón \*Strategy\* en `EstrategiaCobro` y la coordinación desde `GestorEstacionamiento` con `RepositorioJSON`. Se eligió porque permite ver cómo se reparten las responsabilidades y las relaciones entre módulos.



!\[Diagrama de Clases](Uml/diagrama\_clases.png)



\### Diagrama de Secuencia (Registro de Salida y Cobro)

Muestra el orden de llamadas al registrar una salida: el uso del candado `\_lock`, la selección dinámica de la estrategia de cobro según las reglas del estacionamiento, la liberación del cajón y el guardado del estado. Se eligió porque ilustra la operación con mayor lógica de negocio y sincronización del sistema.



!\[Diagrama de Secuencia](Uml/diagrama\_secuencia.png)



\## 2. Decisiones de Diseño



| Concepto | Dónde se usa | Qué problema resuelve |

| :--- | :--- | :--- |

| \*\*Encapsulamiento\*\* | Atributos protegidos (`\_placa`, `\_tiene\_tarjeton`, `\_es\_electrico`, `\_lock`, `\_boletos\_activos`, `\_cajones\_por\_id`) con `@property` en `Vehiculo` y métodos públicos en `GestorEstacionamiento`. | Evita que el estado interno del estacionamiento o los datos del vehículo se modifiquen desde fuera sin pasar por las validaciones y el candado de hilos. |

| \*\*Herencia y clases abstractas\*\* | `Vehiculo` (`ABC`) con subclases `Motocicleta`, `Auto` y `Camioneta`; `EstrategiaCobro` (`ABC`) con `CobroVisitanteEstandar`, `CobroPensionadoVigente` y `CobroBoletoPerdido`. | Define una interfaz común y obliga a cada subclase a implementar sus propias reglas de compatibilidad de cajones y cálculo de tarifas. |

| \*\*Composición y agregación\*\* | Composición entre `Nivel` y `Cajon` (`Nivel` contiene sus cajones); agregación entre `GestorEstacionamiento`, `Nivel` y `RepositorioJSON`. | Modela la estructura física del estacionamiento (los cajones pertenecen a un nivel) y desacopla la lógica de negocio del guardado en archivos. |

| \*\*Polimorfismo\*\* | Llamadas a `vehiculo.tipos\_cajon\_compatibles()` al buscar cajón y `estrategia.calcular(...)` al cobrar una salida. | Elimina cadenas largas de condicionales por tipo de vehículo o modalidad de tarifa dentro de `GestorEstacionamiento`. |

| \*\*Excepciones\*\* | Jerarquía propia en `excepciones.py` (`ErrorEstacionamiento`, `CapacidadAgotadaError`, `VehiculoDuplicadoError`, `BoletoNoEncontradoError`, `PensionError`, `ArchivoDatosError`). | Separa los errores de reglas de negocio y archivos dañados de los fallos internos de Python, permitiendo mostrar avisos claros en consola sin \*tracebacks\*. |

| \*\*Archivos\*\* | `RepositorioJSON` en `persistencia.py` (configuración y estado en JSON) y `generar\_corte\_caja` en `gestor.py` (reporte diario en `.txt`). | Conserva vehículos dentro, pensiones e historial entre ejecuciones y exporta el corte de caja en un formato legible. |

| \*\*Hilos\*\* | `simular\_hora\_pico` en `simulador.py` (3 hilos de entrada y 2 de salida) sincronizados con `threading.Lock` en `GestorEstacionamiento`. | Garantiza exclusión mutua durante horas pico para no asignar un mismo cajón a dos vehículos ni alterar los conteos. |

| \*\*Patrones de diseño\*\* | \*Strategy\* (`EstrategiaCobro` en `tarifas.py`) y \*Factory\* (`FabricaVehiculos.crear` en `modelos.py`). | \*Strategy\* separa las reglas de cobro (visitante, pensionado vigente, boleto perdido); \*Factory\* centraliza la creación de vehículos a partir de la entrada del usuario. |



\## 3. Alternativas Consideradas



1\. \*\*Formato de persistencia (JSON vs. múltiples archivos CSV):\*\*

&#x20;  \* \*Opciones:\* Guardar niveles, boletos, pensiones e historial en varios archivos CSV separados, o usar archivos JSON estructurados.

&#x20;  \* \*Elección:\* Se eligió \*\*JSON\*\* porque permite almacenar estructuras anidadas en un solo archivo, validarlo fácilmente cuando está dañado y usar únicamente el módulo `json` de la biblioteca estándar.

2\. \*\*Prioridad de cajones para autos eléctricos y con tarjetón:\*\*

&#x20;  \* \*Opciones:\* Asignar cualquier cajón compatible sin distinguir prioridad, o priorizar el cajón especializado dentro del nivel más bajo disponible.

&#x20;  \* \*Elección:\* Se eligió \*\*priorizar primero el cajón especializado (`discapacidad` o `electrico`) dentro del nivel más bajo\*\*, dejando `compacto` y `estandar` como respaldo para no rechazar vehículos si los cajones especiales están ocupados.



\## 4. Uso de IA



\* \*\*Qué se pidió:\*\* Apoyo para estructurar los módulos del sistema orientado a objetos, revisar la sincronización con `threading.Lock` y generar el código Mermaid para los diagramas UML.

\* \*\*Qué se usó:\*\* La separación en módulos (`modelos.py`, `tarifas.py`, `persistencia.py`, `gestor.py`, `simulador.py`, `main.py`) y el diseño del patrón \*Strategy\* para las tarifas.

\* \*\*Qué se corrigió:\*\* Se adaptaron las clases para usar constructores `\_\_init\_\_` explícitos y manejo estándar de archivos acorde al curso, y se ajustó la asignación para respetar los cajones reservados por pensión.

\* \*\*Cómo se verificó:\*\* Se revisó la coherencia entre los diagramas UML y el código del repositorio, y se probó el sistema con datos de ejemplo, archivos con errores y la simulación de hora pico.



\## 5. Contribuciones del Equipo



\* \*\*Gil Isaias Kevin:\*\* Implementación de `excepciones.py`, `gestor.py`, `simulador.py`, `main.py` y estructura inicial del repositorio.

\* \*\*Urtado Portillon Arturo Leonardo:\*\* Implementación de `modelos.py`, `tarifas.py` y `persistencia.py`.

\* \*\*Mateos Hernández Sebastian:\*\* Elaboración de diagramas UML (`Docs/Uml/`), redacción de `Docs/diseno.md` y documentación en `README.md`.

\*\*Robledo Julio Cristian Alonso:\*\* Creación de archivos de configuración y datos de ejemplo en `Datos/` (`config\_inicial.json`, `config\_corrupto.json`, `estado\_ejemplo.json`) y pruebas de validación del sistema.

