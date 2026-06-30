"""
Servicio para manejar datos de sismos - Conectado a API de USGS
"""

import json
import os
import shutil
import glob
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

from ..models.schemas import (
    SismosCollection,
    SismosStats,
    Sismo,
    SismoProperties,
    Geometry,
)


class SismosService:
    """Servicio para manejar operaciones de sismos con datos del USGS"""

    def __init__(self, data_file: str = "sismosve.json"):
        self.data_file = data_file
        self.logger = logging.getLogger(__name__)
        self.cache = None
        self.last_update = None
        
        # Configuración de la API de USGS
        self.usgs_api_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        self.usgs_params = {
            "format": "geojson",
            "starttime": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "minmagnitude": 4.0,  # Sismos de magnitud significativa
            "orderby": "time",
            "limit": 50,
            "minlatitude": 0.0,    # Límites para Venezuela
            "maxlatitude": 15.0,
            "minlongitude": -75.0,
            "maxlongitude": -60.0,
        }

    def load_sismos(self) -> Optional[SismosCollection]:
        """
        Carga los sismos desde la API del USGS en tiempo real.
        Si falla, intenta cargar desde el archivo local como fallback.
        """
        try:
            # Intentar obtener datos de USGS
            self.logger.info("Consultando API de USGS...")
            
            # Actualizar fecha de inicio para obtener datos recientes
            self.usgs_params["starttime"] = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            response = requests.get(
                self.usgs_api_url, 
                params=self.usgs_params, 
                timeout=15,
                headers={"User-Agent": "SismosVE/1.0"}
            )
            response.raise_for_status()
            
            data = response.json()
            sismos_collection = self._transform_usgs_to_sismos(data)
            
            # Guardar en caché
            self.cache = sismos_collection
            self.last_update = datetime.now()
            
            # También guardar en archivo local para fallback
            self.save_sismos(sismos_collection, create_backup=False)
            
            self.logger.info(f"Datos actualizados desde USGS: {len(sismos_collection.features)} sismos")
            return sismos_collection
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error al obtener datos de USGS: {e}")
            
            # Fallback: intentar cargar desde archivo local
            self.logger.info("Usando datos locales como fallback...")
            return self._load_from_file()
            
        except Exception as e:
            self.logger.error(f"Error inesperado: {e}")
            return self._load_from_file()

    def _load_from_file(self) -> Optional[SismosCollection]:
        """Carga datos desde el archivo local (fallback)"""
        try:
            if not os.path.exists(self.data_file):
                self.logger.warning(f"Archivo {self.data_file} no existe")
                # Crear datos vacíos
                return SismosCollection(type="sismos", features=[])
            
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Si el archivo está vacío o no tiene features, devolver colección vacía
            if not data or not data.get("features"):
                return SismosCollection(type="sismos", features=[])
                
            return SismosCollection(**data)
            
        except Exception as e:
            self.logger.error(f"Error al cargar archivo local: {e}")
            return SismosCollection(type="sismos", features=[])

    def _transform_usgs_to_sismos(self, usgs_data: Dict[str, Any]) -> SismosCollection:
        """
        Convierte el formato GeoJSON de USGS al formato SismosCollection.
        """
        sismos = []
        
        for feature in usgs_data.get('features', []):
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [0, 0, 0])
            
            # Convertir tiempo de Unix a fecha/hora
            time_ms = props.get('time', 0)
            if time_ms > 0:
                date_time = datetime.fromtimestamp(time_ms / 1000)
                fecha_str = date_time.strftime("%d-%m-%Y")
                hora_str = date_time.strftime("%H:%M")
            else:
                fecha_str = "01-01-2024"
                hora_str = "00:00"
            
            # Obtener magnitud
            mag = props.get('mag', 0)
            if mag is None:
                mag = 0
            
            # Crear propiedades
            properties = SismoProperties(
                depth=f"{coords[2]:.1f} km" if coords[2] and coords[2] != 0 else "N/D",
                value=f"{mag:.1f}",
                addressFormatted=props.get('place', 'Ubicación desconocida'),
                time=hora_str,
                country="Venezuela",
                date=fecha_str,
                lat=str(coords[1]) if coords[1] else "0",
                long=str(coords[0]) if coords[0] else "0"
            )
            
            # Crear geometría
            geometry = Geometry(
                type="Point",
                coordinates=[coords[0], coords[1]] if coords[0] and coords[1] else [0, 0],
                marcador="marker"
            )
            
            # Crear sismo
            sismo = Sismo(
                type="Sismo",
                geometry=geometry,
                properties=properties
            )
            
            sismos.append(sismo)
        
        return SismosCollection(type="sismos", features=sismos)

    def save_sismos(self, sismos: SismosCollection, create_backup: bool = True) -> bool:
        """Guarda los sismos en el archivo JSON"""
        try:
            # Crear backup si es necesario
            if create_backup and os.path.exists(self.data_file):
                self._create_backup()

            # Guardar datos
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(sismos.dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"Sismos guardados en {self.data_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error al guardar sismos: {e}")
            return False

    def get_sismos_stats(self, sismos: SismosCollection) -> SismosStats:
        """Calcula estadísticas de los sismos"""
        if not sismos or not sismos.features:
            return SismosStats(
                total_sismos=0,
                magnitud_minima=0.0,
                magnitud_maxima=0.0,
                magnitud_promedio=0.0,
                ultimo_sismo=None,
                ultima_actualizacion=datetime.now(),
            )

        # Obtener magnitudes
        magnitudes = []
        for sismo in sismos.features:
            try:
                mag = float(sismo.properties.value)
                magnitudes.append(mag)
            except (ValueError, TypeError):
                pass

        if not magnitudes:
            magnitudes = [0.0]

        # Obtener último sismo
        ultimo_sismo = self._get_latest_earthquake(sismos.features)

        return SismosStats(
            total_sismos=len(sismos.features),
            magnitud_minima=min(magnitudes),
            magnitud_maxima=max(magnitudes),
            magnitud_promedio=sum(magnitudes) / len(magnitudes),
            ultimo_sismo=ultimo_sismo.dict() if ultimo_sismo else None,
            ultima_actualizacion=self.last_update if self.last_update else datetime.now(),
        )

    def get_sismos_by_magnitude(
        self, sismos: SismosCollection, min_magnitude: float
    ) -> List[Sismo]:
        """Filtra sismos por magnitud mínima"""
        filtered = []
        for sismo in sismos.features:
            try:
                mag = float(sismo.properties.value)
                if mag >= min_magnitude:
                    filtered.append(sismo)
            except (ValueError, TypeError):
                continue
        return filtered

    def get_recent_sismos(
        self, sismos: SismosCollection, limit: int = 10
    ) -> List[Sismo]:
        """Obtiene los sismos más recientes"""
        # Ordenar por fecha/hora (más reciente primero)
        sorted_sismos = sorted(
            sismos.features,
            key=lambda s: self._parse_datetime(s.properties.date, s.properties.time),
            reverse=True,
        )
        return sorted_sismos[:limit]

    def _create_backup(self):
        """Crea un backup del archivo de datos"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.data_file}.backup_{timestamp}"

            shutil.copy2(self.data_file, backup_name)
            self.logger.info(f"Backup creado: {backup_name}")

            # Limpiar backups antiguos
            self._cleanup_old_backups()

        except Exception as e:
            self.logger.warning(f"Error al crear backup: {e}")

    def _cleanup_old_backups(self, max_backups: int = 5):
        """Elimina backups antiguos"""
        try:
            backup_pattern = f"{self.data_file}.backup_*"
            backup_files = glob.glob(backup_pattern)

            if len(backup_files) > max_backups:
                backup_files.sort(key=os.path.getmtime)
                files_to_delete = backup_files[:-max_backups]
                for file_to_delete in files_to_delete:
                    os.remove(file_to_delete)
                    self.logger.info(f"Backup antiguo eliminado: {file_to_delete}")

        except Exception as e:
            self.logger.warning(f"Error al limpiar backups: {e}")

    def _get_latest_earthquake(self, sismos: List[Sismo]) -> Optional[Sismo]:
        """Obtiene el sismo más reciente"""
        if not sismos:
            return None

        return max(
            sismos,
            key=lambda s: self._parse_datetime(s.properties.date, s.properties.time),
        )

    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """Convierte fecha y hora string a datetime"""
        try:
            day, month, year = date_str.split("-")
            hours, minutes = time_str.split(":")
            return datetime(int(year), int(month), int(day), int(hours), int(minutes))
        except:
            return datetime.min
