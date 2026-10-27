"""Pipecat audio pipeline with bounded, non-decision-making interview turns.
Mock mode still uses Pipecat, but no Sarvam services or microphone audio.
"""
import asyncio,base64
from dataclasses import dataclass
from pipecat.frames.frames import DataFrame,Frame,TranscriptionFrame,TTSSpeakFrame,TTSAudioRawFrame,ErrorFrame,InputAudioRawFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker,PipelineParams
from pipecat.processors.frame_processor import FrameProcessor,FrameDirection
from pipecat.workers.runner import WorkerRunner

QUESTIONS={
'en-IN':['Please state your name as it appears on your application. Do not share identity numbers.','What does your business do, and who are its customers?','How will the requested loan funds be used?'],
'hi-IN':['कृपया अपना आवेदक नाम बताएं। पहचान संख्या साझा न करें।','आपका व्यवसाय क्या करता है और उसके ग्राहक कौन हैं?','ऋण राशि का उपयोग किस काम के लिए होगा?'],
'ta-IN':['உங்கள் விண்ணப்பதாரர் பெயரைக் கூறுங்கள். உண்மையான அடையாள எண்களைப் பகிர வேண்டாம்.','உங்கள் நிறுவனம் என்ன செய்கிறது? அதன் வாடிக்கையாளர்கள் யார்?','கடன் தொகையை எதற்குப் பயன்படுத்துவீர்கள்?']}
CLOSING={'en-IN':'Thank you. Your answers will be reviewed by a credit officer. This interview does not approve the loan.','hi-IN':'धन्यवाद। ऋण अधिकारी आपके उत्तरों की समीक्षा करेंगे। यह साक्षात्कार ऋण की स्वीकृति नहीं है।','ta-IN':'நன்றி. கடன் அதிகாரி உங்கள் பதில்களை மதிப்பாய்வு செய்வார். இந்த நேர்காணல் கடனுக்கு ஒப்புதல் அளிக்காது.'}
@dataclass
class InterviewCommand(DataFrame):
    command:str
    text:str=''

class InterviewProcessor(FrameProcessor):
    def __init__(self,language,send,mock=False):
        super().__init__();self.language=language;self.send=send;self.mock=mock;self.turns=[];self.buffer='';self.finished=False
    async def prompt(self):
        text=QUESTIONS[self.language][len(self.turns)] if len(self.turns)<3 else CLOSING[self.language]
        await self.send({'type':'question','index':len(self.turns),'text':text})
        if not self.mock:await self.push_frame(TTSSpeakFrame(text))
    async def process_frame(self,frame:Frame,direction:FrameDirection):
        await super().process_frame(frame,direction)
        if isinstance(frame,TranscriptionFrame) and not self.finished:
            self.buffer=(self.buffer+' '+frame.text).strip()[:2000]
            await self.send({'type':'transcript','text':self.buffer})
        elif isinstance(frame,InterviewCommand):
            if frame.command=='begin':await self.prompt()
            elif frame.command=='answer' and not self.finished:
                answer=frame.text.strip() if self.mock else self.buffer.strip()
                if not answer:await self.send({'type':'validation','message':'Wait for a transcript or enter a mock answer before submitting.'});return
                self.turns.append({'question':QUESTIONS[self.language][len(self.turns)],'answer':answer[:2000]});self.buffer=''
                await self.send({'type':'answer_saved','turns':self.turns})
                if len(self.turns)==3:self.finished=True
                await self.prompt()
                if self.finished:await self.send({'type':'completed','turns':self.turns,'message':'Interview captured. Officer review is required; no identity or loan decision was made.'})
        else:await self.push_frame(frame,direction)

class BrowserOutput(FrameProcessor):
    def __init__(self,send):super().__init__();self.send=send;self.failure=asyncio.Event()
    async def process_frame(self,frame,direction):
        await super().process_frame(frame,direction)
        if isinstance(frame,TTSAudioRawFrame):await self.send({'type':'audio','pcm':base64.b64encode(frame.audio).decode(),'sample_rate':frame.sample_rate})
        elif isinstance(frame,ErrorFrame):
            self.failure.set();await self.send({'type':'error','message':'Speech provider failed. Stop this session and retry; manual verification remains available.'})
        await self.push_frame(frame,direction)

def build_pipeline(mode,language,send,key='',stt_model='saaras:v3-realtime',tts_model='bulbul:v3',voice='shubh'):
    interview=InterviewProcessor(language,send,mock=mode=='mock');output=BrowserOutput(send)
    if mode=='sarvam':
        from pipecat.services.sarvam.stt import SarvamRealtimeSTTService
        from pipecat.services.sarvam.tts import SarvamTTSService
        stt=SarvamRealtimeSTTService(api_key=key,sample_rate=16000,should_interrupt=False,settings=SarvamRealtimeSTTService.Settings(model=stt_model,language_code=language,mode='transcribe',stream_type='fast'))
        tts=SarvamTTSService(api_key=key,sample_rate=24000,settings=SarvamTTSService.Settings(model=tts_model,voice=voice,language=language,min_buffer_size=30))
        processors=[stt,interview,tts,output]
    else:processors=[interview,output]
    worker=PipelineWorker(Pipeline(processors),params=PipelineParams(audio_in_sample_rate=16000,audio_out_sample_rate=24000),enable_rtvi=False,enable_turn_tracking=False,idle_timeout_secs=None)
    @worker.event_handler('on_pipeline_error')
    async def failed(worker,frame):
        output.failure.set()
        await send({'type':'error','message':'Speech provider failed. Stop and retry, or use manual verification.'})
    @worker.event_handler('on_pipeline_started')
    async def ready(worker,frame):
        await send({'type':'ready','mode':mode,'language':language})
        await worker.queue_frame(InterviewCommand('begin'))
    runner=WorkerRunner(handle_sigint=False,handle_sigterm=False)
    return worker,runner,interview,output
