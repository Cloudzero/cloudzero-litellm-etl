# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests to ensure all imports work correctly and prevent import errors."""

import importlib
import pkgutil

import pytest

import ll2cz


class TestImports:
    """Test that all modules can be imported without errors."""

    def test_all_modules_importable(self):
        """Test that all ll2cz modules can be imported."""
        # Get the package path
        package_path = ll2cz.__path__
        
        # List all modules in the package
        modules = []
        for importer, modname, ispkg in pkgutil.walk_packages(
            path=package_path,
            prefix='ll2cz.',
            onerror=lambda x: None
        ):
            if not ispkg:  # Only test modules, not packages
                modules.append(modname)
        
        # Test importing each module
        failed_imports = []
        for module_name in modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))
        
        # Assert no import failures
        if failed_imports:
            failure_messages = [f"{mod}: {err}" for mod, err in failed_imports]
            pytest.fail(f"Failed to import modules:\n" + "\n".join(failure_messages))

    def test_extract_model_name_import(self):
        """Test that extract_model_name is properly imported where needed."""
        # These modules should import extract_model_name from model_name_strategies
        modules_using_extract_model_name = [
            'll2cz.czrn',
            'll2cz.error_tracking',
            'll2cz.data_processor',
        ]
        
        for module_name in modules_using_extract_model_name:
            module = importlib.import_module(module_name)
            # Verify the function exists in the module's namespace
            assert hasattr(module, 'extract_model_name'), \
                f"{module_name} should have extract_model_name imported"

    def test_cli_entry_point(self):
        """Test that the CLI entry point can be imported."""
        from ll2cz.cli import main
        assert callable(main), "CLI main function should be callable"

    def test_critical_imports(self):
        """Test that critical modules and their imports work."""
        # Test critical import chains
        critical_imports = [
            ('ll2cz.cli', 'main'),
            ('ll2cz.transform', 'CBFTransformer'),
            ('ll2cz.transmit', 'DataTransmitter'),
            ('ll2cz.analysis', 'DataAnalyzer'),
            ('ll2cz.database', 'LiteLLMDatabase'),
            ('ll2cz.cached_database', 'CachedLiteLLMDatabase'),
            ('ll2cz.czrn', 'CZRNGenerator'),
            ('ll2cz.cbf_builder', 'CBFBuilder'),
            ('ll2cz.data_processor', 'DataProcessor'),
            ('ll2cz.transformations', 'generate_resource_id'),
            ('ll2cz.model_name_strategies', 'extract_model_name'),
        ]
        
        for module_name, attr_name in critical_imports:
            try:
                module = importlib.import_module(module_name)
                assert hasattr(module, attr_name), \
                    f"{module_name} should have {attr_name}"
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_no_circular_imports(self):
        """Test that there are no circular import issues."""
        # Import all modules in dependency order
        import_order = [
            'll2cz.model_name_strategies',
            'll2cz.transformations', 
            'll2cz.error_tracking',
            'll2cz.czrn',
            'll2cz.cbf_builder',
            'll2cz.data_processor',
            'll2cz.data_source_strategy',
            'll2cz.chunked_processor',
            'll2cz.cbf_transformer',
            'll2cz.transform',
            'll2cz.date_utils',
            'll2cz.database',
            'll2cz.cache',
            'll2cz.cached_database',
            'll2cz.output',
            'll2cz.transmit',
            'll2cz.analysis',
            'll2cz.config',
            'll2cz.decorators',
            'll2cz.cli',
        ]
        
        for module_name in import_order:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"Circular import detected in {module_name}: {e}")

    def test_type_annotations_imports(self):
        """Test that all type annotation imports are correct for Python 3.9+."""
        # These modules should import from typing
        modules_with_typing = [
            'll2cz.analysis',
            'll2cz.cache',
            'll2cz.cached_database',
            'll2cz.cbf_transformer',
            'll2cz.chunked_processor',
            'll2cz.czrn',
            'll2cz.data_processor',
            'll2cz.data_source_strategy',
            'll2cz.database',
            'll2cz.date_utils',
            'll2cz.decorators',
            'll2cz.error_tracking',
            'll2cz.output',
            'll2cz.transform',
            'll2cz.transmit',
        ]
        
        for module_name in modules_with_typing:
            module = importlib.import_module(module_name)
            # Check module source for proper imports
            if hasattr(module, '__file__') and module.__file__:
                with open(module.__file__, 'r') as f:
                    content = f.read()
                    # Should import from typing, not use built-in generics
                    if 'Dict[' in content or 'List[' in content or 'Optional[' in content:
                        assert 'from typing import' in content, \
                            f"{module_name} uses typing annotations but doesn't import from typing"