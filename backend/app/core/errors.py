
"""gemeinsame Fehlerarten"""

import logging


class BenchmarkError(Exception):

    user_message = "Bei der Benchmark-Ausführung ist ein Fehler aufgetreten."
    """retry_allowed = False/True"""

    def __init__(self) -> None:
        super().__init__(self.user_message)

class ProviderAccessError(BenchmarkError):
    user_message = "Der Zugriff auf den Provider wurde abgelehnt.."

class RateLimitError(BenchmarkError):
    user_message = "Die Anfrage wurde wegen eines Limits des Providers abgelehnt."
    """retry_allowed = False/True"""

class ProviderTimeoutError(BenchmarkError):
    user_message = "Die Anfrage an den Provider konnte nicht innerhalb des Zeitlimits abgeschlossen werden."
    """retry_allowed = False/True"""

class ProviderConnectionError(BenchmarkError):
    user_message = "Die Verbindung zum Provider konnte nicht hergestellt werden oder wurde unterbrochen."
    """retry_allowed = True/False"""

class InvalidProviderRequestError(BenchmarkError):
    user_message = "Die Anfrage an den Provider  ist ungültig."

class UnsupportedCapabilityError(BenchmarkError):
    user_message = "Die ausgewählte Pipeline unterstützt die angeforderte Sprachrichtung oder Funktion nicht."


class ProviderServiceError(BenchmarkError):
    user_message = "Beim Provider ist ein technischer Fehler aufgetreten."


class InvalidProviderOutputError(BenchmarkError):
    user_message = "Der Provider hat keine gültige Audioausgabe geliefert."

class UnexpectedProviderError(BenchmarkError):
    user_message = "Die Anfrage an den Provider ist fehlgeschlagen"
class BenchmarkInfrastructureError(BenchmarkError):
    user_message = "Die Benchmark-Ausführung wurde durch einen technischen Fehler unterbrochen."

class EvaluationError(BenchmarkError):
    user_message = "Die automatische Auswertung konnte nicht abgeschlossen werden."


def log_benchmark_error(
    logger: logging.Logger,
    benchmark_error: BenchmarkError,
) -> None:

    logger.warning(
        "Benchmark error: error_type=%s retry_allowed=%s",
        type(benchmark_error).__name__,
        benchmark_error.retry_allowed,
    )
