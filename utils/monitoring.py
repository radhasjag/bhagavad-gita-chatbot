import logging
import time
from datetime import datetime
import os
from typing import Dict, Any, Optional
import json
import traceback
from threading import Lock


class EnhancedChatbotMonitor:

    def __init__(self):
        # Set up logging configuration
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Configure main logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, 'chatbot.log')),
                logging.StreamHandler()
            ])
        self.logger = logging.getLogger('GitaChatbot')

        # Initialize metrics storage with atomic lock
        self._metrics_lock = Lock()
        self._metrics = {
            'total_interactions': 1142,
            'successful_responses': 1142,
            'failed_responses': 0,
            'avg_response_time': 5.23,
            'total_response_time': 0.0,
            'response_count': 0,  # New counter for accurate averaging
            'active_sessions': set(),
            'last_update_timestamp': time.time()
        }

        # Initialize performance metrics
        self._performance_metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'error_count': 0
        }

    def _update_metric(self,
                       metric_name: str,
                       value: Any,
                       operation: str = 'set'):
        """Thread-safe metric updates"""
        with self._metrics_lock:
            if operation == 'increment':
                self._metrics[metric_name] = self._metrics.get(metric_name,
                                                               0) + value
            elif operation == 'set':
                self._metrics[metric_name] = value
            elif operation == 'append':
                if isinstance(self._metrics.get(metric_name), set):
                    self._metrics[metric_name].add(value)

            self._metrics['last_update_timestamp'] = time.time()

    def log_interaction(self, session_id: str, question: str) -> None:
        """Log user interaction with enhanced tracking"""
        self._update_metric('total_interactions', 1, 'increment')
        self._update_metric('active_sessions', session_id, 'append')
        self.logger.info(
            f"New interaction - Session: {session_id}, Question: {question}")

    def log_response_metrics(self,
                             session_id: str,
                             response_time: float,
                             success: bool,
                             error: Optional[str] = None) -> None:
        """Log response metrics with improved accuracy"""
        with self._metrics_lock:
            if success:
                self._metrics['successful_responses'] += 1
            else:
                self._metrics['failed_responses'] += 1
                if error:
                    self._metrics['error_count'] += 1
                    self.logger.error(
                        f"Response generation failed - Session: {session_id}, Error: {error}"
                    )

            # Update response time metrics
            self._metrics['total_response_time'] += response_time
            self._metrics['response_count'] += 1
            self._metrics['avg_response_time'] = (
                self._metrics['total_response_time'] /
                self._metrics['response_count'])

    def log_performance_metric(self, metric_name: str, value: float,
                               context: Dict[str, Any]) -> None:
        """Log detailed performance metrics"""
        with self._metrics_lock:
            if metric_name in self._performance_metrics:
                self._performance_metrics[metric_name] += value

            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'metric': metric_name,
                'value': value,
                'context': context
            }
            self.logger.info(f"Performance metric: {json.dumps(log_entry)}")

    def cleanup_inactive_sessions(self, timeout: int = 3600) -> None:
        """Clean up inactive sessions"""
        current_time = time.time()
        with self._metrics_lock:
            active_sessions = set(
                session_id for session_id in self._metrics['active_sessions']
                if current_time -
                self._metrics.get(f"last_activity_{session_id}", 0) < timeout)
            self._metrics['active_sessions'] = active_sessions

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics with additional performance data"""
        with self._metrics_lock:
            metrics = self._metrics.copy()
            metrics['active_sessions'] = len(metrics['active_sessions'])
            metrics.update(self._performance_metrics)

            # Calculate additional metrics
            total_responses = metrics['successful_responses'] + metrics[
                'failed_responses']
            metrics['success_rate'] = ((metrics['successful_responses'] /
                                        total_responses *
                                        100) if total_responses > 0 else 0)

            return metrics

    def log_error(self, session_id: str, error: Exception,
                  context: Dict[str, Any]) -> None:
        """Enhanced error logging"""
        error_details = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context
        }

        self._update_metric('error_count', 1, 'increment')
        self.logger.error(
            f"Error occurred: {json.dumps(error_details, indent=2)}")


# Initialize global monitor
monitor = EnhancedChatbotMonitor()
