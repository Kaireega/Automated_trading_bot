#!/usr/bin/env python3
"""
Comprehensive Debugging Utilities for Trading Bot

This module provides centralized debugging utilities that can be used throughout
the trading bot system to add detailed logging, error tracking, and performance
monitoring to every line of code.

Features:
- Line-by-line execution tracking
- Variable state monitoring
- Performance timing
- Error context capture
- Memory usage tracking
- Function call tracing
- Data flow visualization
- Exception handling with context
"""

import logging
import time
import traceback
import sys
import inspect
import functools
import psutil
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import threading
from pathlib import Path


@dataclass
class DebugContext:
    """Context information for debugging a specific operation."""
    function_name: str
    line_number: int
    file_name: str
    timestamp: datetime
    variables: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    memory_usage: Dict[str, float] = field(default_factory=dict)
    call_stack: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DebugTracker:
    """Centralized debug tracking system."""
    
    def __init__(self, log_level: str = "DEBUG"):
        self.logger = logging.getLogger("debug_tracker")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create debug log file
        debug_log_path = Path("logs/debug_tracking.log")
        debug_log_path.parent.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(debug_log_path)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        self.contexts: deque = deque(maxlen=1000)  # Keep last 1000 contexts
        self.performance_data: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.lock = threading.Lock()
    
    def create_context(self, function_name: str, line_number: int, file_name: str) -> DebugContext:
        """Create a new debug context."""
        context = DebugContext(
            function_name=function_name,
            line_number=line_number,
            file_name=file_name,
            timestamp=datetime.now(),
            call_stack=self._get_call_stack()
        )
        
        with self.lock:
            self.contexts.append(context)
        
        return context
    
    def _get_call_stack(self) -> List[str]:
        """Get the current call stack."""
        stack = []
        for frame_info in inspect.stack():
            stack.append(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
        return stack
    
    def log_execution(self, context: DebugContext, message: str, variables: Optional[Dict] = None):
        """Log execution details with context."""
        log_msg = f"[{context.file_name}:{context.line_number}] {context.function_name}: {message}"
        
        if variables:
            context.variables.update(variables)
            log_msg += f" | Variables: {json.dumps(variables, default=str)}"
        
        self.logger.debug(log_msg)
    
    def log_variable_state(self, context: DebugContext, var_name: str, var_value: Any):
        """Log the state of a specific variable."""
        context.variables[var_name] = var_value
        self.logger.debug(
            f"[{context.file_name}:{context.line_number}] {context.function_name}: "
            f"Variable '{var_name}' = {json.dumps(var_value, default=str)}"
        )
    
    def log_performance(self, context: DebugContext, operation: str, duration: float):
        """Log performance metrics."""
        context.performance_metrics[operation] = duration
        self.performance_data[operation].append(duration)
        
        self.logger.debug(
            f"[{context.file_name}:{context.line_number}] {context.function_name}: "
            f"Performance - {operation}: {duration:.4f}s"
        )
    
    def log_memory_usage(self, context: DebugContext):
        """Log current memory usage."""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        context.memory_usage = {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
        
        self.logger.debug(
            f"[{context.file_name}:{context.line_number}] {context.function_name}: "
            f"Memory - RSS: {context.memory_usage['rss']:.2f}MB, "
            f"VMS: {context.memory_usage['vms']:.2f}MB, "
            f"Percent: {context.memory_usage['percent']:.2f}%"
        )
    
    def log_error(self, context: DebugContext, error: Exception, additional_info: str = ""):
        """Log errors with full context."""
        error_msg = f"Error in {context.function_name}: {str(error)}"
        if additional_info:
            error_msg += f" | {additional_info}"
        
        context.errors.append(error_msg)
        self.error_counts[context.function_name] += 1
        
        self.logger.error(f"[{context.file_name}:{context.line_number}] {error_msg}")
        self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def log_warning(self, context: DebugContext, warning: str):
        """Log warnings with context."""
        context.warnings.append(warning)
        self.logger.warning(
            f"[{context.file_name}:{context.line_number}] {context.function_name}: {warning}"
        )
    
    def get_performance_summary(self) -> Dict[str, Dict[str, float]]:
        """Get performance summary statistics."""
        summary = {}
        for operation, times in self.performance_data.items():
            if times:
                summary[operation] = {
                    'count': len(times),
                    'total': sum(times),
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times)
                }
        return summary
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get error summary by function."""
        return dict(self.error_counts)
    
    def export_debug_report(self, file_path: str = "logs/debug_report.json"):
        """Export comprehensive debug report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'contexts': [
                {
                    'function_name': ctx.function_name,
                    'file_name': ctx.file_name,
                    'line_number': ctx.line_number,
                    'timestamp': ctx.timestamp.isoformat(),
                    'variables': ctx.variables,
                    'performance_metrics': ctx.performance_metrics,
                    'memory_usage': ctx.memory_usage,
                    'errors': ctx.errors,
                    'warnings': ctx.warnings
                }
                for ctx in self.contexts
            ],
            'performance_summary': self.get_performance_summary(),
            'error_summary': self.get_error_summary()
        }
        
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Debug report exported to {file_path}")


