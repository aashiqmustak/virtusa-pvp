import asyncio,hashlib,json,secrets,time
from contextlib import suppress
from typing import Literal
from litestar import Request,WebSocket,get,post,websocket
from litestar.exceptions import ClientException
from pydantic import Field
from app.models import Session,VoiceSession,Application,uid,audit,now
from app.schemas import Strict
from app.security.auth import identity
from app.services.cases import get_case,ensure_editable
from app.workflows.engine import invalidate
from app.api.routes import lock
from app.config import settings

class StartVoice(Strict):
    revision:int=Field(ge=0)
    consent:Literal[True]
    language:Literal['en-IN','hi-IN','ta-IN']='en-IN'

def voice_actor(request,s,case_id):
    token=request.headers.get('Authorization','').removeprefix('Bearer ')
    if secrets.compare_digest(token,settings.analyst_token) or secrets.compare_digest(token,settings.reviewer_token):
        return identity(request)
    from app.api.journey import borrower,owned
    p=borrower(request,s);owned(s,case_id,p)
    return 'borrower:'+p.id

def public(v):return {'id':v.id,'created_at':v.created_at,'actor':v.actor,'status':v.status,'revision':v.revision,**v.data}
def configured():return settings.voice_mode in ['mock','sarvam'] and (settings.voice_mode=='mock' or bool(settings.sarvam_api_key))
@get('/api/applications/{case_id:str}/voice-sessions',sync_to_thread=True)
def history(request:Request,case_id:str)->dict:
    with Session() as s:
        voice_actor(request,s,case_id)
        get_case(s,case_id)
        return {'mode':settings.voice_mode,'configured':configured(),'items':[public(v) for v in s.query(VoiceSession).filter_by(case_id=case_id).order_by(VoiceSession.created_at.desc()).limit(20)]}
@post('/api/applications/{case_id:str}/voice-sessions')
async def start(request:Request,case_id:str,data:StartVoice)->dict:
    if not configured():raise ClientException('Voice is unavailable. Configure VOICE_MODE and server-side SARVAM_API_KEY or use mock mode.',status_code=503)
    async with lock:
        with Session.begin() as s:
            actor=voice_actor(request,s,case_id)
            a=get_case(s,case_id);ensure_editable(a)
            if 'journey' not in a.data or a.revision!=data.revision:raise ClientException('Current borrower-journey case required',status_code=409)
            if any(v.status in ['pending','active'] and v.expires_at>time.time() for v in s.query(VoiceSession).filter_by(case_id=case_id)):raise ClientException('A voice session is already active; stop it or wait for expiry',status_code=409)
            ticket=secrets.token_urlsafe(32);v=VoiceSession(id=uid(),case_id=case_id,actor=actor,ticket_hash=hashlib.sha256(ticket.encode()).hexdigest(),revision=a.revision,expires_at=time.time()+60,data={'mode':settings.voice_mode,'language':data.language,'consent_at':now(),'turns':[],'provider':'pipecat / '+('sarvam' if settings.voice_mode=='sarvam' else 'mock'),'review_required':True})
            s.add(v);audit(s,case_id,'voice_consent_recorded',actor=actor,session_id=v.id,mode=settings.voice_mode,language=data.language)
            return {'session_id':v.id,'ticket':ticket,'mode':settings.voice_mode,'socket_path':'/api/voice/socket','expires_in':60}

