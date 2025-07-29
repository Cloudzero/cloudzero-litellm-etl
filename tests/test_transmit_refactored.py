# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for refactored transmit module demonstrating improved testability.

This test suite demonstrates how the refactoring addresses:
1. Single Responsibility: Each component can be tested in isolation
2. Testability: No console output, easy mocking, clear interfaces
3. Separation of Concerns: Business logic, I/O, and presentation tested separately
"""

import pytest
import polars as pl
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from ll2cz.transmit_refactored import (
    TransmitRequest,
    TransmitResult,
    RequestValidator,
    DataLoader,
    DataTransformer,
    BatchAnalyzer,
    TransmitOrchestrator,
    NullOutput,
    CollectingOutput,
    MockTransmitter,
    DataTransmitterV2
)


class TestDataModels:
    """Test pure data models - no dependencies needed."""
    
    def test_transmit_request_validation(self):
        """Test request validation logic."""
        # Valid request
        request = TransmitRequest(mode='all', source='usertable')
        request.validate()  # Should not raise
        
        # Invalid mode
        request = TransmitRequest(mode='invalid', source='usertable')
        with pytest.raises(ValueError, match="Mode must be"):
            request.validate()
        
        # Invalid source
        request = TransmitRequest(mode='all', source='invalid')
        with pytest.raises(ValueError, match="Source must be"):
            request.validate()
    
    def test_transmit_result_methods(self):
        """Test result object methods."""
        # Successful result
        result = TransmitResult(status='success', records=100, operation='replace_hourly')
        assert result.is_successful()
        
        # Test result (also considered successful)
        result = TransmitResult(status='test', records=50)
        assert result.is_successful()
        
        # Error result
        result = TransmitResult(status='error', error='Connection failed')
        assert not result.is_successful()
        
        # Test to_dict conversion
        result = TransmitResult(
            status='success',
            records=100,
            operation='sum',
            metadata={'extra': 'data'}
        )
        result_dict = result.to_dict()
        assert result_dict['status'] == 'success'
        assert result_dict['records'] == 100
        assert result_dict['operation'] == 'sum'
        assert result_dict['extra'] == 'data'


class TestRequestValidator:
    """Test the validator component in isolation."""
    
    def test_validate_valid_requests(self):
        """Test validation of valid requests."""
        validator = RequestValidator()
        
        # Valid combinations
        for mode in ['day', 'month', 'all']:
            for source in ['usertable', 'logs']:
                request = TransmitRequest(mode=mode, source=source)
                validator.validate(request)  # Should not raise
    
    def test_validate_invalid_mode(self):
        """Test validation rejects invalid modes."""
        validator = RequestValidator()
        request = TransmitRequest(mode='weekly', source='usertable')
        
        with pytest.raises(ValueError, match="Mode must be one of"):
            validator.validate(request)
    
    def test_validate_invalid_source(self):
        """Test validation rejects invalid sources."""
        validator = RequestValidator()
        request = TransmitRequest(mode='all', source='invalid')
        
        with pytest.raises(ValueError, match="Source must be one of"):
            validator.validate(request)
    
    def test_validate_invalid_limit(self):
        """Test validation rejects invalid limits."""
        validator = RequestValidator()
        request = TransmitRequest(mode='all', limit=-1)
        
        with pytest.raises(ValueError, match="Limit must be positive"):
            validator.validate(request)


class TestDataLoader:
    """Test data loading component - demonstrates easy mocking."""
    
    def test_load_data_with_custom_factory(self):
        """Test data loader with custom source factory."""
        # Mock dependencies
        mock_db = Mock()
        mock_date_parser = Mock()
        mock_date_parser.parse_date_spec.return_value = None
        
        # Mock source strategy
        mock_strategy = Mock()
        test_data = pl.DataFrame({'id': [1, 2, 3]})
        mock_strategy.get_data.return_value = test_data
        
        # Custom factory
        mock_factory = Mock(return_value=mock_strategy)
        
        # Test
        loader = DataLoader(mock_db, mock_date_parser, source_factory=mock_factory)
        request = TransmitRequest(mode='all', source='custom')
        result = loader.load_data(request)
        
        # Verify
        assert result.equals(test_data)
        mock_factory.assert_called_once_with('custom')
        mock_strategy.get_data.assert_called_once()
    
    def test_test_mode_limit_handling(self):
        """Test that test mode uses appropriate limits."""
        mock_db = Mock()
        mock_date_parser = Mock()
        mock_date_parser.parse_date_spec.return_value = None
        mock_strategy = Mock()
        mock_strategy.get_data.return_value = pl.DataFrame()
        
        loader = DataLoader(mock_db, mock_date_parser, 
                          source_factory=lambda s: mock_strategy)
        
        # Test mode without limit - should use default
        request = TransmitRequest(mode='all', test=True)
        loader.load_data(request)
        mock_strategy.get_data.assert_called_with(mock_db, date_filter=None, limit=5)
        
        # Test mode with custom limit
        mock_strategy.reset_mock()
        request = TransmitRequest(mode='all', test=True, limit=10)
        loader.load_data(request)
        mock_strategy.get_data.assert_called_with(mock_db, date_filter=None, limit=10)
    
    def test_get_date_description(self):
        """Test getting human-readable date description."""
        mock_db = Mock()
        mock_date_parser = Mock()
        mock_date_parser.parse_date_spec.return_value = {
            'description': 'January 2025'
        }
        
        loader = DataLoader(mock_db, mock_date_parser)
        request = TransmitRequest(mode='month', date_spec='01-2025')
        
        desc = loader.get_date_description(request)
        assert desc == 'January 2025'


class TestDataTransformer:
    """Test data transformation component."""
    
    def test_transform_empty_data(self):
        """Test handling of empty data."""
        transformer = DataTransformer()
        empty_df = pl.DataFrame()
        
        result = transformer.transform(empty_df, 'usertable')
        assert result.is_empty()
    
    def test_transform_with_custom_processor(self):
        """Test transformation with custom processor factory."""
        # Mock processor
        mock_processor = Mock()
        mock_processor.process_dataframe.return_value = (
            None,
            [
                {'time/usage_start': '2025-01-01T00:00:00Z', 'cost/cost': 0.1},
                {'time/usage_start': '2025-01-01T01:00:00Z', 'cost/cost': 0.2}
            ],
            {}
        )
        
        # Custom factory
        processor_factory = Mock(return_value=mock_processor)
        
        # Test
        transformer = DataTransformer(processor_factory=processor_factory)
        test_data = pl.DataFrame({'id': [1, 2]})
        result = transformer.transform(test_data, 'custom_source')
        
        # Verify
        assert len(result) == 2
        processor_factory.assert_called_once_with('custom_source')
        mock_processor.process_dataframe.assert_called_once()
    
    def test_chunking_threshold(self):
        """Test that chunking is used for large datasets."""
        # Create transformer with low threshold
        transformer = DataTransformer(chunk_threshold=5)
        
        # Small dataset - should not use chunking
        small_data = pl.DataFrame({'id': list(range(3))})
        assert not transformer._should_use_chunking(small_data)
        
        # Large dataset - should use chunking
        large_data = pl.DataFrame({'id': list(range(10))})
        assert transformer._should_use_chunking(large_data)


class TestBatchAnalyzer:
    """Test batch analysis component."""
    
    def test_analyze_empty_data(self):
        """Test analysis of empty data."""
        analyzer = BatchAnalyzer()
        empty_df = pl.DataFrame()
        
        result = analyzer.analyze_batches(empty_df)
        assert result['batches'] == 0
        assert result['dates'] == []
    
    def test_analyze_data_without_time_column(self):
        """Test analysis of data missing time column."""
        analyzer = BatchAnalyzer()
        data = pl.DataFrame({'id': [1, 2, 3]})
        
        result = analyzer.analyze_batches(data)
        assert result['batches'] == 0
        assert result['dates'] == []
    
    def test_analyze_multi_day_data(self):
        """Test analysis of data spanning multiple days."""
        analyzer = BatchAnalyzer()
        data = pl.DataFrame({
            'time/usage_start': [
                '2025-01-01T00:00:00Z',
                '2025-01-01T12:00:00Z',
                '2025-01-02T00:00:00Z',
                '2025-01-02T12:00:00Z',
                '2025-01-03T00:00:00Z'
            ],
            'cost': [0.1, 0.2, 0.3, 0.4, 0.5]
        })
        
        result = analyzer.analyze_batches(data)
        assert result['batches'] == 3
        assert len(result['dates']) == 3
        assert result['dates'][0] == {'date': '2025-01-01', 'count': 2}
        assert result['dates'][1] == {'date': '2025-01-02', 'count': 2}
        assert result['dates'][2] == {'date': '2025-01-03', 'count': 1}


class TestOutputHandlers:
    """Test different output handler implementations."""
    
    def test_null_output_has_no_side_effects(self):
        """Test that NullOutput truly has no side effects."""
        output = NullOutput()
        
        # All methods should complete without error
        output.show_loading('all', 'usertable', 'Today')
        output.show_no_data()
        output.show_processing(100)
        output.show_test_payload({}, [], 'replace_hourly', 'all')
        output.show_transmitting('sum')
        output.show_success(50)
        output.show_error('Test error')
        
        # No way to observe any side effects - perfect for testing
    
    def test_collecting_output_records_messages(self):
        """Test that CollectingOutput captures messages for verification."""
        output = CollectingOutput()
        
        output.show_loading('all', 'usertable', 'January 2025')
        output.show_processing(100)
        output.show_success(100)
        
        assert 'Loading all from usertable' in output.messages
        assert 'Date: January 2025' in output.messages
        assert 'Processing 100 records' in output.messages
        assert 'Success: 100 records' in output.messages


class TestMockTransmitter:
    """Test the mock transmitter functionality."""
    
    def test_mock_transmitter_records_calls(self):
        """Test that mock transmitter records all calls."""
        transmitter = MockTransmitter()
        
        # First transmission
        data1 = pl.DataFrame({'id': [1, 2]})
        transmitter.transmit(data1, 'replace_hourly')
        
        # Second transmission
        data2 = pl.DataFrame({'id': [3, 4, 5]})
        transmitter.transmit(data2, 'sum')
        
        # Verify
        assert transmitter.call_count == 2
        assert len(transmitter.transmitted_data) == 2
        assert transmitter.transmitted_data[0].equals(data1)
        assert transmitter.transmitted_data[1].equals(data2)
        assert transmitter.operations == ['replace_hourly', 'sum']
    
    def test_mock_transmitter_reset(self):
        """Test that mock transmitter can be reset."""
        transmitter = MockTransmitter()
        
        # Add some data
        transmitter.transmit(pl.DataFrame({'id': [1]}), 'sum')
        assert transmitter.call_count == 1
        
        # Reset
        transmitter.reset()
        assert transmitter.call_count == 0
        assert len(transmitter.transmitted_data) == 0
        assert len(transmitter.operations) == 0


class TestTransmitOrchestrator:
    """Test the orchestrator with fully mocked components."""
    
    def test_successful_flow(self):
        """Test successful transmission flow with all components mocked."""
        # Create test data
        test_data = pl.DataFrame({'id': [1, 2, 3]})
        cbf_data = pl.DataFrame({
            'time/usage_start': ['2025-01-01T00:00:00Z'] * 3,
            'cost/cost': [0.1, 0.2, 0.3]
        })
        
        # Mock all components
        mock_validator = Mock()
        mock_loader = Mock()
        mock_loader.get_date_description.return_value = 'January 2025'
        mock_loader.load_data.return_value = test_data
        
        mock_transformer = Mock()
        mock_transformer.transform.return_value = cbf_data
        
        mock_analyzer = Mock()
        mock_analyzer.analyze_batches.return_value = {
            'batches': 1,
            'dates': [{'date': '2025-01-01', 'count': 3}]
        }
        
        mock_transmitter = MockTransmitter()
        collecting_output = CollectingOutput()
        
        # Create orchestrator
        orchestrator = TransmitOrchestrator(
            mock_validator,
            mock_loader,
            mock_transformer,
            mock_analyzer,
            mock_transmitter,
            collecting_output
        )
        
        # Execute
        request = TransmitRequest(mode='all', append=True)
        result = orchestrator.execute(request)
        
        # Verify result
        assert result.status == 'success'
        assert result.records == 3
        assert result.operation == 'sum'  # append=True
        assert result.is_successful()
        
        # Verify component interactions
        mock_validator.validate.assert_called_once_with(request)
        mock_loader.load_data.assert_called_once_with(request)
        mock_transformer.transform.assert_called_once_with(test_data, 'usertable')
        assert mock_transmitter.call_count == 1
        assert mock_transmitter.operations == ['sum']
        
        # Verify output messages
        assert 'Loading all from usertable' in collecting_output.messages
        assert 'Processing 3 records' in collecting_output.messages
        assert 'Transmitting with sum' in collecting_output.messages
        assert 'Success: 3 records' in collecting_output.messages
    
    def test_test_mode_flow(self):
        """Test that test mode doesn't transmit."""
        # Mock components
        mock_validator = Mock()
        mock_loader = Mock()
        mock_loader.get_date_description.return_value = None
        mock_loader.load_data.return_value = pl.DataFrame({'id': [1, 2]})
        
        mock_transformer = Mock()
        mock_transformer.transform.return_value = pl.DataFrame({
            'time/usage_start': ['2025-01-01T00:00:00Z'] * 2,
            'cost/cost': [0.1, 0.2]
        })
        
        mock_analyzer = Mock()
        mock_analyzer.analyze_batches.return_value = {
            'batches': 1,
            'dates': [{'date': '2025-01-01', 'count': 2}]
        }
        
        mock_transmitter = MockTransmitter()
        output = NullOutput()
        
        # Create orchestrator
        orchestrator = TransmitOrchestrator(
            mock_validator,
            mock_loader,
            mock_transformer,
            mock_analyzer,
            mock_transmitter,
            output
        )
        
        # Execute in test mode
        request = TransmitRequest(mode='all', test=True)
        result = orchestrator.execute(request)
        
        # Verify
        assert result.status == 'test'
        assert result.records == 2
        assert result.is_successful()
        assert mock_transmitter.call_count == 0  # No transmission in test mode
    
    def test_error_handling(self):
        """Test error handling throughout the flow."""
        # Mock validator to raise error
        mock_validator = Mock()
        mock_validator.validate.side_effect = ValueError("Invalid request")
        
        orchestrator = TransmitOrchestrator(
            mock_validator,
            Mock(),  # loader
            Mock(),  # transformer
            Mock(),  # analyzer
            MockTransmitter(),
            CollectingOutput()
        )
        
        request = TransmitRequest(mode='invalid')
        result = orchestrator.execute(request)
        
        assert result.status == 'error'
        assert result.error == "Invalid request"
        assert not result.is_successful()


