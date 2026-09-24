"""Stockage objet — MinIO/S3 avec repli sur le système de fichiers local."""

from __future__ import annotations

import hashlib
import mimetypes
import uuid
from datetime import date
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StockageObjet:
    """Façade de stockage : S3/MinIO si disponible, disque local sinon."""

    def __init__(self) -> None:
        self._client = None
        self._s3_disponible: bool | None = None
        self._racine_locale = Path(settings.storage_local_fallback)

    # ---------- Client ----------

    def _obtenir_client(self):
        if self._client is None:
            import boto3
            from botocore.config import Config

            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
                config=Config(signature_version="s3v4", retries={"max_attempts": 2}),
            )
        return self._client

    def _verifier_s3(self) -> bool:
        if self._s3_disponible is not None:
            return self._s3_disponible
        try:
            client = self._obtenir_client()
            existants = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
            if settings.s3_bucket not in existants:
                client.create_bucket(Bucket=settings.s3_bucket)
            self._s3_disponible = True
        except Exception as exc:  # pragma: no cover - dépend de l'infrastructure
            logger.warning("Stockage objet indisponible, repli local : %s", exc)
            self._s3_disponible = False
        return self._s3_disponible

    # ---------- API ----------

    @staticmethod
    def construire_chemin(domaine: str, nom_fichier: str) -> str:
        """Produit un chemin de stockage daté et unique."""
        aujourd_hui = date.today()
        extension = Path(nom_fichier).suffix.lower()
        identifiant = uuid.uuid4().hex
        return f"{domaine}/{aujourd_hui:%Y/%m}/{identifiant}{extension}"

    def deposer(self, chemin: str, contenu: bytes, type_mime: str | None = None) -> str:
        type_mime = type_mime or mimetypes.guess_type(chemin)[0] or "application/octet-stream"

        if self._verifier_s3():
            self._obtenir_client().put_object(
                Bucket=settings.s3_bucket,
                Key=chemin,
                Body=contenu,
                ContentType=type_mime,
            )
            return chemin

        cible = self._racine_locale / chemin
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(contenu)
        return chemin

    def lire(self, chemin: str) -> bytes:
        if self._verifier_s3():
            reponse = self._obtenir_client().get_object(Bucket=settings.s3_bucket, Key=chemin)
            return reponse["Body"].read()
        return (self._racine_locale / chemin).read_bytes()

    def supprimer(self, chemin: str) -> None:
        if self._verifier_s3():
            self._obtenir_client().delete_object(Bucket=settings.s3_bucket, Key=chemin)
            return
        cible = self._racine_locale / chemin
        if cible.exists():
            cible.unlink()

    def url_signee(self, chemin: str, duree_secondes: int = 3600) -> str:
        if self._verifier_s3():
            return self._obtenir_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.s3_bucket, "Key": chemin},
                ExpiresIn=duree_secondes,
            )
        return f"/api/v1/documents/fichier/{chemin}"

    @staticmethod
    def empreinte(contenu: bytes) -> str:
        return hashlib.sha256(contenu).hexdigest()


stockage = StockageObjet()
