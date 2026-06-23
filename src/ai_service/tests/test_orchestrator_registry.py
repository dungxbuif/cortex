import unittest
from typing import Any

from ai_service.orchestrator.registry import DefaultToolRegistry, to_provider_format, validate_schema


class SchemaValidatorTest(unittest.TestCase):
    def test_validates_object_and_required_fields(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "amount": {"type": "integer"},
                "currency": {"type": "string"},
            },
            "required": ["amount", "currency"]
        }

        # Valid data
        errors = validate_schema(schema, {"amount": 100, "currency": "VND"})
        self.assertEqual(errors, [])

        # Missing required field
        errors = validate_schema(schema, {"amount": 100})
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required field 'currency'", errors[0])
        # Unknown property
        errors = validate_schema(schema, {"amount": 100, "currency": "VND", "extra": "bad"})
        self.assertEqual(len(errors), 1)
        self.assertIn("Unknown property 'extra'", errors[0])
        # Wrong type
        errors = validate_schema(schema, {"amount": "100", "currency": "VND"})
        self.assertEqual(len(errors), 1)
        self.assertIn("Expected integer at 'amount'", errors[0])

    def test_validates_nested_arrays(self) -> None:
        schema: dict[str, Any] = {
            "type": "array",
            "items": {"type": "string"}
        }

        # Valid data
        errors = validate_schema(schema, ["tag1", "tag2"])
        self.assertEqual(errors, [])

        # Invalid item type
        errors = validate_schema(schema, ["tag1", 123])
        self.assertEqual(len(errors), 1)
        self.assertIn("Expected string at '[1]'", errors[0])

    def test_validates_number_types(self) -> None:
        schema: dict[str, Any] = {"type": "number"}
        
        self.assertEqual(validate_schema(schema, 10), [])
        self.assertEqual(validate_schema(schema, 10.5), [])
        self.assertEqual(len(validate_schema(schema, True)), 1)
        self.assertEqual(len(validate_schema(schema, "10")), 1)


class ToolRegistryTest(unittest.TestCase):
    def test_default_tools_have_correct_policies(self) -> None:
        registry = DefaultToolRegistry()
        tools = registry.list_tools()
        
        self.assertGreater(len(tools), 0)

        finance_write = next(t for t in tools if t.name == "finance_create_transaction")
        self.assertEqual(finance_write.confirmation, "require_confirmation")
        self.assertIn("finance_write", finance_write.required_capabilities)

        homelab_read = next(t for t in tools if t.name == "homelab_search_knowledge")
        self.assertEqual(homelab_read.confirmation, "none")
        self.assertIn("homelab_read", homelab_read.required_capabilities)

    def test_list_tools_filtering(self) -> None:
        registry = DefaultToolRegistry()
        finance_tools = registry.list_tools(module="finance")
        self.assertTrue(all(t.module == "finance" for t in finance_tools))
        self.assertEqual(len(finance_tools), 2)
        
        write_tools = registry.list_tools(capability="finance_write")
        self.assertEqual(len(write_tools), 1)
        self.assertEqual(write_tools[0].name, "finance_create_transaction")

    def test_to_provider_format(self) -> None:
        registry = DefaultToolRegistry()
        tools = registry.list_tools()
        provider_fmt = to_provider_format(tools[0])

        self.assertIn("name", provider_fmt)
        self.assertIn("description", provider_fmt)
        self.assertIn("parameters", provider_fmt)
        self.assertEqual(provider_fmt["name"], tools[0].name)


if __name__ == "__main__":
    unittest.main()
