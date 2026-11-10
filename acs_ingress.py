"""Bound streamed input before any framework JSON/multipart parser runs."""
from __future__ import annotations
import asyncio
import time
import acs_api_errors as E


async def bounded_body(scope, receive, max_bytes, *, deadline_seconds=30):
    lengths=[v for k,v in scope.get('headers',[]) if k.lower()==b'content-length']
    if len(lengths)>1:
        raise E.AcsApiError(E.ACS_BAD_REQUEST)
    if lengths:
        try:
            declared=int(lengths[0])
            if declared<0: raise ValueError()
        except (TypeError,ValueError):
            raise E.AcsApiError(E.ACS_BAD_REQUEST) from None
        if declared>max_bytes:
            raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE)
    body=bytearray()
    deadline=time.monotonic()+deadline_seconds
    while True:
        try:
            remaining=deadline-time.monotonic()
            if remaining<=0: raise asyncio.TimeoutError()
            message=await asyncio.wait_for(receive(),remaining)
        except asyncio.TimeoutError:
            raise E.AcsApiError(E.ACS_BAD_REQUEST, 'انتهت مهلة إرسال الطلب قبل اكتماله.',status=408) from None
        if not isinstance(message,dict):raise E.AcsApiError(E.ACS_BAD_REQUEST)
        if message.get('type')=='http.disconnect':return None
        if message.get('type')!='http.request':raise E.AcsApiError(E.ACS_BAD_REQUEST)
        chunk=message.get('body',b'')
        if not isinstance(chunk,(bytes,bytearray)):raise E.AcsApiError(E.ACS_BAD_REQUEST)
        # Check before extend: never copy an already oversized chunk.
        if len(body)+len(chunk)>max_bytes:raise E.AcsApiError(E.ACS_PAYLOAD_TOO_LARGE)
        body.extend(chunk)
        if not message.get('more_body',False):break
    if lengths and declared!=len(body):raise E.AcsApiError(E.ACS_BAD_REQUEST)
    return bytes(body)


def replay(body, receive):
    sent=False
    async def bounded_receive():
        nonlocal sent
        if not sent:
            sent=True
            return {'type':'http.request','body':body,'more_body':False}
        return await receive()
    return bounded_receive
