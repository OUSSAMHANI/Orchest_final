"""
Retry Handler
Manages retry logic for failed agent steps with exponential backoff.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple, Callable

# =========================
# LOGGING SETUP
# =========================

logger = logging.getLogger(__name__)


# =========================
# RETRY CONFIGURATION
# =========================

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 60.0   # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0


# =========================
# RETRY HANDLER
# =========================

class RetryHandler:
    """
    Handles retry logic for failed agent executions.
    Supports exponential backoff and configurable retry limits.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize retry handler with configuration.
        
        Args:
            config: Optional configuration dictionary with:
                - max_retries: Maximum retry attempts per step
                - base_delay: Initial delay in seconds
                - max_delay: Maximum delay cap in seconds
                - backoff_multiplier: Exponential backoff factor
                - retryable_errors: List of error messages that should trigger retry
        """
        self.max_retries = config.get("max_retries", DEFAULT_MAX_RETRIES) if config else DEFAULT_MAX_RETRIES
        self.base_delay = config.get("base_delay", DEFAULT_BASE_DELAY) if config else DEFAULT_BASE_DELAY
        self.max_delay = config.get("max_delay", DEFAULT_MAX_DELAY) if config else DEFAULT_MAX_DELAY
        self.backoff_multiplier = config.get("backoff_multiplier", DEFAULT_BACKOFF_MULTIPLIER) if config else DEFAULT_BACKOFF_MULTIPLIER
        self.retryable_errors = config.get("retryable_errors", []) if config else []
    
    def should_retry(
        self,
        step_id: str,
        current_retry_count: int,
        error: str,
    ) -> bool:
        """
        Determine if a step should be retried.
        
        Args:
            step_id: ID of the step
            current_retry_count: Number of retries already attempted
            error: Error message from the failed execution
        
        Returns:
            True if should retry, False otherwise
        """
        # Check max retries
        if current_retry_count >= self.max_retries:
            logger.info(f"Step '{step_id}' reached max retries ({self.max_retries})")
            return False
        
        # Check if error is retryable
        if self.retryable_errors:
            is_retryable = any(retryable in error.lower() for retryable in self.retryable_errors)
            if not is_retryable:
                logger.info(f"Step '{step_id}' error is not retryable: {error[:100]}")
                return False
        
        logger.info(f"Step '{step_id}' will be retried (attempt {current_retry_count + 1}/{self.max_retries})")
        return True
    
    def get_delay(self, retry_count: int) -> float:
        """
        Calculate delay for a retry attempt using exponential backoff.
        
        Args:
            retry_count: Current retry attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.backoff_multiplier ** retry_count)
        return min(delay, self.max_delay)
    
    def execute_with_retry(
        self,
        step_id: str,
        func: Callable[[], Dict[str, Any]],
        get_current_retry_count: Callable[[str], int],
        increment_retry: Callable[[str], int],
        on_retry: Optional[Callable[[str, int, float], None]] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Execute a function with automatic retry logic.
        
        Args:
            step_id: Step ID for logging
            func: Function to execute (returns result dict)
            get_current_retry_count: Function to get current retry count for step
            increment_retry: Function to increment retry count for step
            on_retry: Optional callback called before each retry (step_id, attempt, delay)
        
        Returns:
            Tuple of (result, total_attempts)
        
        Raises:
            Exception: Last exception if all retries fail
        """
        attempt = 0
        last_error = None
        
        while True:
            try:
                result = func()
                
                # Check if result indicates failure
                if result.get("status") == "failed":
                    error_msg = result.get("error", "Unknown error")
                    raise Exception(error_msg)
                
                logger.info(f"Step '{step_id}' succeeded on attempt {attempt + 1}")
                return result, attempt + 1
                
            except Exception as e:
                last_error = e
                current_retry = get_current_retry_count(step_id)
                
                if not self.should_retry(step_id, current_retry, str(e)):
                    logger.error(f"Step '{step_id}' failed permanently after {attempt + 1} attempts")
                    raise
                
                # Increment retry count
                increment_retry(step_id)
                
                # Calculate and wait for delay
                delay = self.get_delay(attempt)
                
                if on_retry:
                    on_retry(step_id, attempt + 1, delay)
                
                logger.warning(f"Step '{step_id}' failed (attempt {attempt + 1}), retrying in {delay:.2f}s: {e}")
                time.sleep(delay)
                
                attempt += 1
    
    def is_critical_failure(
        self,
        step_id: str,
        error: str,
        retry_count: int,
        is_step_critical: bool,
    ) -> bool:
        """
        Determine if a failure should stop the entire workflow.
        
        Args:
            step_id: ID of the step
            error: Error message
            retry_count: Current retry count
            is_step_critical: Whether the step is marked critical in plan
        
        Returns:
            True if workflow should stop, False if can continue
        """
        # Critical step with no retries left -> stop
        if is_step_critical and retry_count >= self.max_retries:
            logger.error(f"Critical step '{step_id}' failed with no retries left. Stopping workflow.")
            return True
        
        # Non-critical step -> continue regardless
        if not is_step_critical:
            logger.info(f"Non-critical step '{step_id}' failed. Continuing workflow.")
            return False
        
        # Critical step but still has retries -> don't stop yet
        return False


# =========================
# SINGLETON INSTANCE
# =========================

_default_handler: Optional[RetryHandler] = None


def get_retry_handler(config: Optional[Dict[str, Any]] = None) -> RetryHandler:
    """
    Get singleton retry handler instance.
    """
    global _default_handler
    if _default_handler is None or config is not None:
        _default_handler = RetryHandler(config)
    return _default_handler


# =========================
# CONVENIENCE FUNCTIONS
# =========================

def should_retry_step(
    step_id: str,
    current_retry_count: int,
    error: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retryable_errors: Optional[list] = None,
) -> bool:
    """
    Quick helper to check if a step should be retried.
    """
    handler = RetryHandler({
        "max_retries": max_retries,
        "retryable_errors": retryable_errors or [],
    })
    return handler.should_retry(step_id, current_retry_count, error)


def calculate_retry_delay(
    retry_count: int,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
) -> float:
    """
    Calculate exponential backoff delay.
    """
    delay = base_delay * (DEFAULT_BACKOFF_MULTIPLIER ** retry_count)
    return min(delay, max_delay)