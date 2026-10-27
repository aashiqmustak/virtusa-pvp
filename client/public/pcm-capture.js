// Browser microphone -> mono 16 kHz signed little-endian PCM, 100 ms chunks.
// AudioWorklet avoids main-thread timing jitter; output remains silent.
class PCMCapture extends AudioWorkletProcessor {
  constructor() { super(); this.record=false;this.phase=0;this.sum=0;this.count=0;this.samples=[];this.port.onmessage=e=>{const was=this.record;this.record=!!e.data.record;if(was&&!this.record){if(this.samples.length){const out=new ArrayBuffer(this.samples.length*2),view=new DataView(out);this.samples.forEach((v,i)=>view.setInt16(i*2,v,true));this.port.postMessage(out,[out])}for(let i=0;i<10;i++){const tail=new ArrayBuffer(3200);this.port.postMessage(tail,[tail])}this.samples=[];this.phase=0;this.sum=0;this.count=0}} }
  process(inputs) {
    const input=inputs[0]?.[0];if(!this.record||!input)return true;
    const ratio=sampleRate/16000;
    for(const value of input){this.sum+=value;this.count++;this.phase++;
      if(this.phase>=ratio){this.phase-=ratio;const v=Math.max(-1,Math.min(1,this.sum/this.count));this.samples.push(Math.round(v*(v<0?32768:32767)));this.sum=0;this.count=0;
        if(this.samples.length===1600){const out=new ArrayBuffer(3200),view=new DataView(out);this.samples.forEach((v,i)=>view.setInt16(i*2,v,true));this.port.postMessage(out,[out]);this.samples=[]}
      }
    }return true;
  }
}
registerProcessor('pcm-capture',PCMCapture);
