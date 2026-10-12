"""Single research workspace access for deployments; signed, HTTP-only session."""
import hashlib,hmac,os,time
from collections import OrderedDict
from fastapi import Request,WebSocket
COOKIE='railform_session'
attempts=OrderedDict()

def configured():return bool(os.getenv('RAILFORM_ACCESS_TOKEN'))
def session_value():
    expires=str(int(time.time())+86400)
    signature=hmac.new(os.environ['RAILFORM_ACCESS_TOKEN'].encode(),expires.encode(),hashlib.sha256).hexdigest()
    return expires+'.'+signature

def authenticated(request):
    if not configured():return os.getenv('RAILFORM_ENV')!='production'
    raw=request.cookies.get(COOKIE,'')
    try:
        expires,signature=raw.split('.',1)
        expected=hmac.new(os.environ['RAILFORM_ACCESS_TOKEN'].encode(),expires.encode(),hashlib.sha256).hexdigest()
        return int(expires)>time.time() and hmac.compare_digest(signature,expected)
    except (ValueError,TypeError):return False

def allow_attempt(request):
    host=request.client.host if request.client else 'unknown';now=time.monotonic()
    times=[x for x in attempts.get(host,[]) if now-x<60]
    attempts[host]=times+[now];attempts.move_to_end(host)
    while len(attempts)>1000:attempts.popitem(last=False)
    return len(times)<10
