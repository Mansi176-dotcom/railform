import asyncio,csv,io,json,logging,os,uuid,html,time,hmac
from contextlib import asynccontextmanager
from collections import deque
from pathlib import Path
import numpy as np
import pywt
from scipy.signal import welch,resample_poly
from fastapi import FastAPI,WebSocket,HTTPException,Request
from fastapi.responses import JSONResponse,Response,HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from .models import Config,Workflow,VERSION
from .simulation import Simulator,NAMES
from .detection import Detector,calibrate
from .features import decimate
from . import persistence as db
from .evaluation import evaluate
from . import openai_service,access
from pydantic import BaseModel,Field
logging.basicConfig(level=logging.INFO,format='%(message)s');log=logging.getLogger('railform')
class Runtime:
    def __init__(self):
        self.config=Config();self.reference=calibrate();self.status='idle';self.clients=set();self.sequence=0;self.demo=False;self.coverage=0.;self.latency=0.;self.gaps=0;self.evaluation_lock=asyncio.Lock();self.reset()
    def reset(self,demo=False):
        self.status='idle';self.demo=demo;self.run=str(uuid.uuid4());self.sim=Simulator(self.config,demo);self.detector=Detector(self.config.sample_rate,self.reference);self.sequence=0;self.coverage=0.;self.alerts=[];self.raw_index=0;self.gaps=0;self.covered=set()
        db.save('run',self.run,{'config':self.config.model_dump(),'created_at':db.timestamp(),'detector':VERSION,'demo':demo},self.run)
        db.save('ground_truth',self.run,{'events':self.sim.truth()});db.save('detector',self.run,{'version':VERSION,'reference':self.reference});db.prune()
        Path('runtime/raw').mkdir(exist_ok=True)
        for p in Path('runtime/raw').glob('*.npz'):p.unlink()
    def packet(self):
        d=self.detector;position=float(d.positions[-1]) if len(d.positions) else 0.;elapsed=self.sim.index/self.config.sample_rate
        stage=('Healthy reference' if elapsed<14 else 'Light localized event' if elapsed<28 else 'Stronger localized event' if elapsed<50 else 'Wheel-related disturbance' if elapsed<70 else 'Sensor dropout' if elapsed<82 else 'Measured run summary')
        return {'run_id':self.run,'train_id':'RF-01','sample_sequence':self.sim.index,'sample_rate':self.config.sample_rate,'speed_kmh':self.config.speed,'units':'m/s²','sequence':self.sequence,'timestamp':db.timestamp(),'simulation_time':elapsed,'position':position,'coverage':self.coverage,'status':self.status,'features':d.last_features,'signals':[decimate(x,self.config.sample_rate) for x in d.raw] if d.raw.shape[1] else [],'latency':self.latency,'alerts':self.alerts[-100:],'buffer_gaps':self.gaps,'observed_sections':[sum(1 for m in range(i*75,(i+1)*75) if m in self.covered)/75 for i in range(40)],'demo':{'elapsed':elapsed,'stage':stage} if self.demo else None}
    async def worker(self):
        while True:
            if self.status=='running':
                # Fixed acquisition steps; playback only changes number of steps delivered per refresh.
                for _ in range(max(1,round(self.config.playback))):
                    start=time.perf_counter();chunk=self.sim.chunk();events=self.detector.ingest(chunk);self.latency=(time.perf_counter()-start)*1000;self.sequence+=1
                    valid=np.mean(np.isfinite(chunk['raw']),axis=0)>.95
                    self.covered.update((chunk['position'][valid]//1).astype(int).tolist());self.coverage=float(len(self.covered))
                    for event in events:
                        saved=db.save('alert',self.run,{**event,'run_id':self.run});self.alerts.append(saved);log.info(json.dumps({'event':'alert','run':self.run,'id':saved['id'],'label':saved['label']}))
                    self.alerts=self.alerts[-500:]
                    # Disk ring: 32 compressed raw chunks, separate from SQL summaries.
                    np.savez_compressed(f'runtime/raw/chunk-{self.raw_index%32:02d}.npz',raw=chunk['raw'],times=chunk['times'],position=chunk['position'],sample_rate=chunk['sample_rate'],run_id=self.run)
                    self.raw_index+=1
                    if self.sequence%10==0:db.save('feature',self.run,{'sequence':self.sequence,'features':self.detector.last_features},f'{self.run}-feature-{(self.sequence//10)%300}')
                    elapsed=self.sim.index/self.config.sample_rate
                    if (self.demo and elapsed>=90) or (not self.config.repeated and elapsed*self.config.speed/3.6>=3000):self.status='paused';break
            packet=self.packet()
            for queue in list(self.clients):
                if queue.full():
                    try:queue.get_nowait()
                    except asyncio.QueueEmpty:pass
                    self.gaps+=1;packet['buffer_gaps']=self.gaps
                queue.put_nowait(packet)
            await asyncio.sleep(.1)
runtime=None
@asynccontextmanager
async def lifespan(app):
    global runtime
    runtime=Runtime();worker=asyncio.create_task(runtime.worker());yield
    worker.cancel()
    try:await worker
    except asyncio.CancelledError:pass
app=FastAPI(title='RAILFORM',version=VERSION,lifespan=lifespan)
@app.middleware('http')
async def protect_workspace(request:Request,call_next):
    path=request.url.path
    exempt=path in ('/api/health','/api/ready','/api/access','/api/access/login')
    if path.startswith('/api/') and not exempt and not access.authenticated(request):
        return JSONResponse({'error':{'code':401,'message':'Unlock this research workspace first.'}},status_code=401)
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin and origin.split('://',1)[-1]!=request.headers.get('host'):
            return JSONResponse({'error':{'code':403,'message':'Cross-origin write rejected.'}},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    if path.startswith('/api/'):response.headers['Cache-Control']='no-store'
    return response
class AccessRequest(BaseModel):
    token:str=Field(min_length=1,max_length=512)
@app.get('/api/access')
def access_status(request:Request):
    return {'required':access.configured() or os.getenv('RAILFORM_ENV')=='production','authenticated':access.authenticated(request)}
@app.post('/api/access/login')
def access_login(request:Request,body:AccessRequest):
    if not access.allow_attempt(request):raise HTTPException(429,'Too many attempts. Wait a minute.')
    expected=os.getenv('RAILFORM_ACCESS_TOKEN','')
    if not expected or not hmac.compare_digest(body.token,expected):raise HTTPException(401,'Incorrect workspace access code.')
    response=JSONResponse({'authenticated':True})
    response.set_cookie(access.COOKIE,access.session_value(),httponly=True,secure=os.getenv('RAILFORM_ENV')=='production',samesite='strict',max_age=86400)
    return response
@app.get('/api/ai/status')
def ai_status():return openai_service.status()
@app.post('/api/alerts/{id}/explain')
async def ai_explanation(id:str):return await openai_service.explain(alert(id))

@app.exception_handler(HTTPException)
async def http_error(request,exc):return JSONResponse({'error':{'code':exc.status_code,'message':exc.detail}},status_code=exc.status_code)
@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):return JSONResponse({'error':{'code':422,'message':'Invalid configuration or workflow request','details':str(exc)}},status_code=422)
@app.get('/api/health')
def health():return {'status':'ready' if runtime else 'starting','detector':VERSION,'synthetic':True,'deployment':'full-stack','openai_configured':bool(os.getenv('OPENAI_API_KEY'))}
@app.get('/api/ready')
def ready():return health()
@app.get('/api/config')
def config():return runtime.config
@app.post('/api/config')
async def configure(c:Config):
    runtime.config=c;runtime.reference=calibrate(c.sample_rate);runtime.reset();return c
@app.get('/api/status')
def status():return runtime.packet()
@app.post('/api/start')
async def start():runtime.status='running';return {'status':runtime.status,'run_id':runtime.run}
@app.post('/api/pause')
async def pause():runtime.status='paused';return {'status':runtime.status}
@app.post('/api/reset')
async def reset():runtime.reset();return {'status':runtime.status,'run_id':runtime.run}
@app.post('/api/demo')
async def demo():
    runtime.config=Config(seed=42,speed=120,playback=1,preset=0,repeated=False);runtime.reference=calibrate();runtime.reset(True);runtime.status='running';return {'run_id':runtime.run,'duration_s':90}
@app.post('/api/demo/exit')
async def exit_demo():runtime.demo=False;runtime.status='paused';return {'status':runtime.status}
@app.get('/api/sensors')
def sensors():return [{'id':f'RF-01-{i}','train_id':'RF-01','name':name,'axis':name.split(' · ')[1],'units':'m/s²','sample_rate':runtime.config.sample_rate} for i,name in enumerate(NAMES)]
@app.get('/api/alerts')
def alerts():return runtime.alerts
@app.get('/api/alerts/{id}')
def alert(id:str):
    a=db.get(id)
    if not a or 'label' not in a:raise HTTPException(404,'Alert not found')
    return a
@app.post('/api/alerts/{id}')
async def workflow(id:str,w:Workflow):
    a=alert(id);a['status']=w.status;a['history'].append({'at':db.timestamp(),'status':w.status,'note':w.note});a=db.save('alert',a.get('run_id',runtime.run),a,id)
    runtime.alerts=[a if x['id']==id else x for x in runtime.alerts];return a
@app.get('/api/ground-truth')
def truth():return runtime.sim.truth()
@app.get('/api/analysis')
def analysis(sensor:int=1):
    if sensor not in range(4):raise HTTPException(422,'Sensor must be 0–3')
    d=runtime.detector;fs=runtime.config.sample_rate
    if not d.latest:raise HTTPException(409,'No complete analysis window yet')
    x=d.latest['filtered'][sensor];f,p=welch(x,fs,nperseg=1024);small=resample_poly(x,1,4);freq=np.geomspace(30,1500,24);scales=pywt.central_frequency('morl')*(fs/4)/freq
    co,actual=pywt.cwt(small,scales,'morl',sampling_period=4/fs);power=abs(co)**2;step=max(1,power.shape[1]//90);power=power[:,::step];times=np.arange(power.shape[1])*step*4/fs
    return {'samples':len(x),'raw':decimate(d.latest['raw'][sensor],fs),'filtered':decimate(x,fs),'features':d.latest['features'],'history':d.latest['history'],'psd':[[float(a),float(b)] for a,b in zip(f,p)],'wavelet':{'frequencies':[round(v) for v in actual],'times':[round(t,3) for t in times],'data':[[j,i,float(power[i,j])] for i in range(len(freq)) for j in range(len(times))],'max':float(power.max()),'units':'Coefficient power (library normalization); window edge effects'}}
@app.get('/api/windows')
def windows(sensor:int=1):return analysis(sensor)
@app.get('/api/features')
def features():return runtime.detector.last_features
@app.get('/api/spectrum')
def spectrum(sensor:int=1):return analysis(sensor)['psd']
@app.post('/api/evaluation')
async def evaluation():
    if runtime.evaluation_lock.locked():raise HTTPException(409,'Evaluation already running')
    async with runtime.evaluation_lock:
        result=await asyncio.to_thread(evaluate,runtime.reference.copy());return db.save('evaluation',runtime.run,result)
@app.get('/api/evaluation')
def results():return db.records('evaluation')
@app.get('/api/export')
def export(format:str='json'):
    payload={'synthetic':True,'run':db.get(runtime.run),'alerts':runtime.alerts,'features':runtime.detector.last_features,'evaluations':db.records('evaluation',runtime.run),'ai_explanations':db.records('ai_explanation',runtime.run),'limitations':'Research simulation only; no field validation.'}
    if format=='json':return Response(json.dumps(payload,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="railform-run.json"'})
    if format!='csv':raise HTTPException(422,'Format must be csv or json')
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=['id','time','position','segment','label','score','severity','evidence','status'],extrasaction='ignore');writer.writeheader();writer.writerows(runtime.alerts)
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="railform-alerts.csv"'})
@app.get('/api/report/{id}',response_class=HTMLResponse)
def report(id:str):
    a=alert(id);esc=lambda v:html.escape(str(v));rows=''.join(f'<tr><td>{esc(k)}</td><td>{esc(v)}</td><td>{esc(a["references"].get(k,"—"))}</td></tr>' for k,v in a['features'].items())
    return f'''<!doctype html><html lang="en"><title>RAILFORM diagnostic report</title><style>body{{font:15px/1.7 system-ui;color:#242a2d;max-width:850px;margin:60px auto;padding:25px}}h1{{font-size:35px}}small{{color:#626b70}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:9px;border-bottom:1px solid #ddd}}pre{{white-space:pre-wrap}}@media print{{button{{display:none}}body{{margin:0}}}}</style><button onclick="window.print()">Print / Save PDF</button><h1>RAILFORM / Diagnostic report</h1><small>SYNTHETIC DATA · RESEARCH USE ONLY</small><h2>{esc(a['label'])}</h2><p>{esc(a['segment'])} · {a['position']:.2f} m · {a['time']:.3f} s</p><p>{esc(a['explanation'])}</p><table><tr><th>Measured feature</th><th>Value</th><th>Reference</th></tr>{rows}</table><h2>Alternatives & next review</h2><p>{esc(a['alternatives'])}</p><p>{esc(a['next'])}</p><h2>Run configuration</h2><pre>{esc(json.dumps(db.get(a.get('run_id',runtime.run)),indent=2))}</pre><h2>Review history</h2><pre>{esc(json.dumps(a['history'],indent=2))}</pre><p>{esc(a['limitations'])}</p><small>Detector {VERSION} · Exported {db.timestamp()}</small></html>'''
@app.websocket('/ws')
async def stream(ws:WebSocket):
    if not access.authenticated(ws):
        await ws.close(code=1008);return
    origin=ws.headers.get('origin')
    if origin and origin.split('://',1)[-1]!=ws.headers.get('host'):
        await ws.close(code=1008);return
    await ws.accept();queue=asyncio.Queue(maxsize=3);runtime.clients.add(queue)
    try:
        await ws.send_json(runtime.packet())
        while True:await ws.send_json(await queue.get())
    except Exception:pass
    finally:runtime.clients.discard(queue)
if Path('dist').exists():app.mount('/',StaticFiles(directory='dist',html=True),name='frontend')