# Global debug tracker instance
debug_tracker = DebugTracker()


def debug_line(func: Callable) -> Callable:
    """Decorator to add line-by-line debugging to any function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get function context
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        file_name = caller_frame.f_code.co_filename
        line_number = caller_frame.f_lineno
        function_name = func.__name__
        
        # Create debug context
        context = debug_tracker.create_context(function_name, line_number, file_name)
        
        # Log function entry
        debug_tracker.log_execution(
            context, 
            f"Entering function with args={args}, kwargs={kwargs}"
        )
        debug_tracker.log_memory_usage(context)
        
        start_time = time.time()
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Log function exit
            duration = time.time() - start_time
            debug_tracker.log_performance(context, f"{function_name}_execution", duration)
            debug_tracker.log_execution(context, f"Function completed successfully, result={result}")
            
            return result
            
        except Exception as e:
            # Log error
            debug_tracker.log_error(context, e, f"Function {function_name} failed")
            raise
            
        finally:
            debug_tracker.log_memory_usage(context)
    
    return wrapper


def debug_variable(var_name: str, var_value: Any, context: Optional[DebugContext] = None):
    """Debug a specific variable."""
    if context is None:
        # Create context from current frame
        frame = inspect.currentframe().f_back
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name
        context = debug_tracker.create_context(function_name, line_number, file_name)
    
    debug_tracker.log_variable_state(context, var_name, var_value)


@contextmanager
def debug_context(operation_name: str):
    """Context manager for debugging a specific operation."""
    frame = inspect.currentframe().f_back
    file_name = frame.f_code.co_filename
    line_number = frame.f_lineno
    function_name = frame.f_code.co_name
    
    context = debug_tracker.create_context(function_name, line_number, file_name)
    
    debug_tracker.log_execution(context, f"Starting operation: {operation_name}")
    debug_tracker.log_memory_usage(context)
    
    start_time = time.time()
    
    try:
        yield context
    except Exception as e:
        debug_tracker.log_error(context, e, f"Operation {operation_name} failed")
        raise
    finally:
        duration = time.time() - start_time
        debug_tracker.log_performance(context, operation_name, duration)
        debug_tracker.log_execution(context, f"Completed operation: {operation_name}")
        debug_tracker.log_memory_usage(context)


def debug_performance(func: Callable) -> Callable:
    """Decorator to track performance of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        file_name = caller_frame.f_code.co_filename
        line_number = caller_frame.f_lineno
        function_name = func.__name__
        
        context = debug_tracker.create_context(function_name, line_number, file_name)
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            debug_tracker.log_performance(context, f"{function_name}_performance", duration)
            return result
        except Exception as e:
            debug_tracker.log_error(context, e)
            raise
    
    return wrapper


def debug_data_flow(data_name: str, data_value: Any, operation: str = "processing"):
    """Debug data flow through the system."""
    frame = inspect.currentframe().f_back
    file_name = frame.f_code.co_filename
    line_number = frame.f_lineno
    function_name = frame.f_code.co_name
    
    context = debug_tracker.create_context(function_name, line_number, file_name)
    
    debug_tracker.log_execution(
        context, 
        f"Data flow - {operation} {data_name}",
        {f"{data_name}_type": type(data_value).__name__, 
         f"{data_name}_size": len(str(data_value)) if hasattr(data_value, '__len__') else 'N/A'}
    )


def debug_api_call(api_name: str, endpoint: str, params: Dict = None, response: Any = None):
    """Debug API calls."""
    frame = inspect.currentframe().f_back
    file_name = frame.f_code.co_filename
    line_number = frame.f_lineno
    function_name = frame.f_code.co_name
    
    context = debug_tracker.create_context(function_name, line_number, file_name)
    
    debug_info = {
        'api_name': api_name,
        'endpoint': endpoint,
        'params': params,
        'response_type': type(response).__name__ if response else 'None'
    }
    
    debug_tracker.log_execution(context, f"API Call: {api_name} -> {endpoint}", debug_info)


def debug_trade_decision(signal: str, pair: str, price: float, confidence: float, context: Optional[DebugContext] = None):
    """Debug trading decisions."""
    if context is None:
        frame = inspect.currentframe().f_back
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name
        context = debug_tracker.create_context(function_name, line_number, file_name)
    
    trade_info = {
        'signal': signal,
        'pair': pair,
        'price': price,
        'confidence': confidence,
        'timestamp': datetime.now().isoformat()
    }
    
    debug_tracker.log_execution(context, f"Trade Decision: {signal} {pair} at {price}", trade_info)


