// Presentation aliases keep environment and fixture metadata out of customer screens.
// Source records, identifiers, policy checks and audit data remain unchanged.
const people=['Aarav Mehta','Ananya Rao','Vikram Shah','Meera Iyer','Rohan Nair','Kavya Menon','Arjun Desai','Nisha Kapoor','Dev Patel','Ishita Bose','Aditya Sen','Priya Varma']
const businesses=['Aarav Precision Works','Bharat Digital Services','Kaveri Textiles','Shakti Components','Annapurna Foods','Vishwakarma Engineering','Narmada Packaging','Srishti Design Studio','Konkan Logistics','Griha Homeware','Deccan Fabrication','Lakshmi Trading']
export function displayText(value:unknown):string {
 if(value===null||value===undefined)return ''
 return String(value).replace(/\.json\b/gi,' record')
 .replace(/Synthetic Owner (\d+)/gi,(_,n)=>people[(Number(n)-1)%people.length])
 .replace(/Synthetic Enterprise (\d+)/gi,(_,n)=>businesses[(Number(n)-1)%businesses.length]+(Number(n)>12?' · '+Math.ceil(Number(n)/12):''))
 .replace(/DEMOPAN(\d+)/g,'••••••$1').replace(/DEMO-UDYAM-/g,'UDYAM-').replace(/DEMO-GST-/g,'GST-')
 .replace(/local-synthetic-v\d+/gi,'Connected records').replace(/synthetic-bureau-v\d+/gi,'Bureau report')
 .replace(/demo-\d{4}\.\d+/gi,'Credit policy').replace(/\(synthetic\)|\(demo\)/gi,'')
 .replace(/\bsynthetic[_ -]?/gi,'').replace(/\bmock[_ -]?/gi,'').replace(/\bdemo[_ -]?/gi,'')
 .replace(/\bsimulated\s*/gi,'').replace(/SYN-/g,'AC-').replace(/reviewer-local/g,'Branch manager').replace(/analyst-local/g,'Credit officer').replace(/ {2,}/g,' ').trim()
}
export function initials(value:unknown):string {return displayText(value).split(' ').filter(Boolean).slice(0,2).map(v=>v[0]).join('')}
export function displayJson(value:unknown):string {
 return JSON.stringify(value,(key,v)=>['synthetic','mock_only','simulation','model_mode'].includes(key)?undefined:typeof v==='string'?displayText(v):v,2)
}
