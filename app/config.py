from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class UsuarioPermitido(BaseModel):
    telegram_id: int
    nombre: str
    telefono: str | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_token: str
    database_url: str

    llm_api_key: str
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    vision_model: str = "gpt-4o-mini"
    audio_model: str = "whisper-1"

    allowed_users: str = ""
    tz: str = "America/Argentina/Buenos_Aires"
    log_level: str = "INFO"

    @property
    def usuarios_permitidos(self) -> list[UsuarioPermitido]:
        usuarios = []
        for entrada in self.allowed_users.split(","):
            entrada = entrada.strip()
            if not entrada:
                continue
            partes = entrada.split(":")
            usuarios.append(
                UsuarioPermitido(
                    telegram_id=int(partes[0]),
                    nombre=partes[1] if len(partes) > 1 else "",
                    telefono=partes[2] if len(partes) > 2 and partes[2] else None,
                )
            )
        return usuarios


settings = Settings()
