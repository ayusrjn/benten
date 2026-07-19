from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Benten Audio Evaluation Framework"
    API_V1_STR: str = "/api/v1"
    
    # PostgreSQL Configuration
    POSTGRES_USER: str = "benten_admin"
    POSTGRES_PASSWORD: str = "admin_secure_pwd"
    POSTGRES_DB: str = "benten"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    
    # RabbitMQ Configuration
    RABBITMQ_DEFAULT_USER: str = "benten_mq"
    RABBITMQ_DEFAULT_PASS: str = "mq_secure_pwd"
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    
    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Security Configuration
    SECRET_KEY: str = "super-secret-key-for-benten-development-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_DEFAULT_USER}:{self.RABBITMQ_DEFAULT_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
