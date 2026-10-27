import {reactive} from 'vue'
import type {Case} from '../types'
export const desk=reactive({view:'dashboard',selected:null as Case|null,error:'',busy:false})
export function inr(value:unknown){return value===null||value===undefined?'Insufficient evidence':new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(Number(value))}
export function label(value:string){const names:Record<string,string>={awaiting_review:'In review',needs_evidence:'Action needed',approved:'Approved',rejected:'Not approved',draft:'In preparation',processing:'Under assessment',processing_failed:'Needs attention',failed:'Needs attention',complete:'Complete',pending:'Pending',pass:'Pass',fail:'Review required',exception:'Review required',insufficient_evidence:'More information needed',proposal_requires_review:'Ready for review',not_required:'No exception needed'};return names[value]||value.replaceAll('_',' ')}
