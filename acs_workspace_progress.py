"""Bounded worker progress; carries no authentication or approval authority."""
from contextlib import contextmanager
from contextvars import ContextVar
import json

_channel = ContextVar('acs_workspace_progress', default=None)
_resume = ContextVar('acs_workspace_resume', default=None)
_phase = ContextVar('acs_workspace_phase', default='UNDERSTANDING')
_planning_system = ContextVar('acs_workspace_planning_system', default=None)
PHASES = frozenset({'UNDERSTANDING','LAYOUT','ROOM_DETAILS','REVIEW','SAVING'})

@contextmanager
def channel(callback, resume=None):
    c = _channel.set(callback)
    r = _resume.set(resume)
    try:
        yield
    finally:
        _channel.reset(c)
        _resume.reset(r)

def saved():
    return _resume.get()

@contextmanager
def resuming(checkpoint):
    token = _resume.set(checkpoint)
    try:
        yield
    finally:
        _resume.reset(token)

def spent(count):
    emit(_phase.get(), provider_calls=count)

@contextmanager
def planning_policy(system):
    token = _planning_system.set(system)
    try:
        yield
    finally:
        _planning_system.reset(token)

def planning_system(stage):
    return _planning_system.get() if stage in {'outline','plan_chunk'} else None

def emit(phase, checkpoint=None, **counts):
    callback = _channel.get()
    if callback is None or phase not in PHASES:
        return
    event = {'phase':phase}
    _phase.set(phase)
    event.update({k:v for k,v in counts.items() if k in {'completed','total','provider_calls'} and type(v) is int and v >= 0})
    if checkpoint is not None:
        raw = json.dumps(checkpoint, ensure_ascii=False, allow_nan=False)
        if len(raw.encode()) > 2_000_000:
            raise ValueError('Checkpoint exceeds limit')
        event['checkpoint'] = json.loads(raw)
    callback(event)
