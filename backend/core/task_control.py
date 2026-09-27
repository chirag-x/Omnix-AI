"""Cooperative cancellation shared by the agent, tools, and audio player."""
import threading


class TaskCancelled(Exception):
    """The user stopped the current task."""


_cancelled = threading.Event()
_callbacks = []
_lock = threading.Lock()


def register_stop_callback(callback):
    with _lock:
        if callback not in _callbacks:
            _callbacks.append(callback)


def request_stop():
    _cancelled.set()
    with _lock:
        callbacks = tuple(_callbacks)
    for callback in callbacks:
        try:
            callback()
        except Exception:
            # A missing audio device must never prevent task cancellation.
            pass


def reset():
    _cancelled.clear()


def check_cancelled():
    if _cancelled.is_set():
        raise TaskCancelled("Task stopped by user.")


def wait(seconds):
    if _cancelled.wait(max(0.0, float(seconds))):
        raise TaskCancelled("Task stopped by user.")
