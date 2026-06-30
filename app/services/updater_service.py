"""
Servicio de actualización de datos con scheduler
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .sismos_service import SismosService


class UpdaterService:
    """
    Servicio para actualizar datos de sismos automáticamente.
    Ahora solo recarga los datos desde la API de USGS.
    """

    def __init__(self, sismos_service: SismosService, update_interval: int = 300):
        self.sismos_service = sismos_service
        self.update_interval = update_interval  # segundos
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.last_update = None
        self.update_stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_error": None,
        }

    async def start_scheduler(self):
        """Inicia el scheduler de actualizaciones"""
        if self.is_running:
            self.logger.warning("El scheduler ya está ejecutándose")
            return

        try:
            # Agregar job de actualización
            self.scheduler.add_job(
                self.update_sismos_data,
                IntervalTrigger(seconds=self.update_interval),
                id="update_sismos",
                name="Actualizar datos de sismos",
                replace_existing=True,
            )

            # Iniciar scheduler
            self.scheduler.start()
            self.is_running = True

            # Ejecutar primera actualización inmediatamente
            await self.update_sismos_data()

            self.logger.info(
                f"Scheduler iniciado. Actualizando cada {self.update_interval} segundos"
            )

        except Exception as e:
            self.logger.error(f"Error al iniciar scheduler: {e}")
            raise

    async def stop_scheduler(self):
        """Detiene el scheduler"""
        if not self.is_running:
            return

        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            self.logger.info("Scheduler detenido")
        except Exception as e:
            self.logger.error(f"Error al detener scheduler: {e}")

    async def update_sismos_data(self) -> bool:
        """Actualiza los datos de sismos desde la API de USGS"""
        self.logger.info("Iniciando actualización de datos de sismos...")
        self.update_stats["total_updates"] += 1

        try:
            # Recargar datos desde USGS
            sismos_data = self.sismos_service.load_sismos()

            if sismos_data and sismos_data.features:
                self.update_stats["successful_updates"] += 1
                self.last_update = datetime.now()

                # Log estadísticas
                stats = self.sismos_service.get_sismos_stats(sismos_data)
                self.logger.info(
                    f"Actualización completada: {stats.total_sismos} sismos, "
                    f"magnitud {stats.magnitud_minima:.1f}-{stats.magnitud_maxima:.1f} "
                    f"(promedio: {stats.magnitud_promedio:.1f})"
                )
                return True
            else:
                self.logger.warning("No se obtuvieron datos de sismos")
                self.update_stats["failed_updates"] += 1
                return False

        except Exception as e:
            self.logger.error(f"Error en actualización: {e}")
            self.update_stats["failed_updates"] += 1
            self.update_stats["last_error"] = str(e)
            return False

    async def force_update(self) -> bool:
        """Fuerza una actualización inmediata"""
        self.logger.info("Forzando actualización inmediata...")
        return await self.update_sismos_data()

    def get_update_status(self) -> dict:
        """Obtiene el estado del updater"""
        return {
            "is_running": self.is_running,
            "update_interval": self.update_interval,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "stats": self.update_stats,
            "next_update": self._get_next_update_time(),
        }

    def _get_next_update_time(self) -> Optional[str]:
        """Calcula la hora de la próxima actualización"""
        if not self.is_running or not self.last_update:
            return None

        try:
            from datetime import timedelta

            next_update = self.last_update + timedelta(seconds=self.update_interval)
            return next_update.isoformat()
        except:
            return None
