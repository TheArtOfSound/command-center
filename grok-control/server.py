from __future__ import annotations
import asyncio, json, os, shutil, time, uuid
from collections import deque
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

HERE=Path(__file__).resolve().parent
ROOT=Path(os.getenv('QIRA_WORKSPACE_ROOT','~/Documents/GitHub')).expanduser().resolve()
PROJECT_FILE=HERE/'projects.json'; SESSIONS={}
app=FastAPI(title='Qira Grok Ops',version='0.1.0')

def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def defs(): return json.loads(PROJECT_FILE.read_text())
def project_path(p):
    if p.get('path_env') and os.getenv(p['path_env']): return Path(os.environ[p['path_env']]).expanduser().resolve()
    if p.get('workspace_root'): return ROOT
    choices=p.get('folder_candidates') or [p.get('folder')]
    for name in filter(None,choices):
        path=(ROOT/name).resolve()
        if path.exists(): return path
    return (ROOT/next(filter(None,choices),p['id'])).resolve()
def confined(root,path):
    p=Path(path).expanduser().resolve()
    if p!=root and root not in p.parents: raise PermissionError(f'Path escapes project root: {p}')
    return p
async def run(*args,cwd=None,timeout=6):
    try:
        p=await asyncio.create_subprocess_exec(*args,cwd=str(cwd) if cwd else None,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
        out,_=await asyncio.wait_for(p.communicate(),timeout)
        return p.returncode or 0,out.decode(errors='replace').strip()
    except Exception as e: return 127,str(e)

class Agent:
    def __init__(self,p,approval,model,effort):
        self.id=str(uuid.uuid4()); self.project=p; self.root=project_path(p); self.approval=approval; self.model=model; self.effort=effort
        self.proc=None; self.acp=None; self.seq=1; self.pending={}; self.permissions={}; self.terminals={}; self.events=deque(maxlen=1000); self.clients=set(); self.lock=asyncio.Lock(); self.state='starting'; self.tasks=[]
    async def emit(self,e):
        e.setdefault('timestamp',now()); self.events.append(e)
        dead=[]
        for ws in list(self.clients):
            try: await ws.send_json(e)
            except Exception: dead.append(ws)
        for ws in dead: self.clients.discard(ws)
    async def send(self,m):
        if not self.proc or not self.proc.stdin: raise RuntimeError('Grok process is not running')
        self.proc.stdin.write((json.dumps(m,separators=(',',':'))+'\n').encode()); await self.proc.stdin.drain()
    async def request(self,method,params,timeout=120):
        i=self.seq; self.seq+=1; f=asyncio.get_running_loop().create_future(); self.pending[i]=f
        await self.send({'jsonrpc':'2.0','id':i,'method':method,'params':params})
        try: return await asyncio.wait_for(f,timeout) or {}
        finally: self.pending.pop(i,None)
    async def reply(self,i,result=None,error=None):
        await self.send({'jsonrpc':'2.0','id':i,**({'error':error} if error else {'result':result})})
    async def start(self):
        if not shutil.which('grok'): raise RuntimeError('Install Grok: curl -fsSL https://x.ai/cli/install.sh | bash')
        if not self.root.exists(): raise RuntimeError(f'Project path not found: {self.root}')
        args=['grok','--no-auto-update']
        if self.approval=='always': args+=['--always-approve']
        if self.model: args+=['--model',self.model]
        if self.effort: args+=['--effort',self.effort]
        args+=['agent','stdio']
        self.proc=await asyncio.create_subprocess_exec(*args,cwd=str(self.root),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,env=os.environ.copy())
        self.tasks=[asyncio.create_task(self.reader()),asyncio.create_task(self.stderr())]
        init=await self.request('initialize',{'protocolVersion':1,'clientCapabilities':{'fs':{'readTextFile':True,'writeTextFile':True},'terminal':True}},30)
        methods={m.get('id') for m in init.get('authMethods',[])}
        auth='xai.api_key' if os.getenv('XAI_API_KEY') and 'xai.api_key' in methods else ('cached_token' if 'cached_token' in methods else None)
        if not auth: raise RuntimeError('Run `grok login` or set XAI_API_KEY')
        await self.request('authenticate',{'methodId':auth,'_meta':{'headless':True}},60)
        self.acp=(await self.request('session/new',{'cwd':str(self.root),'mcpServers':[]},60)).get('sessionId')
        if not self.acp: raise RuntimeError('Grok returned no ACP session ID')
        self.state='ready'; await self.emit({'type':'session_ready','session_id':self.id,'project_id':self.project['id'],'root':str(self.root),'capabilities':init.get('agentCapabilities',{})})
    async def reader(self):
        while self.proc and self.proc.stdout:
            line=await self.proc.stdout.readline()
            if not line: break
            raw=line.decode(errors='replace').strip()
            if not raw: continue
            try: m=json.loads(raw)
            except Exception: await self.emit({'type':'raw','stream':'stdout','text':raw}); continue
            if 'id' in m and 'method' not in m:
                f=self.pending.get(m['id'])
                if f and not f.done(): f.set_exception(RuntimeError(m['error'].get('message',str(m['error'])))) if m.get('error') else f.set_result(m.get('result'))
            elif 'id' in m and 'method' in m: asyncio.create_task(self.client_call(m))
            elif m.get('method')=='session/update': await self.emit({'type':'session_update','params':m.get('params',{})})
            else: await self.emit({'type':'notification','message':m})
        if self.state!='stopped': self.state='exited'; await self.emit({'type':'process_exit','returncode':self.proc.returncode if self.proc else None})
    async def stderr(self):
        while self.proc and self.proc.stderr:
            line=await self.proc.stderr.readline()
            if not line: break
            await self.emit({'type':'raw','stream':'stderr','text':line.decode(errors='replace').rstrip()})
    async def client_call(self,m):
        i=m['id']; method=m.get('method'); p=m.get('params') or {}
        try:
            if method=='session/request_permission': await self.permission(i,p)
            elif method=='fs/read_text_file':
                path=confined(self.root,p['path']); text=path.read_text(); line=max(int(p.get('line',1)),1); limit=p.get('limit')
                if line!=1 or limit is not None:
                    rows=text.splitlines(keepends=True); text=''.join(rows[line-1:line-1+int(limit)] if limit is not None else rows[line-1:])
                await self.reply(i,{'content':text})
            elif method=='fs/write_text_file':
                path=confined(self.root,p['path']); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(p.get('content','')); await self.reply(i,None)
            elif method=='terminal/create': await self.term_create(i,p)
            elif method=='terminal/output': await self.term_output(i,p)
            elif method=='terminal/wait_for_exit': await self.term_wait(i,p)
            elif method in ('terminal/kill','terminal/release'): await self.term_stop(i,p,method.endswith('release'))
            else: await self.reply(i,error={'code':-32601,'message':f'Unsupported client method: {method}'})
        except Exception as e: await self.reply(i,error={'code':-32000,'message':str(e)}); await self.emit({'type':'client_error','method':method,'error':str(e)})
    async def permission(self,i,p):
        options=p.get('options',[])
        if self.approval=='always':
            option=next((o for o in options if o.get('kind') in ('allow_always','allow_once')),None)
            await self.reply(i,{'outcome':{'outcome':'selected','optionId':option['optionId']}} if option else {'outcome':{'outcome':'cancelled'}}); return
        f=asyncio.get_running_loop().create_future(); self.permissions[i]=f; await self.emit({'type':'permission_request','request_id':i,'params':p})
        try:
            option=await asyncio.wait_for(f,600); result={'outcome':{'outcome':'selected','optionId':option}} if option else {'outcome':{'outcome':'cancelled'}}; await self.reply(i,result)
        except asyncio.TimeoutError: await self.reply(i,{'outcome':{'outcome':'cancelled'}})
        finally: self.permissions.pop(i,None)
    async def term_create(self,i,p):
        cwd=confined(self.root,p.get('cwd') or self.root); env=os.environ.copy()
        for item in p.get('env',[]): env[str(item['name'])]=str(item['value'])
        proc=await asyncio.create_subprocess_exec(p['command'],*[str(x) for x in p.get('args',[])],cwd=str(cwd),env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
        tid='term_'+uuid.uuid4().hex[:12]; t={'proc':proc,'out':bytearray(),'limit':min(max(int(p.get('outputByteLimit',1048576)),4096),10485760),'truncated':False}; self.terminals[tid]=t
        async def capture():
            while True:
                chunk=await proc.stdout.read(4096)
                if not chunk: break
                t['out'].extend(chunk)
                if len(t['out'])>t['limit']: del t['out'][:len(t['out'])-t['limit']]; t['truncated']=True
        t['task']=asyncio.create_task(capture()); await self.reply(i,{'terminalId':tid}); await self.emit({'type':'terminal_started','terminal_id':tid,'command':[p['command'],*p.get('args',[])],'cwd':str(cwd)})
    def terminal(self,p):
        t=self.terminals.get(p['terminalId'])
        if not t: raise KeyError(f"Unknown terminal: {p['terminalId']}")
        return t
    async def term_output(self,i,p):
        t=self.terminal(p); result={'output':bytes(t['out']).decode(errors='replace'),'truncated':t['truncated']}
        if t['proc'].returncode is not None: result['exitStatus']={'exitCode':t['proc'].returncode,'signal':None}
        await self.reply(i,result)
    async def term_wait(self,i,p):
        t=self.terminal(p); code=await t['proc'].wait(); await t['task']; await self.reply(i,{'exitCode':code,'signal':None}); await self.emit({'type':'terminal_exit','terminal_id':p['terminalId'],'exit_code':code})
    async def term_stop(self,i,p,release):
        t=self.terminal(p)
        if t['proc'].returncode is None:
            t['proc'].terminate()
            try: await asyncio.wait_for(t['proc'].wait(),3)
            except asyncio.TimeoutError: t['proc'].kill(); await t['proc'].wait()
        if release: await t['task']; self.terminals.pop(p['terminalId'],None)
        await self.reply(i,None)
    def context(self):
        rules='\n'.join('- '+x for x in self.project.get('guardrails',[]))
        return f"""You are operating inside Bryan Leonard's Qira Grok Ops control plane.
Project: {self.project['name']}
Current objective: {self.project.get('objective','')}
Known traction/state: {self.project.get('traction','')}
Non-negotiable guardrails:
{rules}

Execution standard:
- Inspect the actual repository before making claims.
- Preserve completed work and avoid broad rewrites without evidence.
- Make concrete progress, run relevant checks, and report what was verified.
- Do not claim deployment or completion unless you actually confirmed it.
- Prioritize monetization, reliability, usability, and operational leverage over novelty.

"""
    async def prompt(self,text):
        async with self.lock:
            self.state='working'; await self.emit({'type':'prompt_started','text':text})
            try:
                result=await self.request('session/prompt',{'sessionId':self.acp,'prompt':[{'type':'text','text':self.context()+text}]},3600); await self.emit({'type':'prompt_completed','result':result})
            except Exception as e: await self.emit({'type':'client_error','method':'session/prompt','error':str(e)})
            finally: self.state='ready'
    async def stop(self):
        self.state='stopped'
        for t in self.terminals.values():
            if t['proc'].returncode is None: t['proc'].terminate()
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
            try: await asyncio.wait_for(self.proc.wait(),5)
            except asyncio.TimeoutError: self.proc.kill(); await self.proc.wait()
        for task in self.tasks:
            if not task.done(): task.cancel()
        await self.emit({'type':'session_stopped'})

class NewSession(BaseModel):
    project_id:str; approval_mode:str=Field('ask',pattern='^(ask|always)$'); model:str|None=None; effort:str=Field('high',pattern='^(low|medium|high)$')
class Prompt(BaseModel): text:str=Field(min_length=1,max_length=100000)
class Decision(BaseModel): request_id:int; option_id:str|None=None

@app.get('/')
async def index(): return FileResponse(HERE/'index.html')
@app.get('/api/status')
async def status():
    path=shutil.which('grok'); version=(await run('grok','version'))[1] if path else None
    return {'status':'ok','grok_installed':bool(path),'grok_path':path,'grok_version':version,'workspace_root':str(ROOT),'workspace_exists':ROOT.exists(),'active_sessions':len(SESSIONS),'time':now()}
@app.get('/api/projects')
async def projects():
    out=[]
    for p in defs():
        item=dict(p); path=project_path(p); item.update(resolved_path=str(path),path_exists=path.exists(),is_git_repo=(path/'.git').exists())
        if item['is_git_repo']:
            item['branch']=(await run('git','branch','--show-current',cwd=path,timeout=3))[1]; dirty=(await run('git','status','--porcelain',cwd=path,timeout=3))[1]; item['dirty_files']=len(dirty.splitlines()) if dirty else 0
        out.append(item)
    return out
@app.get('/api/sessions')
async def sessions(): return [{'id':a.id,'project_id':a.project['id'],'project_name':a.project['name'],'state':a.state,'root':str(a.root),'approval_mode':a.approval,'event_count':len(a.events)} for a in SESSIONS.values()]
@app.post('/api/sessions')
async def new_session(d:NewSession):
    p=next((x for x in defs() if x['id']==d.project_id),None)
    if not p: raise HTTPException(404,'Unknown project')
    a=Agent(p,d.approval_mode,d.model,d.effort); SESSIONS[a.id]=a
    try: await a.start()
    except Exception as e: await a.stop(); SESSIONS.pop(a.id,None); raise HTTPException(500,str(e))
    return {'id':a.id,'state':a.state,'project_id':p['id'],'root':str(a.root)}
@app.post('/api/sessions/{sid}/prompt')
async def prompt(sid:str,d:Prompt):
    a=SESSIONS.get(sid)
    if not a: raise HTTPException(404,'Unknown session')
    if a.lock.locked(): raise HTTPException(409,'Session is already processing a prompt')
    asyncio.create_task(a.prompt(d.text)); return {'accepted':True}
@app.post('/api/sessions/{sid}/permission')
async def permission(sid:str,d:Decision):
    a=SESSIONS.get(sid); f=a.permissions.get(d.request_id) if a else None
    if not a: raise HTTPException(404,'Unknown session')
    if not f or f.done(): raise HTTPException(409,'Permission request is no longer pending')
    f.set_result(d.option_id); return {'ok':True}
@app.delete('/api/sessions/{sid}')
async def delete(sid:str):
    a=SESSIONS.pop(sid,None)
    if not a: raise HTTPException(404,'Unknown session')
    await a.stop(); return {'ok':True}
@app.websocket('/ws/{sid}')
async def ws(websocket:WebSocket,sid:str):
    a=SESSIONS.get(sid)
    if not a: await websocket.close(code=4404); return
    await websocket.accept(); a.clients.add(websocket)
    try:
        for e in a.events: await websocket.send_json(e)
        while True: await websocket.receive_text()
    except WebSocketDisconnect: pass
    finally: a.clients.discard(websocket)
@app.on_event('shutdown')
async def shutdown(): await asyncio.gather(*(a.stop() for a in list(SESSIONS.values())),return_exceptions=True)
if __name__=='__main__':
    import uvicorn; uvicorn.run(app,host=os.getenv('GROK_CONTROL_HOST','127.0.0.1'),port=int(os.getenv('GROK_CONTROL_PORT','8787')))
