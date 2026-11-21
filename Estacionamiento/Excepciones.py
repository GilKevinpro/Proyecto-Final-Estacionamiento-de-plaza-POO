"""Excepciones propias del sistema de estacionamiento."""


class ErrorEstacionamiento(Exception):
    """Excepción base para errores del dominio del estacionamiento."""


class CapacidadAgotadaError(ErrorEstacionamiento):
    """Se lanza cuando no hay cajones disponibles o compatibles."""


class VehiculoDuplicadoError(ErrorEstacionamiento):
    """Se lanza cuando el vehículo ya se encuentra dentro del estacionamiento."""


class BoletoNoEncontradoError(ErrorEstacionamiento):
    """Se lanza cuando no existe un boleto activo con la placa o folio indicado."""


class PensionError(ErrorEstacionamiento):
    """Se lanza cuando hay un error en el alta, consulta o renovación de pensión."""


class ArchivoDatosError(ErrorEstacionamiento):
    """Se lanza cuando falta un archivo o su contenido es inválido."""