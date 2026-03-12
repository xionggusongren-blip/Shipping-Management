from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # IBM i 接続設定（機密情報は.envで管理）
    IBMI_HOST: str = "192.168.3.230"
    IBMI_USER: str = ""
    IBMI_PASSWORD: str = ""
    IBMI_LIBRARY: str = "TREED"
    IBMI_TABLE: str = "RJU1"
    JT400_JAR_PATH: str = "/opt/jt400.jar"

    # アプリ設定
    SQLITE_DB_PATH: str = "shipping.db"
    SECRET_KEY: str = "change-me-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
