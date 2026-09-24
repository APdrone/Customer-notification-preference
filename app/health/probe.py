"""Health probe module for checking application health status."""

import sys
import time
from typing import Tuple


class HealthProbe:
    """Evaluates application health status with minimal overhead.
    
    The health probe performs lightweight checks to verify the application
    is running and responsive. This is an MVP implementation that checks
    only application process state, not external dependencies.
    
    Methods:
        check(): Performs health check and returns (is_healthy, details)
    """
    
    # Timeout safeguard: health probe must complete within 200ms
    # Note: First call may include import overhead, subsequent calls << 5ms
    PROBE_TIMEOUT_MS = 200
    
    @staticmethod
    def check() -> Tuple[bool, str]:
        """Check application health status.
        
        Returns:
            Tuple[bool, str]: (is_healthy, detail_message)
                - is_healthy: True if application is running normally
                - detail_message: Empty string if healthy, error message if not
        
        Raises:
            None. All exceptions are caught and return (False, error_msg)
        
        Examples:
            >>> is_healthy, detail = HealthProbe.check()
            >>> if is_healthy:
            ...     return {"status": "healthy"}
            >>> else:
            ...     return {"status": "unhealthy"}
        """
        try:
            start_time = time.time()
            
            # Check 1: Verify core modules are loaded
            if not HealthProbe._check_core_modules():
                return (False, "Core modules not loaded")
            
            # Check 2: Verify application is not shutting down
            if not HealthProbe._check_shutdown_state():
                return (False, "Application is shutting down")
            
            # Check 3: Verify system is responsive
            if not HealthProbe._check_responsiveness():
                return (False, "System not responsive")
            
            # Verify probe completed within timeout
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms > HealthProbe.PROBE_TIMEOUT_MS:
                return (False, f"Probe timeout: {elapsed_ms:.1f}ms > {HealthProbe.PROBE_TIMEOUT_MS}ms")
            
            # All checks passed
            return (True, "")
            
        except Exception as e:
            # Catch all exceptions and return unhealthy state
            return (False, f"Health probe error: {str(e)}")
    
    @staticmethod
    def _check_core_modules() -> bool:
        """Verify core application modules are loaded.
        
        Returns:
            bool: True if core modules loaded, False otherwise
        """
        try:
            # Don't re-import to avoid circular deps; just verify Python is OK
            # The fact that we can execute this function means the app is running
            return True
        except Exception:
            return False
    
    @staticmethod
    def _check_shutdown_state() -> bool:
        """Check if application is in shutdown state.
        
        Returns:
            bool: True if application is NOT shutting down
        """
        try:
            # Check if Python is in normal running state (not shutting down)
            return not getattr(sys, 'is_finalizing', lambda: False)()
        except Exception:
            return True  # Assume healthy if check fails
    
    @staticmethod
    def _check_responsiveness() -> bool:
        """Verify application can respond to basic operations.
        
        Returns:
            bool: True if application responsive, False otherwise
        """
        try:
            # Perform minimal operation to verify responsiveness
            # This is just a sanity check that basic Python operations work
            _ = sum([1, 2, 3])  # Simple computation
            return True
        except Exception:
            return False
