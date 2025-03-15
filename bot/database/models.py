from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, func, BigInteger, JSON

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    tg_id = Column(BigInteger, primary_key=True)
    username = Column(String, unique=True, nullable=False)

    orders = relationship("Order", back_populates="user")
    cart = relationship("Cart", back_populates="user", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    types = Column(JSON, nullable=False, default=[])
    photo_url = Column(String, nullable=True)




class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.tg_id"))
    total_price = Column(Float, nullable=False)  # Загальна ціна
    items = Column(JSON, nullable=False)  # JSON зі списком товарів
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=func.now())


    user = relationship("User", back_populates="orders")


class Cart(Base):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.tg_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    message_id = Column(Integer, nullable=True)

    user = relationship("User", back_populates="cart")
    product = relationship("Product")