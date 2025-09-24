from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, JSON, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .database import Base


class PropertyType(enum.Enum):
    HOUSE = "house"
    APARTMENT = "apartment"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    COMMERCIAL = "commercial"


class PropertyStatus(enum.Enum):
    AVAILABLE = "available"
    SOLD = "sold"
    PENDING = "pending"
    RENTED = "rented"
    OFF_MARKET = "off_market"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(255), unique=True, index=True)  # Google OAuth ID
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    picture = Column(String(500))  # プロフィール画像URL
    phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    properties = relationship("Property", back_populates="owner")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    saved_pins = relationship("SavedPin", back_populates="user", cascade="all, delete-orphan")
    user_settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    location = Column(String(500), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    area_sqft = Column(Float)
    property_type = Column(Enum(PropertyType), nullable=False)
    status = Column(Enum(PropertyStatus), default=PropertyStatus.AVAILABLE, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="properties")
    images = relationship("PropertyImage", back_populates="property")


class PropertyImage(Base):
    __tablename__ = "property_images"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    caption = Column(String(255))
    is_primary = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    property = relationship("Property", back_populates="images")


class Session(Base):
    """セッション管理テーブル（認証不要）"""
    __tablename__ = "sessions"

    id = Column(String(100), primary_key=True, index=True)  # UUID
    data = Column(Text)  # JSON形式のセッションデータ
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)

    # リレーション
    search_histories = relationship("SearchHistory", back_populates="session")
    commute_histories = relationship("CommuteHistory", back_populates="session")
    saved_properties = relationship("SavedProperty", back_populates="session")


class SearchHistory(Base):
    """検索履歴テーブル"""
    __tablename__ = "search_histories"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("sessions.id"), nullable=False)
    search_type = Column(String(50))  # property_search, commute_search
    search_params = Column(Text)  # JSON形式の検索条件
    results_count = Column(Integer)  # 結果件数
    created_at = Column(DateTime, default=datetime.utcnow)

    # リレーション
    session = relationship("Session", back_populates="search_histories")


class CommuteHistory(Base):
    """通勤時間計算履歴テーブル"""
    __tablename__ = "commute_histories"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("sessions.id"), nullable=False)
    from_address = Column(String(500), nullable=False)
    to_address = Column(String(500), nullable=False)
    from_lat = Column(Float)
    from_lon = Column(Float)
    to_lat = Column(Float)
    to_lon = Column(Float)
    commute_time = Column(Integer)  # 分
    fare = Column(Float)  # 運賃
    route_data = Column(Text)  # JSON形式の詳細経路情報
    created_at = Column(DateTime, default=datetime.utcnow)

    # リレーション
    session = relationship("Session", back_populates="commute_histories")


class SavedProperty(Base):
    """保存した物件テーブル"""
    __tablename__ = "saved_properties"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("sessions.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    notes = Column(Text)  # メモ
    commute_data = Column(Text)  # JSON形式の通勤時間データ
    created_at = Column(DateTime, default=datetime.utcnow)

    # リレーション
    session = relationship("Session", back_populates="saved_properties")
    property = relationship("Property")


class RefreshToken(Base):
    """リフレッシュトークン管理テーブル"""
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="refresh_tokens")


class UserSettings(Base):
    """ユーザー設定テーブル"""
    __tablename__ = "user_settings"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    settings = Column(JSON, default={})  # JSON形式の設定データ
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="user_settings")


class SavedPin(Base):
    """保存されたピン（駅）データテーブル"""
    __tablename__ = "saved_pins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    station_name = Column(String(255), nullable=False)
    line_name = Column(String(255))
    coord_lat = Column(Float, nullable=False)
    coord_lon = Column(Float, nullable=False)

    # 駅周辺情報
    nearby_places = Column(JSON)  # Google Maps/Search APIから取得した周辺施設情報

    # NAVITIMEから取得した情報
    reachable_stations = Column(JSON)  # 到達可能な駅のリスト
    average_rent = Column(Float)  # 平均家賃

    # 会話コンテキストから得られた情報
    conversation_context = Column(Text)  # 会話の内容や文脈
    notes = Column(Text)  # ユーザーのメモ
    tags = Column(JSON)  # タグ（例：["子育て向き", "商業施設充実"]）

    # メタデータ
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="saved_pins")

    __table_args__ = (
        UniqueConstraint('user_id', 'station_name', 'line_name', name='_user_station_line_uc'),
    )