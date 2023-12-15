from sqlalchemy import Engine as SQAEngine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from test_sdd.cases import Cases
from test_sdd.conftest import PYTEST_CONTEXT
from test_sdd.controllers import docker


@docker.WithServers(
    PYTEST_CONTEXT.config.servers,
    {
        "arg": (_args := ["first arg", "second arg", "third arg"]),
    },
)
class TestWithServers:
    def test_it_works(self, Engine: SQAEngine, arg: str, ormConnected: Cases):
        assert isinstance(Engine, SQAEngine)
        assert arg in _args

        metadata = ormConnected[0].metadata
        metadata.create_all(Engine)

        SessionMaker = sessionmaker(Engine)
        with SessionMaker() as session:
            result = session.execute(
                text(
                    """
                    SHOW TABLES;
                    """
                )
            )

        assert print(list(result.scalars()))