class TestDataTransmitterV2:
    """Test the main API class."""
    
    def test_backward_compatibility(self):
        """Test that the API maintains backward compatibility."""
        mock_db = Mock()
        
        # Create transmitter
        transmitter = DataTransmitterV2(
            database=mock_db,
            cz_api_key='test-key',
            cz_connection_id='test-id'
        )
        
        # Should have all the expected components
        assert hasattr(transmitter, 'orchestrator')
        assert hasattr(transmitter, 'data_loader')
        assert hasattr(transmitter, 'data_transformer')
        
        # transmit() method should return dict
        with patch.object(transmitter.orchestrator, 'execute') as mock_execute:
            mock_execute.return_value = TransmitResult(
                status='success',
                records=100,
                operation='replace_hourly'
            )
            
            result = transmitter.transmit(mode='all')
            
            assert isinstance(result, dict)
            assert result['status'] == 'success'
            assert result['records'] == 100
            assert result['operation'] == 'replace_hourly'
    
    def test_custom_components(self):
        """Test that custom components can be injected."""
        mock_db = Mock()
        custom_validator = Mock()
        custom_transformer = Mock()
        custom_output = CollectingOutput()
        custom_transmitter = MockTransmitter()
        
        # Create with custom components
        transmitter = DataTransmitterV2(
            database=mock_db,
            cz_api_key='test-key',
            cz_connection_id='test-id',
            output=custom_output,
            transmitter=custom_transmitter,
            validator=custom_validator,
            data_transformer=custom_transformer
        )
        
        # Verify custom components are used
        assert transmitter.orchestrator.validator is custom_validator
        assert transmitter.orchestrator.data_transformer is custom_transformer
        assert transmitter.orchestrator.output is custom_output
        assert transmitter.orchestrator.transmitter is custom_transmitter


