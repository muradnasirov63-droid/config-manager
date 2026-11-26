import json
from abc import ABC, abstractmethod
from typing import Any
import yaml
from jsonschema import Draft7Validator
from app.schemas import ValidationReport

SCHEMAS: dict[str, dict[str, Any]] = {
    "database-v1": {
        "type": "object",
        "required": ["db"],
        "properties": {
            "db": {
                "type": "object",
                "required": ["host", "port"],
                "properties": {
                    "host": {"type": "string", "minLength": 1},
                    "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                },
            }
        },
    },
    "service-v1": {
        "type": "object",
        "required": ["service"],
        "properties": {
            "service": {
                "type": "object",
                "required": ["name", "replicas"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "replicas": {"type": "integer", "minimum": 1, "maximum": 100},
                },
            }
        },
    },
}


class ConfigParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> Any:
        ...


class YamlParser(ConfigParser):
    def parse(self, content: str) -> Any:
        return yaml.safe_load(content)


class JsonParser(ConfigParser):
    def parse(self, content: str) -> Any:
        return json.loads(content)


PARSERS: dict[str, ConfigParser] = {
    "yaml": YamlParser(),
    "json": JsonParser(),
}


class ConfigValidator:
    def validate(self, content: str, fmt: str = "yaml", schema_ref: str | None = None) -> ValidationReport:
        parser = PARSERS.get(fmt)
        if parser is None:
            return ValidationReport(valid=False, errors=[f"Unsupported format: {fmt}"])
        try:
            parsed = parser.parse(content)
        except Exception as exc:
            return ValidationReport(valid=False, errors=[f"Parse error ({fmt}): {exc}"])

        if not isinstance(parsed, dict):
            return ValidationReport(valid=False, errors=["Root of configuration must be a mapping/object"])

        if schema_ref:
            schema = SCHEMAS.get(schema_ref)
            if schema is None:
                return ValidationReport(valid=False, errors=[f"Unknown schema: {schema_ref}"])
            validator = Draft7Validator(schema)
            errs = []
            for err in sorted(validator.iter_errors(parsed), key=lambda e: list(e.path)):
                path = "/".join(str(p) for p in err.path)
                errs.append(f"{path}: {err.message}" if path else err.message)
            if errs:
                return ValidationReport(valid=False, errors=errs)

        return ValidationReport(valid=True, errors=[])
