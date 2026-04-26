"""Repository for Advertisement operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime
from db import models
from typing import Optional, List


class AdRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, admin_id: int, text: str = None,
                     media_file_id: str = None, media_type: str = None,
                     buttons: dict = None, expires_at: datetime = None) -> models.Ad:
        ad = models.Ad(
            admin_id=admin_id,
            text=text,
            media_file_id=media_file_id,
            media_type=media_type,
            buttons=buttons,
            expires_at=expires_at,
        )
        self.session.add(ad)
        await self.session.flush()
        return ad

    async def get_by_id(self, ad_id: int) -> Optional[models.Ad]:
        stmt = select(models.Ad).where(models.Ad.id == ad_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active(self) -> List[models.Ad]:
        now = datetime.utcnow()
        stmt = select(models.Ad).where(
            models.Ad.is_active == True,
            (models.Ad.expires_at == None) | (models.Ad.expires_at > now)
        ).order_by(desc(models.Ad.created_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_all(self, limit: int = 50) -> List[models.Ad]:
        stmt = select(models.Ad).order_by(desc(models.Ad.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def toggle_active(self, ad_id: int) -> Optional[models.Ad]:
        ad = await self.get_by_id(ad_id)
        if ad:
            ad.is_active = not ad.is_active
            await self.session.flush()
        return ad

    async def increment_views(self, ad_id: int):
        ad = await self.get_by_id(ad_id)
        if ad:
            ad.views_count += 1
            await self.session.flush()

    async def increment_clicks(self, ad_id: int):
        ad = await self.get_by_id(ad_id)
        if ad:
            ad.clicks_count += 1
            await self.session.flush()

    async def delete(self, ad_id: int) -> bool:
        ad = await self.get_by_id(ad_id)
        if ad:
            await self.session.delete(ad)
            await self.session.flush()
            return True
        return False