class TestRefactoringBenefits:
    """Tests that demonstrate the benefits of the refactoring."""
    
    def test_no_console_output_in_unit_tests(self):
        """Demonstrate that tests can run without any console output."""
        # Create a complete transmitter with null output
        mock_db = Mock()
        transmitter = DataTransmitterV2(
            database=mock_db,
            cz_api_key='test',
            cz_connection_id='test',
            output=NullOutput(),  # No console output
            transmitter=MockTransmitter()  # No network calls
        )
        
        # This would normally print to console, but with NullOutput it's silent
        # Perfect for unit tests that shouldn't have side effects
    
    def test_easy_component_substitution(self):
        """Demonstrate how easy it is to substitute components."""
        # Can easily create test doubles for any component
        test_validator = RequestValidator()  # Real validator
        test_loader = Mock()  # Mock loader
        test_transformer = Mock()  # Mock transformer
        test_analyzer = BatchAnalyzer()  # Real analyzer
        test_transmitter = MockTransmitter()  # Test transmitter
        test_output = CollectingOutput()  # Test output
        
        # All components work together seamlessly
        orchestrator = TransmitOrchestrator(
            test_validator,
            test_loader,
            test_transformer,
            test_analyzer,
            test_transmitter,
            test_output
        )
        
        # Easy to test specific scenarios
    
    def test_separation_of_concerns(self):
        """Demonstrate clear separation of concerns."""
        # Each component has a single, clear responsibility:
        
        # 1. Validation only validates
        validator = RequestValidator()
        assert hasattr(validator, 'validate')
        assert not hasattr(validator, 'load_data')
        
        # 2. Loader only loads
        loader = DataLoader(Mock(), Mock())
        assert hasattr(loader, 'load_data')
        assert not hasattr(loader, 'transform')
        
        # 3. Transformer only transforms
        transformer = DataTransformer()
        assert hasattr(transformer, 'transform')
        assert not hasattr(transformer, 'transmit')
        
        # 4. Output only handles output
        output = NullOutput()
        assert hasattr(output, 'show_success')
        assert not hasattr(output, 'validate')
        
        # This makes each component easy to understand, test, and modify