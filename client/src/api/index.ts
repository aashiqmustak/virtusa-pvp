export function token(){return sessionStorage.getItem('msme_token')||''}
export async function api<T=any>(path:string,body?:unknown):Promise<T>{
 const response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token(),...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)})
 if(!response.ok){const err=await response.json().catch(()=>({}));throw new Error(err.detail||err.message||`Request failed (${response.status})`)}
 return response.json()
}
export function upload(caseId:string,file:File,kind:string,replaces:string,onProgress:(value:number)=>void):Promise<any>{
 return new Promise((resolve,reject)=>{const req=new XMLHttpRequest();req.open('POST',`/api/applications/${caseId}/documents?kind=${encodeURIComponent(kind)}${replaces?'&replaces='+encodeURIComponent(replaces):''}`);req.setRequestHeader('Authorization','Bearer '+token());req.upload.onprogress=e=>{if(e.lengthComputable)onProgress(Math.round(e.loaded/e.total*100))};req.onerror=()=>reject(new Error('Upload connection failed'));req.onload=()=>{let data;try{data=JSON.parse(req.responseText)}catch{reject(new Error('Invalid server response'));return}req.status<300?resolve(data):reject(new Error(data.detail||'Upload failed'))};const form=new FormData();form.append('data',file);req.send(form)})
}
