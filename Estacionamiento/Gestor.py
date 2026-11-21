"""Lógica principal del estacionamiento protegida con candado para hilos."""

from datetime import datetime, timedelta
from pathlib import Path
import threading

from .excepciones import (
    ArchivoDatosError,
    BoletoNoEncontradoError,
    CapacidadAgotadaError,
    PensionError,
    VehiculoDuplicadoError,
)

from .modelos import Boleto, Pension, RegistroMovimiento, TipoCajon

from .tarifas import (
    CobroBoletoPerdido,
    CobroPensionadoVigente,
    CobroVisitanteEstandar,
)