def debug_strategy_execution(strategy_name: str, signal: str, indicators: Dict, context: Optional[DebugContext] = None):
    """Debug strategy execution."""
    if context is None:
        frame = inspect.currentframe().f_back
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name
        context = debug_tracker.create_context(function_name, line_number, file_name)
    
    strategy_info = {
        'strategy_name': strategy_name,
        'signal': signal,
        'indicators': indicators,
        'timestamp': datetime.now().isoformat()
    }
    
    debug_tracker.log_execution(context, f"Strategy Execution: {strategy_name} -> {signal}", strategy_info)


def debug_risk_calculation(risk_type: str, value: float, max_value: float, context: Optional[DebugContext] = None):
    """Debug risk calculations."""
    if context is None:
        frame = inspect.currentframe().f_back
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name
        context = debug_tracker.create_context(function_name, line_number, file_name)
    
    risk_info = {
        'risk_type': risk_type,
        'current_value': value,
        'max_value': max_value,
        'percentage': (value / max_value * 100) if max_value > 0 else 0,
        'timestamp': datetime.now().isoformat()
    }
    
    debug_tracker.log_execution(context, f"Risk Calculation: {risk_type}", risk_info)


def debug_indicator_calculation(indicator_name: str, values: List[float], result: float, context: Optional[DebugContext] = None):
    """Debug technical indicator calculations."""
    if context is None:
        frame = inspect.currentframe().f_back
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name
        context = debug_tracker.create_context(function_name, line_number, file_name)
    
    indicator_info = {
        'indicator_name': indicator_name,
        'input_values_count': len(values),
        'input_values_sample': values[-5:] if len(values) > 5 else values,
        'result': result,
        'timestamp': datetime.now().isoformat()
    }
    
    debug_tracker.log_execution(context, f"Indicator Calculation: {indicator_name}", indicator_info)


def debug_backtest_step(step: int, total_steps: int, current_price: float, signal: str, context: Optional[DebugContext] = None):
    """Debug backtesting steps."""
    if context is None:
        frame = inspect.currentframe().f_back
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name
        context = debug_tracker.create_context(function_name, line_number, file_name)
    
    backtest_info = {
        'step': step,
        'total_steps': total_steps,
        'progress_percent': (step / total_steps * 100) if total_steps > 0 else 0,
        'current_price': current_price,
        'signal': signal,
        'timestamp': datetime.now().isoformat()
    }
    
    debug_tracker.log_execution(context, f"Backtest Step: {step}/{total_steps}", backtest_info)


def get_debug_summary() -> Dict[str, Any]:
    """Get a summary of all debug information."""
    return {
        'performance_summary': debug_tracker.get_performance_summary(),
        'error_summary': debug_tracker.get_error_summary(),
        'total_contexts': len(debug_tracker.contexts),
        'memory_usage': psutil.Process(os.getpid()).memory_info()._asdict()
    }


def export_debug_report(file_path: str = None):
    """Export debug report."""
    if file_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"logs/debug_report_{timestamp}.json"
    
    debug_tracker.export_debug_report(file_path)
    return file_path


# Convenience functions for common debugging patterns
def debug_entry_point(module_name: str):
    """Debug entry point for modules."""
    frame = inspect.currentframe().f_back
    file_name = frame.f_code.co_filename
    line_number = frame.f_lineno
    function_name = frame.f_code.co_name
    
    context = debug_tracker.create_context(function_name, line_number, file_name)
    debug_tracker.log_execution(context, f"Module {module_name} entry point reached")


def debug_exit_point(module_name: str, result: Any = None):
    """Debug exit point for modules."""
    frame = inspect.currentframe().f_back
    file_name = frame.f_code.co_filename
    line_number = frame.f_lineno
    function_name = frame.f_code.co_name
    
    context = debug_tracker.create_context(function_name, line_number, file_name)
    debug_tracker.log_execution(context, f"Module {module_name} exit point reached", {'result': result})


def debug_conditional(condition: bool, true_msg: str, false_msg: str, context: Optional[DebugContext] = None):
    """Debug conditional statements."""
    if context is None:
        frame = inspect.currentframe().f_back
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name
        context = debug_tracker.create_context(function_name, line_number, file_name)
    
    message = true_msg if condition else false_msg
    debug_tracker.log_execution(context, f"Conditional: {message}", {'condition': condition})


def debug_loop_iteration(loop_name: str, iteration: int, total_iterations: int = None, context: Optional[DebugContext] = None):
    """Debug loop iterations."""
    if context is None:
        frame = inspect.currentframe().f_back
        file_name = frame.f_code.co_filename
        line_number = frame.f_lineno
        function_name = frame.f_code.co_name
        context = debug_tracker.create_context(function_name, line_number, file_name)
    
    progress_info = {
        'iteration': iteration,
        'total_iterations': total_iterations,
        'progress_percent': (iteration / total_iterations * 100) if total_iterations else None
    }
    
    debug_tracker.log_execution(context, f"Loop {loop_name} iteration {iteration}", progress_info)
