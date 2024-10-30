import logging
import time
from datetime import datetime
import os
from typing import Dict, Any, Optional
import json
import traceback

class ChatbotMonitor:
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
            ]
        )
        self.logger = logging.getLogger('GitaChatbot')
        
        # Initialize metrics storage
        self.metrics = {
            'total_interactions': 0,
            'successful_responses': 0,
            'failed_responses': 0,
            'avg_response_time': 0,
            'total_response_time': 0
        }
        
        # Initialize session tracking
        self.active_sessions = set()
        
    def log_interaction(self, session_id: str, question: str) -> None:
        """Log user interaction"""
        self.metrics['total_interactions'] += 1
        self.active_sessions.add(session_id)
        self.logger.info(f"New interaction - Session: {session_id}, Question: {question}")
        
    def log_response_metrics(self, session_id: str, response_time: float, success: bool, 
                           error: Optional[str] = None) -> None:
        """Log response generation metrics"""
        if success:
            self.metrics['successful_responses'] += 1
        else:
            self.metrics['failed_responses'] += 1
            if error:
                self.logger.error(f"Response generation failed - Session: {session_id}, Error: {error}")
        
        # Update average response time
        self.metrics['total_response_time'] += response_time
        self.metrics['avg_response_time'] = (
            self.metrics['total_response_time'] / 
            (self.metrics['successful_responses'] + self.metrics['failed_responses'])
        )
        
    def log_error(self, session_id: str, error: Exception, context: Dict[str, Any]) -> None:
        """Log detailed error information"""
        error_details = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context
        }
        self.logger.error(f"Error occurred: {json.dumps(error_details, indent=2)}")
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        metrics = self.metrics.copy()
        metrics['active_sessions'] = len(self.active_sessions)
        return metrics
    
    def log_performance_metric(self, metric_name: str, value: float, context: Dict[str, Any]) -> None:
        """Log performance-related metrics"""
        self.logger.info(f"Performance metric - {metric_name}: {value}, Context: {json.dumps(context)}")

# Initialize global monitor
monitor = ChatbotMonitor()