# No credentials in websocket URL/logs. Authenticate with a short-lived, single-use
# ticket in the first message before importing/starting provider services.
@websocket('/api/voice/socket')
async def voice_socket(socket:WebSocket)->None:
    origin=socket.headers.get('origin')
    if origin and origin not in settings.voice_origins.split(','):
        await socket.close(code=1008);return
    await socket.accept();session_id=None;interview=None;worker=None;runner_task=None;status='aborted';send_lock=asyncio.Lock()
    async def send(payload):
        async with send_lock:await asyncio.wait_for(socket.send_json(payload),5)
    try:
        hello=await asyncio.wait_for(socket.receive_json(),10)
        if not isinstance(hello,dict) or len(json.dumps(hello))>1000:raise ValueError('Invalid authentication')
        async with lock:
            with Session.begin() as s:
                v=s.get(VoiceSession,hello.get('session_id',''))
                if not v or v.status!='pending' or v.expires_at<time.time() or not secrets.compare_digest(v.ticket_hash,hashlib.sha256(str(hello.get('ticket','')).encode()).hexdigest()):raise ValueError('Invalid or expired voice ticket')
                a=get_case(s,v.case_id);ensure_editable(a)
                if a.revision!=v.revision:raise ValueError('Case changed; start a new session')
                session_id=v.id;language=v.data['language'];mode=v.data['mode'];v.status='active';v.ticket_hash='';v.expires_at=time.time()+300
        from app.services.voice.pipeline import build_pipeline,InterviewCommand,InputAudioRawFrame
        worker,runner,interview,output=build_pipeline(mode,language,send,settings.sarvam_api_key,settings.sarvam_stt_model,settings.sarvam_tts_model,settings.sarvam_voice)
        runner_task=asyncio.create_task(runner.run(worker))
        started=time.monotonic();audio_bytes=0;commands=0
        while time.monotonic()-started<300:
            if output.failure.is_set() or runner_task.done():status='failed';break
            receive=asyncio.create_task(socket.receive());failure=asyncio.create_task(output.failure.wait())
            done,_=await asyncio.wait([receive,runner_task,failure],timeout=min(60,300-(time.monotonic()-started)),return_when=asyncio.FIRST_COMPLETED)
            if failure not in done:failure.cancel()
            await asyncio.gather(failure,return_exceptions=True)
            if failure in done:status='failed'
            if receive not in done:
                receive.cancel();await asyncio.gather(receive,return_exceptions=True);break
            msg=receive.result()
            if msg['type']=='websocket.disconnect':break
            raw=msg.get('bytes')
            if raw is not None:
                if mode!='sarvam' or len(raw)>8192 or len(raw)%2:raise ValueError('Invalid PCM audio')
                audio_bytes+=len(raw)
                if audio_bytes>32000*(time.monotonic()-started+3):raise ValueError('Audio rate exceeded')
                await worker.queue_frame(InputAudioRawFrame(audio=raw,sample_rate=16000,num_channels=1))
            else:
                text=msg.get('text','')
                if len(text)>2500:raise ValueError('Message too large')
                data=json.loads(text);commands+=1
                if commands>40:raise ValueError('Command budget exceeded')
                if data.get('type')=='stop':status='completed' if interview.finished else 'aborted';break
                if data.get('type')!='answer':raise ValueError('Unsupported command')
                answer=data.get('text','')
                if not isinstance(answer,str) or len(answer)>2000:raise ValueError('Invalid answer')
                await worker.queue_frame(InterviewCommand('answer',answer if mode=='mock' else ''))
        if interview and interview.finished:status='completed'
    except Exception:
        status='failed'
        with suppress(Exception):await send({'type':'error','message':'Voice session could not continue. Check consent, session expiry and provider configuration; retry or use manual verification.'})
    finally:
        if worker:
            with suppress(Exception):await asyncio.wait_for(worker.cancel(),5)
        if runner_task:
            runner_task.cancel();await asyncio.gather(runner_task,return_exceptions=True)
        if session_id:
            async with lock:
                with Session.begin() as s:
                    v=s.get(VoiceSession,session_id);a=s.get(Application,v.case_id)
                    stale=a.revision!=v.revision or a.status in ['approved','rejected','processing']
                    v.status=status;v.expires_at=time.time();v.data={**v.data,'turns':interview.turns if interview else [],'finished_at':now(),'stale':stale}
                    if status=='completed' and not stale:
                        j=dict(a.data['journey']);j['verification']={};a.data={**a.data,'journey':j}
                        invalidate(s,a,'cam','Voice transcript captured; human verification required')
                    audit(s,a.id,'voice_session_finished',session_id=v.id,status=status,stale=stale,actor=v.actor)
            with suppress(Exception):await send({'type':'saved','status':status,'stale':stale})
        with suppress(Exception):await socket.close()

routes=[history,start,voice_socket]
