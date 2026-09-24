"""Unit tests for the health probe module."""

import pytest
import time
from app.health import HealthProbe


class TestHealthProbe:
    """Test suite for HealthProbe health checking functionality."""
    
    def test_probe_healthy(self):
        """Test that probe returns healthy state when app running normally."""
        is_healthy, detail = HealthProbe.check()
        assert is_healthy is True
        assert detail == ""
    
    def test_probe_returns_tuple(self):
        """Test that probe returns correct tuple format."""
        result = HealthProbe.check()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
    
    def test_probe_core_modules_check(self):
        """Test that probe verifies core modules are loaded."""
        # This test verifies _check_core_modules works
        assert HealthProbe._check_core_modules() is True
    
    def test_probe_shutdown_state_check(self):
        """Test that probe checks shutdown state."""
        # This test verifies _check_shutdown_state works
        assert HealthProbe._check_shutdown_state() is True
    
    def test_probe_responsiveness_check(self):
        """Test that probe verifies system responsiveness."""
        # This test verifies _check_responsiveness works
        assert HealthProbe._check_responsiveness() is True
    
    def test_probe_response_time_under_timeout(self):
        """Test that probe completes within 200ms timeout."""
        start_time = time.time()
        is_healthy, detail = HealthProbe.check()
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Probe should complete in reasonable time (well under 200ms)
        assert elapsed_ms < 200
        assert is_healthy is True
    
    def test_probe_consistency(self):
        """Test that probe returns consistent results on repeated calls."""
        results = [HealthProbe.check() for _ in range(5)]
        
        # All results should be identical
        for result in results:
            assert result[0] is True  # healthy
            assert result[1] == ""     # no detail
    
    def test_probe_exception_handling(self):
        """Test that probe handles exceptions gracefully."""
        # Simulate an exception by patching _check_core_modules
        original_method = HealthProbe._check_core_modules
        
        try:
            # Make _check_core_modules raise an exception
            HealthProbe._check_core_modules = staticmethod(
                lambda: (_ for _ in ()).throw(RuntimeError("test error"))
            )
            
            # Probe should catch exception and return unhealthy
            is_healthy, detail = HealthProbe.check()
            assert is_healthy is False
            assert "Health probe error" in detail
        finally:
            # Restore original method
            HealthProbe._check_core_modules = original_method
    
    def test_probe_timeout_constant(self):
        """Test that probe timeout is defined and reasonable."""
        assert hasattr(HealthProbe, 'PROBE_TIMEOUT_MS')
        assert HealthProbe.PROBE_TIMEOUT_MS == 200
        assert HealthProbe.PROBE_TIMEOUT_MS > 0


class TestHealthProbeErrorPaths:
    """Test error paths and edge cases in HealthProbe."""
    
    def test_probe_module_check_exception(self):
        """Test that module check handles exceptions."""
        original = HealthProbe._check_core_modules
        
        try:
            # Simulate exception in module check
            HealthProbe._check_core_modules = staticmethod(
                lambda: (_ for _ in ()).throw(ValueError("test"))
            )
            is_healthy, detail = HealthProbe.check()
            # Should return unhealthy due to probe error
            assert is_healthy is False
            assert "Health probe error" in detail
        finally:
            HealthProbe._check_core_modules = original
    
    def test_probe_shutdown_check_exception(self):
        """Test that shutdown check handles exceptions."""
        original = HealthProbe._check_shutdown_state
        
        try:
            HealthProbe._check_shutdown_state = staticmethod(
                lambda: (_ for _ in ()).throw(RuntimeError("test"))
            )
            # Even with shutdown check failure, should handle gracefully
            # (but will fail on the check itself)
            is_healthy, detail = HealthProbe.check()
            assert is_healthy is False
        finally:
            HealthProbe._check_shutdown_state = original
    
    def test_probe_responsiveness_check_exception(self):
        """Test that responsiveness check handles exceptions."""
        original = HealthProbe._check_responsiveness
        
        try:
            HealthProbe._check_responsiveness = staticmethod(
                lambda: (_ for _ in ()).throw(Exception("test"))
            )
            is_healthy, detail = HealthProbe.check()
            assert is_healthy is False
        finally:
            HealthProbe._check_responsiveness = original
    
    def test_probe_module_check_returns_false(self):
        """Test behavior when module check fails."""
        original = HealthProbe._check_core_modules
        
        try:
            HealthProbe._check_core_modules = staticmethod(lambda: False)
            is_healthy, detail = HealthProbe.check()
            assert is_healthy is False
            assert "Core modules not loaded" in detail
        finally:
            HealthProbe._check_core_modules = original
    
    def test_probe_shutdown_check_returns_false(self):
        """Test behavior when shutdown check indicates shutdown."""
        original = HealthProbe._check_shutdown_state
        
        try:
            HealthProbe._check_shutdown_state = staticmethod(lambda: False)
            is_healthy, detail = HealthProbe.check()
            assert is_healthy is False
            assert "shutting down" in detail
        finally:
            HealthProbe._check_shutdown_state = original
    
    def test_probe_responsiveness_check_returns_false(self):
        """Test behavior when responsiveness check fails."""
        original = HealthProbe._check_responsiveness
        
        try:
            HealthProbe._check_responsiveness = staticmethod(lambda: False)
            is_healthy, detail = HealthProbe.check()
            assert is_healthy is False
            assert "responsive" in detail
        finally:
            HealthProbe._check_responsiveness = original
    
    def test_probe_slow_execution_timeout(self):
        """Test that probe times out if execution is too slow."""
        import time as time_module
        original_time = time_module.time
        
        try:
            # Mock time to simulate slow execution
            call_count = [0]
            
            def slow_time():
                call_count[0] += 1
                if call_count[0] == 1:  # First call
                    return original_time()
                elif call_count[0] == 2:  # After checks start
                    return original_time() + 0.3  # Add 300ms to simulate slow execution
                else:  # Final call
                    return original_time() + 0.4
            
            time_module.time = slow_time
            
            is_healthy, detail = HealthProbe.check()
            assert is_healthy is False
            assert "timeout" in detail.lower()
        finally:
            time_module.time = original_time


class TestHealthProbeEdgeCases:
    """Test edge cases for HealthProbe."""
    
    def test_probe_called_rapidly(self):
        """Test that probe handles rapid successive calls."""
        results = []
        for _ in range(10):
            is_healthy, detail = HealthProbe.check()
            results.append((is_healthy, detail))
        
        # All results should be healthy
        for is_healthy, detail in results:
            assert is_healthy is True
            assert detail == ""
    
    def test_probe_performance_characteristics(self):
        """Test that probe meets performance characteristics."""
        # Measure average response time over multiple calls
        times = []
        for _ in range(10):
            start = time.time()
            HealthProbe.check()
            times.append((time.time() - start) * 1000)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Average should be very fast (excluding first cold-start call)
        assert avg_time < 100  # Average < 100ms
        # Max should be under timeout
        assert max_time < 200  # Max < 200ms
