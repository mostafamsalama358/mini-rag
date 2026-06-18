from helpers.config import get_settings


async def get_db_client():
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    settings = get_settings()
    postgres_conn = (
        f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    )
    db_engine = create_async_engine(postgres_conn)
    db_client = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    return db_engine, db_client


async def get_setup_utils():
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from stores.llm.LLMProviderFactory import LLMProviderFactory
    from stores.llm.templates.template_parser import TemplateParser
    from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory

    settings = get_settings()

    postgres_conn = (
        f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    )

    db_engine = create_async_engine(postgres_conn)
    db_client = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(
        config=settings, db_client=db_client
    )

    generation_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEND
    )
    generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

    embedding_client = llm_provider_factory.create(
        provider=settings.EMBEDDING_BACKEND
    )
    embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )

    vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )
    await vectordb_client.connect()

    template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG,
    )

    return (
        db_engine,
        db_client,
        llm_provider_factory,
        vectordb_provider_factory,
        generation_client,
        embedding_client,
        vectordb_client,
        template_parser,
    )
